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

from cfb.nws_client import fetch_cfb_hourly
from mlb.weatherapi import fetch_weatherapi_hourly, find_weatherapi_period
from mlb.nws import find_period_for_time
from hrrr import get_hrrr_periods


# NFL game window: 1h before through 4h after kickoff.
# Football is ~3.5 hours; 4h buffer covers halftime + late TV slate overrun.
HOURS_BEFORE_KICKOFF = 1
HOURS_GAME_WINDOW    = 4
HOURS_GAME_HIGHLIGHT = 3   # only 3 in-game hours get highlighted, per Kevin


def build_nfl_slate(start_date: Optional[datetime] = None,
                    days_ahead: int = 8) -> list[dict]:
    """Build full weather-attached NFL slate.

    Default 8-day window covers Thu→Mon spread + buffer."""
    if start_date is None:
        start_date = datetime.now(timezone.utc)

    games = get_nfl_week_games(start_date, days_ahead=days_ahead)
    if not games:
        return []

    venue_weather: dict[tuple[float, float], tuple[list[dict], str, Optional[str]]] = {}

    for g in games:
        _attach_weather_to_game(g, venue_weather)

    print(
        f"[nfl.slate] built slate: {len(games)} games, "
        f"{len(venue_weather)} unique outdoor venues fetched",
        flush=True,
    )
    return games


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
                p2["is_game_hour"] = (kickoff <= st < kickoff + timedelta(hours=HOURS_GAME_WINDOW))
                out.append(p2)
        except (ValueError, AttributeError):
            continue
    return out
