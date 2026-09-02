"""synoptic_live_client.py — REFERENCE IMPLEMENTATION for OVERcast Live.

This file is not imported by MSW. It exists to be copied into OVERcast
Live, so that service starts from a client with the safety properties
already built in rather than growing them after something breaks.

THE ONE RULE
    One batched HTTP request per poll cycle, for ALL venues at once.

    Synoptic's Latest service accepts a comma-separated station list and
    allows up to 75,000 stations per call, so 87 CFB stadiums is a single
    request — not 87. Everything about the cost and rate-limit story
    depends on that. A naive per-venue loop would be 87x the requests and
    would reintroduce exactly the burst problem this design exists to
    avoid.

WHY SYNOPTIC RATHER THAN NWS
    MSW depends on api.weather.gov, api.weatherapi.com and open-meteo.com.
    Render's outbound IPs are shared across every service in a region and
    across other Render customers, so a second service over-fetching any
    of those three can get MSW throttled. Synoptic is a vendor MSW touches
    nowhere, so Live's request budget is fully decoupled from MSW's.

    Corollary: do NOT "optimize" this later by falling back to NWS when
    Synoptic is down. That reintroduces the coupling. Serve stale data or
    serve nothing.

OBSERVATION FRESHNESS
    NOAA high-frequency METAR (hfmetars, on by default) updates roughly
    every 5 minutes at airport stations. That is what makes "it started
    raining" detectable on a useful timescale.

    Everything returned here is an OBSERVATION, not a forecast, and it is
    from the nearest station — typically an airport a few miles from the
    stadium, not the stadium itself. Present it as "conditions at KATL,
    6.2 mi away, 4 minutes ago", never as conditions on the field.
"""

from __future__ import annotations

import json
import os
import random
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import requests

LATEST_URL = "https://api.synopticdata.com/v2/stations/latest"

# Reject observations older than this. A station that has gone quiet is
# worse than no station, because a stale "clear" reading during a
# downpour is confidently wrong.
MAX_OBS_AGE_MIN = 45

# Ask the API to filter server-side too, so we transfer less.
WITHIN_MINUTES = 90

REQUEST_TIMEOUT_SEC = 25
MAX_RETRIES = 4

# Variables Live actually uses. Keep this list tight — every extra
# variable is more payload on every poll.
VARS = ",".join([
    "air_temp",
    "wind_speed",
    "wind_gust",
    "wind_direction",
    "relative_humidity",
    "weather_condition",       # present weather: "rain", "snow", etc.
    "precip_accum_one_hour",
])

# Present-weather strings that mean precipitation is falling NOW.
_WET_TOKENS = ("rain", "snow", "drizzle", "shower", "thunder", "sleet",
               "hail", "ice", "freezing", "mist", "precip")


