"""future_radar — per-game "Future radar" popup support (MLB first, 2026-10-07).

The popup (templates/mlb/_future_radar.html) loops the last hour of real
NEXRAD radar around the ballpark, then plays the HRRR model's simulated
radar through the end of the game. All imagery comes straight from Iowa
State's Environmental Mesonet (free; commercial use allowed). This module
only answers one question per game: SHOULD the button show?

AGREEMENT CHECK (currently OFF, see AGREEMENT_CHECK; originally Kevin
2026-10-07: future radar must not contradict the
hourly rain chances). Before the button appears we compare the HRRR's own
hourly rain at the ballpark during game hours with the game-window rain
chance we already display:
    - rain chance >= 60% but the HRRR is dry all game      -> hide
    - rain chance <= 20% but the HRRR has heavy rain       -> hide
    - HRRR point data unavailable                          -> hide
Anything else shows. A shown loop therefore backs up the forecast.

ELIGIBILITY: open-air parks only (retractables and domes skip), first
pitch within the HRRR's 18-hour range, game not over.

Cost: one Open-Meteo HRRR call per ballpark per hour (cached), using the
same paid/free endpoint logic as hrrr.py. The popup itself adds no load.
"""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

_IEM_INIT_URL = "https://mesonet.agron.iastate.edu/data/gis/images/4326/hrrr/refd_1080.json"
_OM_FREE = "https://api.open-meteo.com/v1/forecast"
_OM_PAID = "https://customer-api.open-meteo.com/v1/forecast"
_UA = "kevinrothwx.com (contact: kevinrothwx@gmail.com)"

WET_IN = 0.01        # any measurable rain in an hour
HEAVY_IN = 0.10      # "heavy" for this check: a tenth of an inch in an hour
HIGH_POP = 60
LOW_POP = 20
GAME_HOURS = 3.5
# Kevin, 2026-10-07: OFF for now. Show the HRRR whenever it's available, even
# when it disagrees with our rain chance. Flip to True to re-enable the check
# described in the module docstring (it also skips the Open-Meteo call).
AGREEMENT_CHECK = False
HRRR_RANGE_H = 18

_lock = threading.Lock()
_init_cache: dict = {"at": 0.0, "data": None}
_point_cache: dict = {}      # "lat,lon" -> (fetched_at, {iso_hour: inches})


def hrrr_init() -> Optional[datetime]:
    """Latest HRRR run IEM has rendered (REFD product). Cached 10 min."""
    with _lock:
        if _init_cache["data"] and time.time() - _init_cache["at"] < 600:
            return _init_cache["data"]
    try:
        import requests
        r = requests.get(_IEM_INIT_URL, timeout=8, headers={"User-Agent": _UA})
        r.raise_for_status()
        dt = datetime.strptime(r.json()["model_init_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        with _lock:
            _init_cache.update(at=time.time(), data=dt)
        return dt
    except Exception as e:
        print(f"[future_radar] IEM HRRR init unavailable: {type(e).__name__}: {e}", flush=True)
        return None


def _hrrr_hourly_rain(lat: float, lon: float) -> Optional[dict]:
    """{hour_utc_iso: inches} from the HRRR at this point. Cached 1 hour."""
    key = f"{lat:.3f},{lon:.3f}"
    with _lock:
        hit = _point_cache.get(key)
        if hit and time.time() - hit[0] < 3600:
            return hit[1]
    import requests
    params = {"latitude": lat, "longitude": lon, "hourly": "precipitation",
              "models": "ncep_hrrr_conus", "precipitation_unit": "inch",
              "timezone": "UTC", "forecast_days": 2}
    api_key = (os.environ.get("OPEN_METEO_API_KEY") or "").strip()
    data = None
    for paid in ([True, False] if api_key else [False]):
        try:
            p = dict(params)
            if paid:
                p["apikey"] = api_key
            r = requests.get(_OM_PAID if paid else _OM_FREE, params=p, timeout=10,
                             headers={"User-Agent": _UA})
            if r.status_code == 200:
                data = r.json()
                break
        except Exception as e:
            print(f"[future_radar] HRRR point fetch failed ({'paid' if paid else 'free'}): {e}", flush=True)
    if not data:
        return None
    h = data.get("hourly") or {}
    out = {}
    for t, v in zip(h.get("time") or [], h.get("precipitation") or []):
        if v is not None:
            out[t + ":00Z" if len(t) == 16 else t] = float(v)
    with _lock:
        _point_cache[key] = (time.time(), out)
    return out


def decide(lat, lon, first_pitch_utc: datetime, pop_pct, roof_type: str,
           now: Optional[datetime] = None) -> dict:
    """Return {'show': bool, 'reason': str, ...popup config when shown}."""
    now = now or datetime.now(timezone.utc)
    if (roof_type or "").lower() not in ("open_air", "open"):
        return {"show": False, "reason": "roof"}
    if lat is None or lon is None or first_pitch_utc is None:
        return {"show": False, "reason": "no location"}
    end = first_pitch_utc + timedelta(hours=GAME_HOURS)
    if end <= now:
        return {"show": False, "reason": "game over"}
    init = hrrr_init()
    if not init:
        return {"show": False, "reason": "model unavailable"}
    if end > init + timedelta(hours=HRRR_RANGE_H):
        return {"show": False, "reason": "beyond HRRR range"}
    if not AGREEMENT_CHECK:
        return _config(lat, lon, first_pitch_utc, end, init, "available")
    rain = _hrrr_hourly_rain(float(lat), float(lon))
    if rain is None:
        return {"show": False, "reason": "HRRR point data unavailable"}
    start_hr = first_pitch_utc.replace(minute=0, second=0, microsecond=0)
    hours = [start_hr + timedelta(hours=i) for i in range(int(GAME_HOURS) + 1)]
    vals = [rain.get(h.strftime("%Y-%m-%dT%H:%M:00Z"), 0.0) for h in hours]
    wet, heavy = any(v >= WET_IN for v in vals), any(v >= HEAVY_IN for v in vals)
    pop = int(pop_pct or 0)
    if pop >= HIGH_POP and not wet:
        return {"show": False, "reason": f"disagrees: {pop}% chance but HRRR dry"}
    if pop <= LOW_POP and heavy:
        return {"show": False, "reason": f"disagrees: {pop}% chance but HRRR heavy rain"}
    return _config(lat, lon, first_pitch_utc, end, init, "agrees")


def _config(lat, lon, first_pitch_utc, end, init, reason) -> dict:
    return {
        "show": True, "reason": reason,
        "lat": float(lat), "lon": float(lon),
        "first_pitch_utc": first_pitch_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_utc": end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "init": init.strftime("%Y%m%d%H%M"),
        "init_utc": init.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# EOF-CANARY 2026-10-07-future-radar
