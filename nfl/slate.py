"""nfl.slate — build the NFL weather slate for a date window.

NWS-primary, WeatherAPI-fallback (reuses cfb/nws_client for pacing +
circuit breaker). Dome venues are skipped entirely — no weather lookup
since the game is indoors. Retractable venues fetch outdoor conditions
(template handles the Closed/Open toggle).

Game shape extends schedule.py output with:
  - "forecast":         kickoff snapshot dict (None for domes)
  - "hourly":           list of period dicts around kickoff
  - "weather_source":   "nws" | "weatherapi-fallback" | "indoor-skip" | "all-failed"
  - "weather_error":    None | str
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from .schedule import get_nfl_week_games
from . import odds as nfl_odds_client
from . import odds_storage as nfl_odds_storage

from cfb.nws_client import fetch_cfb_hourly
from mlb.weatherapi import fetch_weatherapi_hourly, find_weatherapi_period
from mlb.nws import find_period_for_time
from hrrr import get_hrrr_periods


# NFL game window: 1h before through 4h after kickoff.
# Football is ~3.5 hours; 4h buffer covers halftime + late TV slate overrun.
HOURS_BEFORE_KICKOFF = 1
HOURS_GAME_WINDOW    = 4   # how many hours after kickoff the hourly window extends
HOURS_HIGHLIGHTED    = 3   # how many of those hours get the game-hour shaded highlight
                            # (typical NFL game runs ~3 hours: kickoff → kickoff+3)
HOURS_GAME_HIGHLIGHT = 3   # only 3 in-game hours get highlighted, per Kevin


def build_nfl_slate(start_date: Optional[datetime] = None,
                    days_ahead: int = 8) -> list[dict]:
    """Build full weather-attached NFL slate.

    Default 8-day window covers Thu→Mon spread + buffer."""
    if start_date is None:
        # Back the window start up 24h so today's already-kicked-off
        # games stay on the slate all day. Same fix Kevin flagged for
        # CFB on 2026-08-29: filter_to_window drops games with
        # kickoff_utc < start_utc, and if start_utc is now() then a
        # noon-ET Sunday game disappears at 12:01. Now the window
        # includes today's earlier kickoffs; _is_game_stale below drops
        # them the next morning by venue-local calendar day.
        start_date = datetime.now(timezone.utc) - timedelta(hours=24)

    games = get_nfl_week_games(start_date, days_ahead=days_ahead)
    if not games:
        return []

    # Drop stale games — kickoff already in the past by venue-local date.
    # Kept in-window by the 24h backup above; dropped here once the
    # venue's local calendar has rolled over.
    games = [g for g in games if not _is_game_stale(g)]

    venue_weather: dict[tuple[float, float], tuple[list[dict], str, Optional[str]]] = {}

    # Fetch odds ONCE per build (2 API credits — one per NFL slug). Empty
    # list on any failure; the slate still builds, just without totals.
    odds_list = nfl_odds_client.fetch_nfl_totals()

    now_utc = datetime.now(timezone.utc)
    for g in games:
        _attach_weather_to_game(g, venue_weather)
        g["odds"] = _build_odds_for_game(g, odds_list, now_utc)

    odds_ct = sum(1 for g in games if g.get("odds"))
    print(
        f"[nfl.slate] built slate: {len(games)} games, "
        f"{len(venue_weather)} unique outdoor venues fetched, "
        f"{odds_ct} odds attached",
        flush=True,
    )
    return games


def _build_odds_for_game(game: dict, odds_list: list[dict],
                         now_utc: datetime) -> Optional[dict]:
    """Match a game to its odds entry and return the template-shaped dict.

    Mirrors cfb/slate.py._build_odds_for_game, including the kickoff
    freeze: once a game starts, The Odds API returns LIVE in-game totals,
    and since we only poll every 25 minutes that number is stale garbage
    between cycles. So we snapshot the last pre-kickoff total and serve
    that for the rest of the game instead.

    Returns None when no odds match — books don't post every game.
    """
    if not odds_list:
        return None
    event_id = game.get("event_id") or game.get("id")
    away = (game.get("away") or {}).get("name") or ""
    home = (game.get("home") or {}).get("name") or ""
    kickoff_utc = game.get("kickoff_utc")
    if not (event_id and away and home and kickoff_utc):
        return None

    match = nfl_odds_client.match_odds_to_game(odds_list, away, home, kickoff_utc)
    if not match:
        return None

    live_total   = match["total"]
    book_display = match["book_display"]
    game_started = kickoff_utc <= now_utc

    if not game_started:
        # Opening is immutable — first total we ever saw for this game.
        nfl_odds_storage.record_opening_if_new(event_id, live_total, book_display)
        # Kickoff line is last-write-wins; the final pre-kickoff write is
        # what we freeze and display once the game is underway.
        nfl_odds_storage.record_kickoff_line(event_id, live_total, book_display)

    opening_rec   = nfl_odds_storage.get_opening(event_id)
    opening_total = opening_rec["total"] if opening_rec else None

    if game_started:
        frozen = nfl_odds_storage.get_kickoff_line(event_id)
        if frozen is not None:
            current_total = frozen["total"]
            if frozen.get("book_display"):
                book_display = frozen["book_display"]
        else:
            # Game started before we ever tracked it — no snapshot exists.
            # Live total is imperfect but better than showing nothing.
            current_total = live_total
    else:
        current_total = live_total

    if opening_total is not None:
        delta = round(current_total - opening_total, 2)
    else:
        delta = None

    if delta is None:
        delta_str = None
    elif delta > 0:
        delta_str = f"+{delta}"
    elif delta < 0:
        delta_str = f"{delta}"      # already carries the minus sign
    else:
        delta_str = "0"

    return {
        "current":      current_total,
        "opening":      opening_total,
        "delta":        delta,
        "delta_str":    delta_str,
        "book_display": book_display,
        "book_key":     match.get("book_key", ""),
        "frozen":       game_started,
    }


def _is_game_stale(game: dict) -> bool:
    """A game is stale when today's local calendar date at the venue is
    already past the game's local calendar date. Mirrors cfb/slate.py's
    _is_game_stale. Keeps today's in-progress games visible; drops
    yesterday's the next morning per venue-local time."""
    venue = game.get("venue") or {}
    kickoff_utc = game.get("kickoff_utc")
    tz_name = venue.get("timezone") or venue.get("tz")
    if not kickoff_utc or not tz_name:
        return False
    try:
        from zoneinfo import ZoneInfo as _ZI
        tz = _ZI(tz_name)
        kickoff_local_date = kickoff_utc.astimezone(tz).date()
        today_local_date = datetime.now(tz).date()
        return kickoff_local_date < today_local_date
    except Exception:
        return False


