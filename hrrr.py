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
    - Horizon: ~48-60 hours via the gfs_hrrr model. Rounds / races more
      than ~48 h out will have no HRRR coverage and the toggle won't show.

OUTPUT FORMAT:
    Pre-normalized to the same period dict shape as mlb.nws.extract_forecast,
    so existing _hourly_window / _periods_for_round_day helpers slice the
    HRRR list interchangeably with NWS. Includes a "gust" field (mph)
    from wind_gusts_10m, populated when HRRR returns it.
"""

from __future__ import annotations

import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional


# Open-Meteo serves two endpoints:
#   - api.open-meteo.com:           free, anonymous, IP-rate-limited
#   - customer-api.open-meteo.com:  paid, API-key authenticated, no IP throttle
# When OPEN_METEO_API_KEY env var is set we use the paid endpoint and
# include the key as a query param. When it isn't, we fall back to the
# free endpoint (where Render's shared IP gets throttled).
OPEN_METEO_FREE_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_PAID_URL = "https://customer-api.open-meteo.com/v1/forecast"

HRRR_USER_AGENT = "kevinrothwx.com (contact: kevinrothwx@gmail.com)"

# Backoff windows — how long to refuse retries after a failure. Open-Meteo's
# free tier rate-limits per IP, and Render uses shared egress, so a 429 can
# happen even when our own request volume is tiny. Long backoff on 429
# stops us from hammering them and getting throttled harder; short backoff
# on other errors (network blip, 5xx) so we recover quickly when they pass.
_BACKOFF_429 = timedelta(hours=1)
_BACKOFF_OTHER = timedelta(minutes=10)

# (lat,lon) key → list of period dicts. Cleared by the per-sport warmers
# every 25 min to get fresh HRRR runs.
_hrrr_cache: dict[str, list] = {}

# (lat,lon) key → datetime when we're allowed to retry. NOT cleared by the
# warmer — backoffs need to survive cache flushes to be effective. Cleared
# only on success in get_hrrr_periods.
_backoff_until: dict[str, datetime] = {}


def clear_periods_cache() -> None:
    """Called by background warmers (golf, nascar) to force fresh fetches.
    Backoff timestamps are intentionally preserved — a warmer cycle alone
    is not a signal that rate-limiting has lifted."""
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

    # Respect backoff. Survives warmer cache clears so we don't keep
    # hammering Open-Meteo when they're already telling us to stop.
    now = datetime.now(timezone.utc)
    backoff_until = _backoff_until.get(key)
    if backoff_until and now < backoff_until:
        return None

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,dewpoint_2m,"
                  "precipitation_probability,wind_speed_10m,"
                  "wind_direction_10m,wind_gusts_10m",
        # Open-Meteo renamed their HRRR identifier from "hrrr_conus" to
        # "gfs_hrrr" at some point. The latter is a blended product that
        # uses HRRR for the first ~48-60 hours within CONUS and returns
        # null values beyond that horizon (which our parser drops below
        # where temps[i] is None).
        "models": "gfs_hrrr",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        # forecast_days=3 returns today + next 2 days. HRRR's model
        # horizon is ~48-60 hours, so the 3rd day will often be partially
        # null — our parser drops null entries. The reason we need 3
        # (not 2) is that Open-Meteo counts from today 00:00 UTC; for a
        # tournament starting in 2-3 days, forecast_days=2 cuts off
        # before the round and we'd never have HRRR for it.
        "forecast_days": 3,
    }
    # Try paid endpoint first if an API key is configured. If it returns ANY
    # error (auth, quota, server error, network), fall back to the free
    # endpoint instead of failing outright. This protects against the
    # situation Kevin hit on 2026-06-24 where HRRR went site-wide dark
    # because the paid endpoint had some kind of issue our code couldn't
    # see (no error logged) and the slate cache got stuck with no HRRR
    # data even though the warmer was still running.
    api_key = (os.environ.get("OPEN_METEO_API_KEY") or "").strip()
    headers = {"User-Agent": HRRR_USER_AGENT}

    def _fetch(use_paid):
        endpoint = OPEN_METEO_PAID_URL if use_paid else OPEN_METEO_FREE_URL
        p = dict(params)
        if use_paid and api_key:
            p["apikey"] = api_key
        return requests.get(endpoint, params=p, headers=headers, timeout=15)

    resp = None
    endpoint_used = None
    try:
        if api_key:
            try:
                resp = _fetch(use_paid=True)
                endpoint_used = "paid"
                if resp.status_code != 200:
                    # Non-2xx from paid — log and fall through to free
                    print(f"[hrrr] paid endpoint returned {resp.status_code} for "
                          f"{lat},{lon}: {resp.text[:120]!r} — trying free fallback",
                          flush=True)
                    resp = None
                    endpoint_used = None
            except Exception as paid_err:
                print(f"[hrrr] paid endpoint failed for {lat},{lon}: {paid_err} "
                      f"— trying free fallback", flush=True)
                resp = None
                endpoint_used = None
        if resp is None:
            resp = _fetch(use_paid=False)
            endpoint_used = "free"

        # Detect rate-limit explicitly so we can apply a longer backoff
        # than other transient errors.
        if resp.status_code == 429:
            _backoff_until[key] = now + _BACKOFF_429
            print(f"[hrrr] 429 rate-limited for {lat},{lon} on {endpoint_used} "
                  f"endpoint — backing off until {_backoff_until[key].isoformat()}",
                  flush=True)
            _hrrr_cache[key] = []
            return None
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        _backoff_until[key] = now + _BACKOFF_OTHER
        print(f"[hrrr] fetch failed for {lat},{lon} on {endpoint_used or 'unknown'} "
              f"endpoint: {e} — short backoff until {_backoff_until[key].isoformat()}",
              flush=True)
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
    gusts = hourly.get("wind_gusts_10m") or []

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
            "gust":           round(float(gusts[i])) if i < len(gusts) and gusts[i] is not None else None,
            "precip_pct":     int(pops[i]) if i < len(pops) and pops[i] is not None else 0,
            "humidity_pct":   int(rhs[i]) if i < len(rhs) and rhs[i] is not None else None,
            "short_forecast": "",
        })

    if not periods:
        print(f"[hrrr] empty period list for {lat},{lon}", flush=True)
        _hrrr_cache[key] = []
        return None

    # Success — clear any leftover backoff so future cycles run normally
    _backoff_until.pop(key, None)
    _hrrr_cache[key] = periods
    print(f"[hrrr] fetched {len(periods)} periods for {lat},{lon} via {endpoint_used} endpoint", flush=True)
    return periods
