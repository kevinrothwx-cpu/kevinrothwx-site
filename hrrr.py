"""
hrrr.py — High-Resolution Rapid Refresh (HRRR) forecast via Open-Meteo.

WHY this exists alongside the NWS module:
    NWS publishes a blend of operational forecast model output. HRRR is a
    separate 3-km CONUS model that re-runs every hour with newer data.
    For short-range (≤48 h) storm timing and surface wind detail, HRRR is
    often the better read. We surface it as a SECONDARY layer next to the
    NWS forecast on PGA and NASCAR pages — a toggle reveals it.

DATA SOURCE:
    Open-Meteo serves HRRR output as clean JSON. Free, no API key.
    Docs: https://open-meteo.com/en/docs/hrrr-api

COVERAGE:
    - Domain: continental US only. Outside CONUS → returns None and the
      caller should fall back to NWS / WeatherAPI alone.
    - Horizon: ~48 hours via the hrrr_conus model. Rounds / races more
      than ~48 h out will have no HRRR coverage and the toggle won't show.

OUTPUT FORMAT:
    Pre-normalized to the same period dict shape as mlb.nws.extract_forecast,
    so existing _hourly_window / _periods_for_round_day helpers slice the
    HRRR list interchangeably with NWS.
"""

from __future__ import annotations

import requests
from typing import Optional


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
HRRR_USER_AGENT = "kevinrothwx.com (contact: kevinrothwx@gmail.com)"

# (lat,lon) key → list of period dicts. Cleared by the per-sport warmers.
_hrrr_cache: dict[str, list] = {}


def clear_periods_cache() -> None:
    """Called by background warmers (golf, nascar) to force fresh fetches."""
    _hrrr_cache.clear()


def _is_conus(lat: float, lon: float) -> bool:
    """HRRR domain bounding box. Generous to avoid false negatives at edges."""
    return 24.0 <= lat <= 50.0 and -125.0 <= lon <= -66.5


def get_hrrr_periods(lat: float, lon: float) -> Optional[list]:
    """
    Fetch and cache HRRR hourly periods for a lat/lon. Returns a list of
    period dicts (shape matches mlb.nws.extract_forecast output) or None
    if outside CONUS or on fetch failure.

    Caching mirrors mlb.nws.get_nws_periods: lookup by lat/lon, cache miss
    triggers fetch + store, cache hit returns the stored list. The warmer
    clears this every 25 min so each cycle gets a fresh HRRR run.

    A previous failure is cached as an empty list — that way a single
    Open-Meteo blip doesn't trigger a retry on every subsequent page load
    in the same warmer cycle.
    """
    if not _is_conus(lat, lon):
        return None

    key = f"{lat:.4f},{lon:.4f}"
    if key in _hrrr_cache:
        cached = _hrrr_cache[key]
        return cached if cached else None  # empty list = previous failure

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,dewpoint_2m,"
                  "precipitation_probability,wind_speed_10m,wind_direction_10m",
        "models": "hrrr_conus",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "forecast_days": 2,
    }
    try:
        resp = requests.get(
            OPEN_METEO_URL,
            params=params,
            headers={"User-Agent": HRRR_USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[hrrr] fetch failed for {lat},{lon}: {e}", flush=True)
        _hrrr_cache[key] = []
        return None

    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    rhs   = hourly.get("relative_humidity_2m") or []
    dews  = hourly.get("dewpoint_2m") or []
    pops  = hourly.get("precipitation_probability") or []
    winds = hourly.get("wind_speed_10m") or []
    wdirs = hourly.get("wind_direction_10m") or []

    periods = []
    for i, t_str in enumerate(times):
        if i >= len(temps) or temps[i] is None:
            continue
        # Open-Meteo returns "YYYY-MM-DDTHH:MM" in UTC when timezone unset.
        # Append seconds + explicit UTC offset so downstream fromisoformat()
        # parses without ambiguity.
        start_time = f"{t_str}:00+00:00"
        periods.append({
            "start_time":     start_time,
            "temp":           round(float(temps[i])),
            "dew":            round(float(dews[i])) if i < len(dews) and dews[i] is not None else None,
            "wind_speed":     round(float(winds[i])) if i < len(winds) and winds[i] is not None else 0,
            "wind_deg":       float(wdirs[i]) if i < len(wdirs) and wdirs[i] is not None else 0,
            "precip_pct":     int(pops[i]) if i < len(pops) and pops[i] is not None else 0,
            "humidity_pct":   int(rhs[i]) if i < len(rhs) and rhs[i] is not None else None,
            "short_forecast": "",
        })

    if not periods:
        print(f"[hrrr] empty period list for {lat},{lon}", flush=True)
        _hrrr_cache[key] = []
        return None

    _hrrr_cache[key] = periods
    print(f"[hrrr] fetched {len(periods)} periods for {lat},{lon}", flush=True)
    return periods