def _attach_weather_to_game(game: dict, venue_cache: dict) -> None:
    venue = game.get("venue") or {}
    roof = (venue.get("roof_type") or "").lower()
    lat = venue.get("lat")
    lon = venue.get("lon")
    kickoff_utc = game.get("kickoff_utc")

    # Dome venues — skip weather entirely. Game is indoors, no impact.
    if roof == "fixed_dome":
        game["forecast"] = None
        game["hourly"] = []
        game["weather_source"] = "indoor-skip"
        game["weather_error"] = None
        return

    if lat is None or lon is None or kickoff_utc is None:
        game["forecast"] = None
        game["hourly"] = []
        game["weather_source"] = "no-venue-data"
        game["weather_error"] = "Stadium lat/lon not available for this game"
        return

    key = (round(lat, 4), round(lon, 4))
    if key in venue_cache:
        periods, source, err = venue_cache[key]
    else:
        # International venues (nws_unsupported) skip the NWS attempt —
        # NWS only covers US territory, calling it for London / Mexico
        # City / Munich just wastes a request and trips the circuit
        # breaker over time.
        if venue.get("nws_unsupported"):
            periods, source, err = _fetch_weatherapi_only(lat, lon)
        else:
            periods, source, err = _fetch_with_nws_fallback(lat, lon)
        venue_cache[key] = (periods, source, err)

    if not periods:
        game["forecast"] = None
        game["hourly"] = []
        game["weather_source"] = source or "all-failed"
        game["weather_error"] = err
        return

    if source == "nws":
        snapshot = find_period_for_time(periods, kickoff_utc)
    else:
        snapshot = find_weatherapi_period(periods, kickoff_utc)

    hourly = _hourly_window(periods, kickoff_utc)

    game["forecast"] = snapshot
    game["hourly"] = hourly
    game["weather_source"] = source
    game["weather_error"] = err

    # HRRR high-res overlay (3 km CONUS, includes wind gusts). Fetched per
    # game so the per-game HRRR toggle on the slate page has data. HRRR is
    # cached in-process by lat/lon so shared venues (MetLife: NYG+NYJ,
    # SoFi: LAR+LAC) get one fetch. Skip HRRR entirely for international
    # venues — HRRR is CONUS only. Fail-soft: no HRRR = no toggle.
    if venue.get("nws_unsupported"):
        game["hrrr_hourly"] = []
    else:
        try:
            hrrr_periods = get_hrrr_periods(lat, lon)
            if hrrr_periods:
                game["hrrr_hourly"] = _hourly_window(hrrr_periods, kickoff_utc)
            else:
                game["hrrr_hourly"] = []
        except Exception as e:
            print(f"[nfl.slate] HRRR fetch failed for {lat},{lon}: {e}", flush=True)
            game["hrrr_hourly"] = []


