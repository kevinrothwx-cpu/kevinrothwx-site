"""big_board — data for "The Big Board" game-weather map (PREVIEW, 2026-10-07).

One flat list of every upcoming NFL, college football and MLB game with its
stadium location and the forecast we already show on the slate pages. The
map page (/lab/big-board) draws a dot per game and lays official NOAA
layers (NHC storm cone/track, radar) underneath.

PREVIEW RULES (see app.py routes):
    - Not linked anywhere, not in the sitemap, served with a noindex header.
    - Reads the warm slate caches only (allow_build=False): opening the map
      can never trigger NWS / Odds API calls or a slow rebuild.
    - Read-only. Never writes.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
_CACHE_SECONDS = 60
_cache: dict = {"at": 0.0, "data": None}
_lock = threading.Lock()

_COMPASS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")


def _num(v) -> Optional[int]:
    try:
        return None if v is None else int(round(float(v)))
    except (TypeError, ValueError):
        return None


def _compass(deg) -> Optional[str]:
    d = _num(deg)
    return None if d is None else _COMPASS[int(((d % 360) + 11.25) // 22.5) % 16]


def _flags(fc: Optional[dict]) -> list[str]:
    """Weather flags for dot color + legend. Same spirit as the site's cards."""
    if not fc:
        return []
    out = []
    wind, gust = _num(fc.get("wind_speed")) or 0, _num(fc.get("gust"))
    rain, temp = _num(fc.get("precip_pct")) or 0, _num(fc.get("temp"))
    if wind >= 15 or (gust or 0) >= 25:
        out.append("wind")
    if rain >= 50:
        out.append("rain")
    if temp is not None and temp <= 32:
        out.append("cold")
    if temp is not None and temp >= 90:
        out.append("heat")
    return out


def _entry(sport, away, home, ko, venue_name, city, lat, lon, roof, fc, url):
    if lat is None or lon is None or ko is None:
        return None
    if ko.tzinfo is None:
        ko = ko.replace(tzinfo=timezone.utc)
    ko_et = ko.astimezone(ET)
    indoor = (roof or "").lower() in ("fixed_dome", "dome", "indoor")
    f = None if (indoor or not fc) else {
        "temp": _num(fc.get("temp")),
        "wind": _num(fc.get("wind_speed")),
        "gust": _num(fc.get("gust")),
        "dir": _compass(fc.get("wind_deg")),
        "rain": _num(fc.get("precip_pct")),
        "sky": fc.get("short_forecast") or "",
    }
    return {
        "sport": sport,
        "away": away, "home": home,
        "kickoff_utc": ko.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "day": ko_et.strftime("%Y-%m-%d"),
        "day_label": ko_et.strftime("%a %b %-d"),
        "time_label": ko_et.strftime("%-I:%M %p ET"),
        "venue": venue_name or "", "city": city or "",
        "lat": float(lat), "lon": float(lon),
        "roof": (roof or "open").lower(), "indoor": indoor,
        "forecast": f,
        "flags": [] if indoor else _flags(fc),
        "url": url,
    }


def _football(sport, getter, prefix):
    out = []
    try:
        games, _ = getter(allow_build=False)
    except Exception as e:
        print(f"[big_board] {sport} slate unavailable: {e}", flush=True)
        return out
    for g in games or []:
        try:
            v = g.get("venue") or {}
            date = g.get("kickoff_date_eastern") or ""
            url = g.get("url_path") or (f"{prefix}/{date}/{g.get('slug')}" if g.get("slug") else prefix)
            e = _entry(sport,
                       (g.get("away") or {}).get("short") or (g.get("away") or {}).get("name"),
                       (g.get("home") or {}).get("short") or (g.get("home") or {}).get("name"),
                       g.get("kickoff_utc"), v.get("name"), v.get("city"),
                       v.get("lat"), v.get("lon"), v.get("roof_type") or v.get("roof"),
                       g.get("forecast"), url)
            if e:
                out.append(e)
        except Exception as ex:
            print(f"[big_board] {sport} game skipped: {ex}", flush=True)
    return out


def _mlb():
    out = []
    try:
        from mlb.cache import get_slate
    except Exception:
        return out
    today = datetime.now(ET)
    for d in (today, today + timedelta(days=1)):
        ds = d.strftime("%Y-%m-%d")
        try:
            slate, _ = get_slate(ds, allow_build=False)
        except Exception as e:
            print(f"[big_board] mlb {ds} unavailable: {e}", flush=True)
            continue
        for g in slate or []:
            try:
                park = g.get("park") or {}
                e = _entry("mlb", g.get("away_name"), g.get("home_name"),
                           g.get("first_pitch_utc"), g.get("venue"), park.get("city"),
                           park.get("lat"), park.get("lon"), park.get("roof_type"),
                           g.get("forecast"), f"/mlb/{ds}/{g.get('slug')}")
                if e:
                    out.append(e)
            except Exception as ex:
                print(f"[big_board] mlb game skipped: {ex}", flush=True)
    return out


def build_board_data() -> dict:
    """All upcoming games across NFL, CFB and MLB. Cached 60s in-process."""
    with _lock:
        if _cache["data"] is not None and time.time() - _cache["at"] < _CACHE_SECONDS:
            return _cache["data"]
    from nfl.cache import get_nfl_slate
    from cfb.cache import get_cfb_slate
    now = datetime.now(timezone.utc)
    games = (_football("nfl", get_nfl_slate, "/nfl")
             + _football("cfb", get_cfb_slate, "/ncaaf")
             + _mlb())
    # Upcoming only, plus anything that kicked off in the last 4 hours.
    cutoff = (now - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
    games = [g for g in games if g["kickoff_utc"] >= cutoff]
    games.sort(key=lambda g: g["kickoff_utc"])
    data = {"generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "games": games}
    with _lock:
        _cache.update(at=time.time(), data=data)
    return data



# ── HRRR "future radar" (2026-10-07) ────────────────────────────────────────
# Iowa Environmental Mesonet renders NCEP HRRR simulated reflectivity as map
# tiles, every 15 minutes out to 18 hours, with a rain/snow/ice color ramp
# (REFP). Free, and IEM explicitly allows commercial use. The map needs the
# model run time so every frame comes from the SAME run; IEM recommends
# reading it from this metadata file rather than using "latest" in tile URLs.
_HRRR_META_URL = "https://mesonet.agron.iastate.edu/data/gis/images/4326/hrrr/refp_1080.json"
_hrrr_cache: dict = {"at": 0.0, "data": None}


def hrrr_latest() -> dict:
    """{'init': 'YYYYMMDDHHMI', 'init_utc': iso} for the latest HRRR run IEM
    has finished processing. Cached 10 minutes. Never raises."""
    with _lock:
        if _hrrr_cache["data"] and time.time() - _hrrr_cache["at"] < 600:
            return _hrrr_cache["data"]
    out = {"init": None, "init_utc": None}
    try:
        import requests
        r = requests.get(_HRRR_META_URL, timeout=8,
                         headers={"User-Agent": "mysportsweather.com big-board"})
        r.raise_for_status()
        iso = r.json().get("model_init_utc")
        dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        out = {"init": dt.strftime("%Y%m%d%H%M"), "init_utc": iso}
        with _lock:
            _hrrr_cache.update(at=time.time(), data=out)
    except Exception as e:
        print(f"[big_board] HRRR metadata unavailable: {type(e).__name__}: {e}", flush=True)
    return out


# EOF-CANARY 2026-10-07-big-board
