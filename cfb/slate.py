"""
cfb.slate — build a CFB weather slate for a date window.

Combines the schedule fetcher (cfb/schedule.py) with weather attachment
to produce a normalized list of games each carrying:
  - Full team + venue + ranking info from the schedule
  - Kickoff-time weather snapshot
  - Hourly forecast strip around kickoff (for detail pages)
  - Weather source tag + error if any

Weather strategy (per design decision with Kevin, revised 2026-06-28):
    PRIMARY: NWS via cfb/nws_client (distinct UA, sequential pacing,
             circuit breaker on 429/503, permanent gridpoint cache)
    FALLBACK: WeatherAPI (paid tier, when NWS fails or circuit is open)

This matches the MLB and golf pattern. NWS gives more stable forecast
values between updates (curated human edits + ensemble averaging), which
matters because users mentally bookmark the cheat-sheet numbers and we
don't want them to oscillate on every page load. WeatherAPI is the
safety net so the site never breaks if NWS throttles us.

The cfb/nws_client wrapper exists specifically to keep CFB traffic
distinguishable from OVERcast and MLB traffic at the NWS server side,
with pacing + circuit breaker so a CFB Saturday burst can never compound
into an OVERcast incident.

Caching: per-venue (lat/lon) weather is cached for the duration of a
slate build, so games at the same stadium share a single fetch. Gridpoint
resolutions inside cfb/nws_client are cached permanently per venue.

Game shape (extends schedule.py's parse_cfb_event output):
    All schedule fields, plus:
    - "forecast":         kickoff snapshot dict (or None on failure)
    - "hourly":           list of period dicts around kickoff (or [])
    - "weather_source":   "nws" | "weatherapi-fallback" | "all-failed"
    - "weather_error":    None | str (last-source error message)
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from .schedule import get_cfb_week_games
from .nws_client import fetch_cfb_hourly

from mlb.weatherapi import fetch_weatherapi_hourly, find_weatherapi_period
from mlb.nws import extract_forecast, find_period_for_time


# ── Tuning constants ──────────────────────────────────────────────────────

# Hourly strip around kickoff for the detail page.
# Football games run ~3.5 hours. Show 1 hour before kickoff through end of
# game window so user sees pre-game and full-game conditions.
HOURS_BEFORE_KICKOFF = 1
HOURS_GAME_WINDOW    = 4   # buffer past kickoff to cover ~3.5h game + halftime


# ── Public entry point ───────────────────────────────────────────────────

def build_cfb_slate(start_date: Optional[datetime] = None,
                    days_ahead: int = 7) -> list[dict]:
    """Build the full weather-attached slate for a date window.

    Args:
        start_date: First day to include (datetime; date portion used).
                    Defaults to today (UTC date boundary).
        days_ahead: How many forward days to fetch. Default 7 covers the
                    typical CFB week (Tue MAC night through Sunday).

    Returns:
        List of game dicts sorted by kickoff time, each with weather
        attached. Empty list if no games or all fetches fail.
    """
    if start_date is None:
        start_date = datetime.now(timezone.utc)

    games = get_cfb_week_games(start_date, days_ahead=days_ahead)
    if not games:
        return []

    # Per-venue weather cache (shared across all games in this slate build).
    # Key: (lat, lon), value: (periods_list, source_str, error_str)
    venue_weather: dict[tuple[float, float], tuple[list[dict], str, Optional[str]]] = {}

    for g in games:
        _attach_weather_to_game(g, venue_weather)

    print(
        f"[cfb.slate] built slate: {len(games)} games, "
        f"{len(venue_weather)} unique venues fetched",
        flush=True,
    )
    return games


# ── Weather attachment ────────────────────────────────────────────────────

def _attach_weather_to_game(game: dict, venue_cache: dict) -> None:
    """Mutate game dict in place: add forecast, hourly, weather_source,
    weather_error fields."""
    venue = game.get("venue") or {}
    lat = venue.get("lat")
    lon = venue.get("lon")
    kickoff_utc = game.get("kickoff_utc")

    # No lat/lon = game at a venue not yet populated in our DB AND not
    # provided by ESPN's venue payload either. Leave weather null.
    if lat is None or lon is None or kickoff_utc is None:
        game["forecast"] = None
        game["hourly"] = []
        game["weather_source"] = "no-venue-data"
        game["weather_error"] = "Stadium lat/lon not available for this game"
        return

    # Cache hit or miss
    key = (round(lat, 4), round(lon, 4))
    if key in venue_cache:
        periods, source, err = venue_cache[key]
    else:
        periods, source, err = _fetch_weather_with_fallback(lat, lon)
        venue_cache[key] = (periods, source, err)

    if not periods:
        game["forecast"] = None
        game["hourly"] = []
        game["weather_source"] = source or "all-failed"
        game["weather_error"] = err
        return

    # Kickoff snapshot.
    # NWS periods are already normalized via extract_forecast inside
    # cfb/nws_client; find_period_for_time picks the right one by time.
    # WeatherAPI uses its own period finder.
    if source == "nws":
        snapshot = find_period_for_time(periods, kickoff_utc)
    else:  # weatherapi-fallback
        snapshot = find_weatherapi_period(periods, kickoff_utc)

    # Hourly window: 1h before kickoff through 4h after
    hourly = _hourly_window(periods, kickoff_utc)

    game["forecast"] = snapshot
    game["hourly"] = hourly
    game["weather_source"] = source
    game["weather_error"] = err


# ── Provider fetch with fallback ──────────────────────────────────────────

def _fetch_weather_with_fallback(lat: float, lon: float) -> tuple[list[dict], str, Optional[str]]:
    """Try NWS first (primary for CFB), fall back to WeatherAPI on failure.

    NWS goes through cfb/nws_client which adds pacing, circuit breaker,
    and distinct User-Agent to keep CFB traffic distinguishable from
    OVERcast at the NWS server side. fetch_cfb_hourly returns None on
    any failure (rate limit, timeout, bad response, circuit open) — the
    caller falls back to WeatherAPI in any of those cases.

    Returns (periods, source_label, error_msg).
    Empty periods list means BOTH sources failed.
    """
    # Layer 1: NWS primary via the paced/circuit-broken client
    try:
        periods = fetch_cfb_hourly(lat, lon)
        if periods:
            return periods, "nws", None
        nws_err = "NWS returned None (circuit open, rate-limited, or empty)"
    except Exception as e:
        nws_err = str(e)
        print(f"[cfb.slate] NWS client raised for {lat},{lon}: {e} — falling back to WeatherAPI",
              flush=True)

    # Layer 2: WeatherAPI fallback
    try:
        periods = fetch_weatherapi_hourly(lat, lon)
        if periods:
            print(f"[cfb.slate] WeatherAPI fallback ok for {lat},{lon}", flush=True)
            return periods, "weatherapi-fallback", None
        return [], "all-failed", f"NWS: {nws_err}; WeatherAPI returned empty"
    except Exception as wa_err:
        return [], "all-failed", f"NWS: {nws_err}; WeatherAPI: {wa_err}"


# ── Hourly window extraction ──────────────────────────────────────────────

def _hourly_window(periods: list[dict], kickoff_utc: datetime) -> list[dict]:
    """Extract the hourly forecast for the game window around kickoff.

    Returns 1h before kickoff through 4h after (5-6 entries typical).
    Each entry is a period dict matching the provider's hourly shape.
    Game-time entries are flagged with is_game_hour=True for template use.
    """
    """Extract the hourly forecast for the game window around kickoff.

    Returns 1h before kickoff through 4h after (5-6 entries typical).
    Each entry is a period dict matching the provider's hourly shape.
    Game-time entries are flagged with is_game_hour=True for template use.
    """
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