def _fetch_weatherapi_only(lat: float, lon: float) -> tuple[list[dict], str, Optional[str]]:
    """Direct WeatherAPI path for international venues — NWS only serves
    US territory, no point trying NWS first for London / Munich / etc."""
    try:
        periods = fetch_weatherapi_hourly(lat, lon)
        if periods:
            return periods, "weatherapi-international", None
        return [], "all-failed", "WeatherAPI returned empty for international venue"
    except Exception as e:
        return [], "all-failed", f"WeatherAPI: {e}"


def _fetch_with_nws_fallback(lat: float, lon: float) -> tuple[list[dict], str, Optional[str]]:
    try:
        periods = fetch_cfb_hourly(lat, lon)
        if periods:
            return periods, "nws", None
        nws_err = "NWS returned None (circuit open, rate-limited, or empty)"
    except Exception as e:
        nws_err = str(e)
        print(f"[nfl.slate] NWS raised for {lat},{lon}: {e} — falling back to WeatherAPI",
              flush=True)

    try:
        periods = fetch_weatherapi_hourly(lat, lon)
        if periods:
            print(f"[nfl.slate] WeatherAPI fallback ok for {lat},{lon}", flush=True)
            return periods, "weatherapi-fallback", None
        return [], "all-failed", f"NWS: {nws_err}; WeatherAPI returned empty"
    except Exception as wa_err:
        return [], "all-failed", f"NWS: {nws_err}; WeatherAPI: {wa_err}"


def _hourly_window(periods: list[dict], kickoff_utc: datetime) -> list[dict]:
    """Extract 1h before kickoff through 4h after. Game-time flagged."""
    if not periods:
        return []
    kickoff = kickoff_utc.replace(minute=0, second=0, microsecond=0)
    start = kickoff - timedelta(hours=HOURS_BEFORE_KICKOFF)
    end = kickoff + timedelta(hours=HOURS_GAME_WINDOW)
    out = []
    for p in periods:
        try:
            st_raw = p.get("start_time") or ""
            st = datetime.fromisoformat(st_raw.replace("Z", "+00:00"))
            if st.tzinfo is None:
                st = st.replace(tzinfo=timezone.utc)
            if start <= st < end:
                p2 = dict(p)
                p2["is_game_hour"] = (kickoff <= st < kickoff + timedelta(hours=HOURS_HIGHLIGHTED))
                out.append(p2)
        except (ValueError, AttributeError):
            continue
    return out


# EOF-CANARY 2026-07-04-cfb-recovery
