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


# EOF-CANARY 2026-10-07-big-board