class SynopticLiveClient:
    """Batched, rate-limit-aware observation fetcher.

    Thread-safe. Serializes concurrent callers behind a single lock so
    that N game threads asking for conditions produce ONE upstream
    request, not N. This is the single most important property here.
    """

    def __init__(self, token: Optional[str] = None,
                 min_seconds_between_calls: float = 60.0):
        self.token = (token or os.environ.get("SYNOPTIC_TOKEN", "")).strip()
        if not self.token:
            raise ValueError("SYNOPTIC_TOKEN not set")
        self.min_interval = min_seconds_between_calls
        self._lock = threading.Lock()
        self._cache: dict[str, dict] = {}
        self._cache_at: Optional[datetime] = None
        self._backoff_until: float = 0.0
        self.last_error: Optional[str] = None

    # ── public API ────────────────────────────────────────────────────

    def get_conditions(self, station_ids: list[str],
                       force: bool = False) -> dict[str, dict]:
        """Current conditions keyed by station id (uppercased).

        Returns the cached payload when it is younger than
        min_interval — so calling this once per game per second still
        produces at most one upstream request per minute.

        Never raises. On failure returns the last good cache (possibly
        empty) and sets .last_error.
        """
        if not station_ids:
            return {}
        with self._lock:
            if not force and self._cache_fresh():
                return dict(self._cache)
            if time.time() < self._backoff_until:
                # In backoff after an upstream failure. Serve stale
                # rather than hammering a service that just told us to
                # slow down.
                return dict(self._cache)
            try:
                self._cache = self._fetch(station_ids)
                self._cache_at = datetime.now(timezone.utc)
                self.last_error = None
                self._backoff_until = 0.0
            except Exception as e:
                self.last_error = f"{type(e).__name__}: {e}"
                # Exponential-ish backoff with jitter, capped at 10 min.
                prev = max(self._backoff_until - time.time(), 0)
                delay = min(max(prev * 2, 30), 600) + random.uniform(0, 5)
                self._backoff_until = time.time() + delay
                print(f"[synoptic] fetch failed ({self.last_error}); "
                      f"backing off {delay:.0f}s, serving "
                      f"{len(self._cache)} cached station(s)", flush=True)
        return dict(self._cache)

    def status(self) -> dict:
        """Health block — surface this in Live's own API/admin."""
        age = None
        if self._cache_at:
            age = (datetime.now(timezone.utc) - self._cache_at).total_seconds() / 60.0
        return {
            "stations_cached": len(self._cache),
            "cache_age_min": round(age, 1) if age is not None else None,
            "in_backoff": time.time() < self._backoff_until,
            "backoff_remaining_sec": max(int(self._backoff_until - time.time()), 0),
            "last_error": self.last_error,
        }

    # ── internals ─────────────────────────────────────────────────────

    def _cache_fresh(self) -> bool:
        if not self._cache_at:
            return False
        age = (datetime.now(timezone.utc) - self._cache_at).total_seconds()
        return age < self.min_interval

    def _fetch(self, station_ids: list[str]) -> dict[str, dict]:
        """ONE request for every station. Do not make this per-venue."""
        stids = ",".join(sorted({s.strip().upper() for s in station_ids if s}))
        params = {
            "token": self.token,
            "stid": stids,
            "vars": VARS,
            "within": WITHIN_MINUTES,
            "units": "english,speed|mph",
            "obtimezone": "UTC",
            "output": "json",
        }

        last_exc = None
        for attempt in range(MAX_RETRIES):
            try:
                r = requests.get(LATEST_URL, params=params,
                                 timeout=REQUEST_TIMEOUT_SEC)
                if r.status_code == 429 or r.status_code >= 500:
                    raise RuntimeError(f"HTTP {r.status_code}")
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:                       # noqa: BLE001
                last_exc = e
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep((2 ** attempt) + random.uniform(0, 1))
        else:                                            # pragma: no cover
            raise last_exc                               # type: ignore[misc]

        code = str((data.get("SUMMARY") or {}).get("RESPONSE_CODE", ""))
        if code == "200":
            raise RuntimeError("Synoptic auth failure — check token")
        if code == "2":
            return {}                                    # zero results
        if code != "1":
            raise RuntimeError(
                f"Synoptic {code}: "
                f"{(data.get('SUMMARY') or {}).get('RESPONSE_MESSAGE')}")

        out = {}
        for st in data.get("STATION") or []:
            parsed = _parse_station(st)
            if parsed:
                out[parsed["stid"]] = parsed
        return out


# ── parsing ───────────────────────────────────────────────────────────────

def _obs_value(obs: dict, prefix: str):
    """Pull a value from the OBSERVATIONS block.

    Keys are suffixed per sensor ("air_temp_value_1", "air_temp_value_2"),
    so match on prefix rather than assuming _1 exists — some stations
    number their sensors differently.
    """
    for key, val in (obs or {}).items():
        if key.startswith(prefix) and isinstance(val, dict):
            return val.get("value"), val.get("date_time")
    return None, None


