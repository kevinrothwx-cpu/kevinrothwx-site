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
        # Back the window start up 24h. Was previously "datetime.now(utc)"
        # which caused already-kicked-off games to drop off the slate the
        # moment they went past their scheduled time (the CFBD window
        # filter rejects kickoff < start_utc). Kevin flagged 2026-08-29:
        # Saturday afternoon slate was missing the noon-ET games because
        # they'd already started.
        #
        # Now: the window includes today's earlier kickoffs, and
        # _is_game_stale below drops them the next morning based on the
        # venue's local calendar day. That gives users the natural
        # "yesterday's games are gone by morning" behavior while keeping
        # today's in-progress games visible all day.
        start_date = datetime.now(timezone.utc) - timedelta(hours=24)

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
    # Separate HRRR/NBM cache — CONUS overlay only.
    venue_hrrr: dict[tuple[float, float], list[dict]] = {}

    # PARALLEL VENUE FETCH (2026-08-25). Was sequential per-game which meant
    # 50-70 unique venues × ~500-1500ms/fetch = ~40s for a full Saturday
    # slate. Under Twitter-link traffic this saturated gunicorn threads
    # (see cfb.cache _build_lock comment). Now we pre-collect unique venues
    # and fetch weather + NBM in parallel with a bounded worker pool.
    # After this step the game loop is pure assembly, no I/O.
    unique_venues = _collect_unique_venues(games)
    if unique_venues:
        _parallel_prefetch_venues(unique_venues, venue_weather, venue_hrrr)

    now_utc = datetime.now(timezone.utc)
    for g in games:
        _attach_weather_to_game(g, venue_weather, venue_hrrr)
        # Odds attachment — safe to run even when odds_list is empty.
        g["odds"] = _build_odds_for_game(g, odds_list, now_utc)

    odds_ct = sum(1 for g in games if g.get("odds"))
    print(
        f"[cfb.slate] built slate: {len(games)} games, "
        f"{len(venue_weather)} unique venues fetched, "
        f"{len(venue_hrrr)} NBM overlays, "
        f"{odds_ct} odds attached",
        flush=True,
    )
    return games


def _collect_unique_venues(games: list[dict]) -> list[tuple[float, float, bool]]:
    """Return one entry per unique (lat, lon) across the slate.
    Third field is nws_unsupported so the parallel fetcher can route to
    the right provider (WeatherAPI-only for international venues)."""
    seen: dict[tuple[float, float], bool] = {}
    for g in games:
        v = g.get("venue") or {}
        lat = v.get("lat"); lon = v.get("lon")
        if lat is None or lon is None:
            continue
        key = (round(lat, 4), round(lon, 4))
        if key in seen:
            continue
        seen[key] = bool(v.get("nws_unsupported"))
    return [(lat, lon, ns) for (lat, lon), ns in seen.items()]


def _parallel_prefetch_venues(
    venues: list[tuple[float, float, bool]],
    venue_weather: dict,
    venue_hrrr: dict,
) -> None:
    """Fetch weather + NBM for all unique venues in parallel. Populates
    the two caches in place. Bounded worker pool so we don't slam any
    single provider (NWS/WeatherAPI/Open-Meteo).

    Fault-tolerant: any single venue's failure is logged and the venue
    is left absent from the caches; the downstream _attach_weather_to_game
    will fall through to its own single-venue fetch (which will then hit
    the empty cache and try synchronously — but only for the failed ones,
    not the whole slate)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_one(v):
        lat, lon, nws_unsupported = v
        key = (round(lat, 4), round(lon, 4))
        try:
            if nws_unsupported:
                periods, source, err = _fetch_weatherapi_only(lat, lon)
            else:
                periods, source, err = _fetch_weather_with_fallback(lat, lon)
            hrrr = [] if nws_unsupported else (get_hrrr_periods(lat, lon) or [])
            return key, (periods, source, err), hrrr, None
        except Exception as e:
            return key, ([], "parallel-fetch-failed", str(e)), [], str(e)

    # 8 workers = comfortable on NWS (their guidance is <10 concurrent
    # req/s), and Open-Meteo (free tier is IP-rate-limited but 8 parallel
    # is well within tolerance). Bumping higher risks 429s.
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_fetch_one, v) for v in venues]
        for fut in as_completed(futures):
            try:
                key, weather_tuple, hrrr_list, err = fut.result()
                venue_weather[key] = weather_tuple
                venue_hrrr[key] = hrrr_list
                if err:
                    print(f"[cfb.slate] parallel fetch failed for {key}: {err}",
                          flush=True)
            except Exception as e:
                print(f"[cfb.slate] parallel worker crashed: {e}", flush=True)


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

    live_total    = match["total"]
    book_display  = match["book_display"]
    game_started  = kickoff_utc <= now_utc

    # Only record opening for pre-kickoff games. After kickoff the "current"
    # value from The Odds API is the live in-game total, which is stale
    # between our 25-min warmer cycles — don't record it as an opening for
    # a game we started tracking late.
    if not game_started:
        cfb_odds_storage.record_opening_if_new(event_id, live_total, book_display)
        # Also snapshot the CURRENT total each cycle so we have a "last
        # seen before kickoff" value to freeze at. Overwrites previous
        # kickoff-line snapshot each time; the final write just before
        # kickoff is what we lock and display through the game window.
        cfb_odds_storage.record_kickoff_line(event_id, live_total, book_display)

    opening_rec   = cfb_odds_storage.get_opening(event_id)
    opening_total = opening_rec["total"] if opening_rec else None

    # Pick the "current" total to display:
    #   pre-kickoff  → whatever The Odds API just returned (live movement)
    #   post-kickoff → the frozen kickoff-line snapshot (stable through
    #                  the game window; live in-game totals are meaningless
    #                  because we only poll every 25 min)
    if game_started:
        frozen = cfb_odds_storage.get_kickoff_line(event_id)
        if frozen is not None:
            current_total = frozen["total"]
            # Prefer the book that was live when we snapshotted the
            # kickoff line — usually the same, but be defensive.
            if frozen.get("book_display"):
                book_display = frozen["book_display"]
        else:
            # No pre-kickoff snapshot exists (game started before we
            # first tracked it). Fall back to the current live total —
            # not ideal, but better than showing nothing.
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
    """Extract 1h before kickoff through 4h after. Game-time entries flagged.

    Also adds hour_eastern ("2 PM", "10 AM") so templates can render a
    human-friendly hour header instead of the 24-hour military time that
    fell through when local_hour_label was absent."""
    if not periods:
        return []
    kickoff = kickoff_utc.replace(minute=0, second=0, microsecond=0)
    start = kickoff - timedelta(hours=HOURS_BEFORE_KICKOFF)
    end = kickoff + timedelta(hours=HOURS_GAME_WINDOW)
    from zoneinfo import ZoneInfo as _ZI
    _ET = _ZI("America/New_York")
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
                # Human-friendly Eastern hour label — "2 PM", "10 AM"
                try:
                    p2["hour_eastern"] = st.astimezone(_ET).strftime("%-I %p").lstrip("0")
                except Exception:
                    p2["hour_eastern"] = st.strftime("%H:%M")
                out.append(p2)
        except (ValueError, AttributeError):
            continue
    return out


# EOF-CANARY 2026-07-04-cfb-recovery
