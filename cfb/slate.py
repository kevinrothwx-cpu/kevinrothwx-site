"""
cfb.slate — build a CFB weather slate for a date window.

Combines the schedule fetcher (cfb/schedule.py) with weather attachment
to produce a normalized list of games each carrying:
  - Full team + venue + ranking info from the schedule
  - Kickoff-time weather snapshot
  - Hourly forecast strip around kickoff (for detail pages)
  - HRRR overlay strip around kickoff (3km CONUS)
  - Weather source tag + error if any

Weather strategy (per design decision with Kevin):
    PRIMARY: NWS via cfb/nws_client (distinct UA, sequential pacing,
             circuit breaker on 429/503, permanent gridpoint cache)
    FALLBACK: WeatherAPI (paid tier, when NWS fails or circuit is open)
    OVERLAY:  HRRR (Open-Meteo 3km CONUS), attached separately so the
              template can render an optional higher-resolution toggle.

Stale-game filter: games with a kickoff_local calendar date already in
the past at the venue's local timezone are dropped from the slate. CFB
spreads across Wed-Sat, so we can't just filter by "today ET"; each
game ages off in its own venue-local morning.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from .schedule import get_cfb_week_games
from .nws_client import fetch_cfb_hourly
from . import odds as cfb_odds_client
from . import odds_storage as cfb_odds_storage

from mlb.weatherapi import fetch_weatherapi_hourly, find_weatherapi_period
from mlb.nws import extract_forecast, find_period_for_time
from hrrr import get_hrrr_periods


# ── Tuning constants ──────────────────────────────────────────────────────

HOURS_BEFORE_KICKOFF = 1
HOURS_GAME_WINDOW    = 4   # buffer past kickoff to cover ~3.5h game + halftime


# ── Public entry point ───────────────────────────────────────────────────

def build_cfb_slate(start_date: Optional[datetime] = None,
                    days_ahead: int = 7) -> list[dict]:
    """Build the full weather-attached slate for a date window."""
    if start_date is None:
        start_date = datetime.now(timezone.utc)

    games = get_cfb_week_games(start_date, days_ahead=days_ahead)
    if not games:
        return []

    # Drop stale games — kickoff already in the past by venue-local date.
    games = [g for g in games if not _is_game_stale(g)]

    # Fetch odds ONCE per slate build (one API credit covers the whole
    # response). Empty list on any failure — slate still builds without odds.
    odds_list = cfb_odds_client.fetch_cfb_totals()

    # Per-venue NWS/WeatherAPI cache shared across the build.
    venue_weather: dict[tuple[float, float], tuple[list[dict], str, Optional[str]]] = {}
    # Separate HRRR cache — HRRR is optional overlay, US CONUS only.
    venue_hrrr: dict[tuple[float, float], list[dict]] = {}

    now_utc = datetime.now(timezone.utc)
    for g in games:
        _attach_weather_to_game(g, venue_weather, venue_hrrr)
        # Odds attachment — safe to run even when odds_list is empty.
        g["odds"] = _build_odds_for_game(g, odds_list, now_utc)

    odds_ct = sum(1 for g in games if g.get("odds"))
    print(
        f"[cfb.slate] built slate: {len(games)} games, "
        f"{len(venue_weather)} unique venues fetched, "
        f"{len(venue_hrrr)} HRRR overlays, "
        f"{odds_ct} odds attached",
        flush=True,
    )
    return games


def _build_odds_for_game(game: dict, odds_list: list[dict], now_utc: datetime) -> Optional[dict]:
    """Match a game to its odds entry, record the opening line if new,
    and return the template-shaped odds dict. See mlb/slate.py's
    _build_odds_for_game for the shape reference — identical here.

    Returns None if we couldn't match odds for this game (Odds API doesn't
    always cover every game, especially early week or FCS opponents)."""
    if not odds_list:
        return None
    event_id = game.get("event_id")
    away = (game.get("away") or {}).get("name") or ""
    home = (game.get("home") or {}).get("name") or ""
    kickoff_utc = game.get("kickoff_utc")
    if not (event_id and away and home and kickoff_utc):
        return None

    match = cfb_odds_client.match_odds_to_game(odds_list, away, home, kickoff_utc)
    if not match:
        return None

    current_total = match["total"]
    book_display  = match["book_display"]
    game_started  = kickoff_utc <= now_utc

    # Only record opening for pre-kickoff games. After kickoff the "current"
    # value from The Odds API is stale/closed — don't accidentally record
    # that as an opening for a game we started tracking late.
    if not game_started:
        cfb_odds_storage.record_opening_if_new(event_id, current_total, book_display)

    opening_rec   = cfb_odds_storage.get_opening(event_id)
    opening_total = opening_rec["total"] if opening_rec else None

    if opening_total is not None:
        delta = round(current_total - opening_total, 2)
    else:
        delta = None

    if delta is None:
        delta_str = None
    elif delta > 0:
        delta_str = f"+{delta}"
    elif delta < 0:
        delta_str = f"{delta}"  # already has minus sign
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
    already past the game's local calendar date. Handles CFB's Wed-Sat
    spread cleanly — each game ages off in its own venue-local morning
    regardless of what timezone the venue is in."""
    venue = game.get("venue") or {}
    kickoff_utc = game.get("kickoff_utc")
    tz_name = venue.get("timezone") or venue.get("tz")
    if not kickoff_utc or not tz_name:
        return False
    try:
        tz = ZoneInfo(tz_name)
        kickoff_local_date = kickoff_utc.astimezone(tz).date()
        today_local_date = datetime.now(tz).date()
        return kickoff_local_date < today_local_date
    except Exception:
        return False