def _parse_station(st: dict) -> Optional[dict]:
    obs = st.get("OBSERVATIONS") or {}
    stid = (st.get("STID") or "").upper()
    if not stid:
        return None

    temp_f, temp_at = _obs_value(obs, "air_temp_value")
    wind_mph, _ = _obs_value(obs, "wind_speed_value")
    gust_mph, _ = _obs_value(obs, "wind_gust_value")
    wind_dir, _ = _obs_value(obs, "wind_direction_value")
    humidity, _ = _obs_value(obs, "relative_humidity_value")
    wx_text, wx_at = _obs_value(obs, "weather_condition_value")
    precip_1h, _ = _obs_value(obs, "precip_accum_one_hour_value")

    observed_at = temp_at or wx_at
    age_min = None
    if observed_at:
        try:
            dt = datetime.fromisoformat(str(observed_at).replace("Z", "+00:00"))
            age_min = round((datetime.now(timezone.utc) - dt).total_seconds() / 60.0, 1)
        except Exception:
            age_min = None

    # Stale observations are actively misleading — a "clear" reading from
    # an hour ago during a downpour reads as current truth. Drop them.
    if age_min is not None and age_min > MAX_OBS_AGE_MIN:
        return None

    text = str(wx_text or "").lower()
    is_precipitating = any(tok in text for tok in _WET_TOKENS)
    # Fall back to accumulation only when present-weather is absent —
    # accumulation lags and can read 0.0 during light rain that just
    # started, so it is the weaker signal.
    if not text and precip_1h is not None:
        try:
            is_precipitating = float(precip_1h) > 0.0
        except (TypeError, ValueError):
            pass

    return {
        "stid": stid,
        "station_name": st.get("NAME"),
        "observed_at_utc": observed_at,
        "obs_age_min": age_min,
        "temp_f": temp_f,
        "wind_mph": wind_mph,
        "gust_mph": gust_mph,
        "wind_dir_deg": wind_dir,
        "humidity_pct": humidity,
        "weather_text": wx_text,
        "precip_accum_1h_in": precip_1h,
        "is_precipitating": is_precipitating,
        # Never let a consumer mistake this for a stadium-sited sensor.
        "source": "synoptic",
        "is_observation": True,
    }


# ── venue resolution ──────────────────────────────────────────────────────

def load_station_map(path: str) -> dict:
    """Load the map produced by tools/build_station_map.py."""
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("venues") or {}


def conditions_for_venue(venue_key: str, station_map: dict,
                         conditions: dict) -> Optional[dict]:
    """Resolve one venue to conditions, walking primary then fallbacks.

    Returns None for domes (no weather indoors) and when every mapped
    station is stale or missing — a caller that gets None should say
    "no current observation", never substitute a forecast silently.
    """
    venue = station_map.get(venue_key)
    if not venue or not venue.get("needs_obs"):
        return None

    candidates = []
    if venue.get("primary"):
        candidates.append(venue["primary"])
    candidates.extend(venue.get("fallbacks") or [])

    for cand in candidates:
        got = conditions.get((cand.get("stid") or "").upper())
        if got:
            return {**got,
                    "venue": venue.get("name"),
                    "station_distance_mi": cand.get("distance_mi"),
                    "used_fallback": cand is not candidates[0]}
    return None


def all_station_ids(station_map: dict) -> list[str]:
    """Every station id to request — primaries AND fallbacks, deduped.

    Fallbacks cost nothing extra: they ride along in the same single
    batched request, so failover is instant rather than requiring a
    second round trip when a primary goes quiet.
    """
    ids = set()
    for v in station_map.values():
        if not v.get("needs_obs"):
            continue
        if v.get("primary"):
            ids.add((v["primary"].get("stid") or "").upper())
        for fb in v.get("fallbacks") or []:
            ids.add((fb.get("stid") or "").upper())
    return sorted(i for i in ids if i)


if __name__ == "__main__":
    import sys
    map_path = sys.argv[1] if len(sys.argv) > 1 else "data/venue_station_map.json"
    smap = load_station_map(map_path)
    stids = all_station_ids(smap)
    print(f"{len(smap)} venues -> {len(stids)} unique stations "
          f"-> 1 API request per poll")
    client = SynopticLiveClient()
    conds = client.get_conditions(stids)
    print(f"got {len(conds)} station observations; status={client.status()}")
    for key in list(smap)[:5]:
        print(" ", key, "->", conditions_for_venue(key, smap, conds))
