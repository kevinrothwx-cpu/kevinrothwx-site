"""
mlb.weatherapi — fallback weather provider for non-US venues.

Replaces the earlier Open-Meteo integration. Kevin already pays for
WeatherAPI.com (100K calls/month free tier), and is using it from OVERcast
for international locations. We use the same key.

Coverage strategy:
    - NWS for US venues (rate-safe, no key, high quality)
    - WeatherAPI.com for everything else (Toronto, Mexico, World Cup
      international venues, future PGA majors abroad)

Quota math: even at peak (World Cup with 4 matches/day at 4 international
venues, plus Toronto MLB, plus PGA), we use <10K calls/month. Well under
the 100K cap.

Output shape matches mlb.nws.extract_forecast() so downstream code is
provider-agnostic.
"""

from __future__ import annotations

import os
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional


WEATHERAPI_FORECAST_URL = "https://api.weatherapi.com/v1/forecast.json"

# Compass direction handling — WeatherAPI returns numeric `wind_degree` already
# so no conversion needed. But we keep the same wind_deg key downstream wants.


def _api_key() -> str:
    """Read the API key from env. Raises if missing."""
    key = os.environ.get("WEATHERAPI_KEY", "")
    if not key:
        raise RuntimeError(
            "WEATHERAPI_KEY env var not set. "
            "Get a free key at https://www.weatherapi.com/ and set it on Render."
        )
    return key


def fetch_weatherapi_hourly(lat: float, lon: float) -> list[dict]:
    """
    Fetch hourly forecast for a lat/lon and reshape to per-hour dicts
    matching the NWS-extracted forecast shape.

    Returns up to ~3 days of hourly periods (72 entries).
    """
    resp = requests.get(
        WEATHERAPI_FORECAST_URL,
        params={
            "key":   _api_key(),
            "q":     f"{lat},{lon}",
            "days":  3,
            "aqi":   "no",
            "alerts":"no",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    forecast = data.get("forecast", {}).get("forecastday", [])
    periods: list[dict] = []

    # Detect the venue's local timezone offset from the WeatherAPI response
    # so we can convert their "naive local" times to proper UTC.
    tz_id = data.get("location", {}).get("tz_id")  # e.g. "America/Toronto"
    if tz_id:
        try:
            from zoneinfo import ZoneInfo
            local_tz = ZoneInfo(tz_id)
        except Exception:
            local_tz = timezone.utc
    else:
        local_tz = timezone.utc

    for day in forecast:
        for h in day.get("hour", []):
            # WeatherAPI returns "time" as local naive ISO ("2026-06-08 18:00")
            time_str = h.get("time", "")
            try:
                naive_dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
                local_dt = naive_dt.replace(tzinfo=local_tz)
                start_utc = local_dt.astimezone(timezone.utc)
            except ValueError:
                continue
            end_utc = start_utc + timedelta(hours=1)

            periods.append({
                "start_time":     start_utc.isoformat(),
                "end_time":       end_utc.isoformat(),
                "temp":           round(float(h.get("temp_f", 70))),
                "dew":            round(float(h.get("dewpoint_f", 50))),
                "wind_speed":     round(float(h.get("wind_mph", 0))),
                "wind_deg":       float(h.get("wind_degree", 0)),
                "precip_pct":     int(h.get("chance_of_rain", 0)),
                "humidity_pct":   int(h.get("humidity", 0)),
                "short_forecast": h.get("condition", {}).get("text", ""),
            })

    return periods


def find_weatherapi_period(periods: list[dict], target_utc: datetime) -> Optional[dict]:
    """Mirror of nws.find_period_for_time / open_meteo.find_open_meteo_period."""
    if not periods:
        return None

    rounded = target_utc.replace(second=0, microsecond=0)
    if rounded.minute >= 30:
        rounded = rounded.replace(minute=0) + timedelta(hours=1)
    else:
        rounded = rounded.replace(minute=0)

    for p in periods:
        start = datetime.fromisoformat(p["start_time"])
        end   = datetime.fromisoformat(p["end_time"])
        if start <= rounded < end:
            return p

    # Fallback: first future period
    future = [p for p in periods if datetime.fromisoformat(p["start_time"]) >= rounded]
    return future[0] if future else periods[0]