# ── Weather attachment ────────────────────────────────────────────────────

def _attach_weather_to_game(game: dict, venue_cache: dict, hrrr_cache: dict) -> None:
    """Mutate game dict in place: forecast, hourly, hrrr_hourly, weather_source, weather_error."""
    venue = game.get("venue") or {}
    lat = venue.get("lat")
    lon = venue.get("lon")
    kickoff_utc = game.get("kickoff_utc")

    if lat is None or lon is None or kickoff_utc is None:
        game["forecast"] = None
        game["hourly"] = []
        game["hrrr_hourly"] = []
        game["weather_source"] = "no-venue-data"
        game["weather_error"] = "Stadium lat/lon not available for this game"
        return

    key = (round(lat, 4), round(lon, 4))
    if key in venue_cache:
        periods, source, err = venue_cache[key]
    else:
        # International neutral-site games (Croke Park Dublin, Wembley,
        # Estadio Azteca, etc.) can't use NWS — it only covers US
        # territory. Route straight to WeatherAPI to avoid a guaranteed
        # NWS failure and its noisy log line.
        if venue.get("nws_unsupported"):
            periods, source, err = _fetch_weatherapi_only(lat, lon)
        else:
            periods, source, err = _fetch_weather_with_fallback(lat, lon)
        venue_cache[key] = (periods, source, err)

    if not periods:
        game["forecast"] = None
        game["hourly"] = []
        game["hrrr_hourly"] = []
        game["weather_source"] = source or "all-failed"
        game["weather_error"] = err
        return

    # Kickoff snapshot. NWS + WeatherAPI use different period schemas,
    # so pick the right accessor based on which source produced them.
    if source == "nws":
        snapshot = find_period_for_time(periods, kickoff_utc)
    else:  # weatherapi-fallback OR weatherapi-international
        snapshot = find_weatherapi_period(periods, kickoff_utc)

    hourly = _hourly_window(periods, kickoff_utc)

    # HRRR overlay — CONUS-only. Skip venues flagged nws_unsupported
    # (future-proof for teams playing in Ireland/UK — not a concern today
    # since all FBS teams are US, but the schema is ready).
    hrrr_hourly: list[dict] = []
    if not venue.get("nws_unsupported"):
        if key in hrrr_cache:
            all_hrrr = hrrr_cache[key]
        else:
            try:
                all_hrrr = get_hrrr_periods(lat, lon) or []
            except Exception as e:
                print(f"[cfb.slate] HRRR fetch failed at {lat},{lon}: {e}", flush=True)
                all_hrrr = []
            hrrr_cache[key] = all_hrrr
        if all_hrrr:
            hrrr_hourly = _hourly_window(all_hrrr, kickoff_utc)

    game["forecast"] = snapshot
    game["hourly"] = hourly
    game["hrrr_hourly"] = hrrr_hourly
    game["weather_source"] = source
    game["weather_error"] = err


# ── Provider fetch with fallback ──────────────────────────────────────────

def _fetch_weather_with_fallback(lat: float, lon: float) -> tuple[list[dict], str, Optional[str]]:
    """NWS primary via cfb/nws_client, WeatherAPI fallback on failure."""
    try:
        periods = fetch_cfb_hourly(lat, lon)
        if periods:
            return periods, "nws", None
        nws_err = "NWS returned None (circuit open, rate-limited, or empty)"
    except Exception as e:
        nws_err = str(e)
        print(f"[cfb.slate] NWS client raised for {lat},{lon}: {e} - falling back to WeatherAPI",
              flush=True)

    try:
        periods = fetch_weatherapi_hourly(lat, lon)
        if periods:
            print(f"[cfb.slate] WeatherAPI fallback ok for {lat},{lon}", flush=True)
            return periods, "weatherapi-fallback", None
        return [], "all-failed", f"NWS: {nws_err}; WeatherAPI returned empty"
    except Exception as wa_err:
        return [], "all-failed", f"NWS: {nws_err}; WeatherAPI: {wa_err}"


def _fetch_weatherapi_only(lat: float, lon: float) -> tuple[list[dict], str, Optional[str]]:
    """Direct WeatherAPI path for international neutral-site games (Croke
    Park, Wembley, Estadio Azteca, etc.). NWS only serves US territory
    so there's no point trying it first — skip the guaranteed failure
    and the noisy log line."""
    try:
        periods = fetch_weatherapi_hourly(lat, lon)
        if periods:
            return periods, "weatherapi-international", None
        return [], "all-failed", "WeatherAPI returned empty for international venue"
    except Exception as e:
        return [], "all-failed", f"WeatherAPI (international): {e}"


# ── Hourly window extraction ──────────────────────────────────────────────

def _hourly_window(periods: list[dict], kickoff_utc: datetime) -> list[dict]:
    """Extract 1h before kickoff through 4h after. Game-time entries flagged."""
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
                p2["is_game_hour"] = (kickoff <= st < kickoff + timedelta(hours=HOURS_GAME_WINDOW))
                out.append(p2)
        except (ValueError, AttributeError):
            continue
    return out


# EOF-CANARY 2026-07-04-cfb-recovery
