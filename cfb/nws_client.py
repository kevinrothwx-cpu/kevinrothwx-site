"""CFB-specific NWS client wrapper.

Why this exists separately from mlb/nws.py:

  1. Distinct User-Agent so NWS server logs can differentiate CFB traffic
     from MLB / OVERcast traffic on the same outbound IP. If NWS throttles,
     we can tell which sport caused it.

  2. Sequential pacing with a per-call delay. The MLB module fires venue
     fetches as-fast-as-possible inside its warmer. On a CFB Saturday with
     ~70 unique stadiums that pattern would burst at >10 req/sec briefly
     even if average is low — and bursts are what trigger rate limits.

  3. Circuit breaker. If NWS returns enough 429s in a short window, we
     STOP calling NWS for CFB for a cooldown period. The caller falls back
     to WeatherAPI. This protects OVERcast (which shares our outbound IP)
     from compounding the throttle problem.

  4. Permanent in-memory gridpoint cache. FBS stadium coordinates never
     change, so resolving each (lat,lon) → /points/.../forecast URL once
     per process lifetime saves half our NWS API calls.

Health reporting:
    Every call records its outcome to nws_health (rolling counter + alert),
    so the admin dashboard reflects what CFB is actually seeing.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import requests

from nws_health import record as nws_record
from mlb.nws import extract_forecast  # reuse the period normalizer

log = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────────

# Distinct UA: NWS staff see "kevinrothwx-site/1.0 ncaaf" in their logs
# and can correlate any throttle event to this sport specifically.
NWS_USER_AGENT = "kevinrothwx-site/1.0 ncaaf (kevinrothwx@gmail.com)"

NWS_HEADERS = {
    "User-Agent": NWS_USER_AGENT,
    "Accept":     "application/geo+json",
}

NWS_POINTS_URL = "https://api.weather.gov/points/{lat},{lon}"

# Pacing — sleep between consecutive NWS calls. 200ms = max 5 req/sec
# which is the published NWS recommendation. Keeps bursts from compounding
# with OVERcast traffic.
INTER_CALL_DELAY_SEC = 0.20

# Per-call request timeout
REQUEST_TIMEOUT_SEC = 15

# Circuit breaker — once tripped, NWS calls are short-circuited
# (return None immediately so caller falls back to WeatherAPI) for this long.
CIRCUIT_OPEN_SEC = 10 * 60  # 10 min cooldown after we get rate-limited


# ── State ─────────────────────────────────────────────────────────────────

# Permanent per-venue gridpoint URL cache: (lat_4dp, lon_4dp) → hourly_url
_gridpoint_cache: dict[tuple[float, float], str] = {}
_gridpoint_lock = threading.Lock()

# Last NWS call timestamp (for pacing). Module-level so pacing is global
# across the whole CFB warmer regardless of which function is called.
_last_call_at = 0.0
_pacing_lock = threading.Lock()

# Circuit breaker state. _circuit_open_until is the epoch at which we'll
# allow NWS calls again. 0 means circuit is closed (normal operation).
_circuit_open_until = 0.0
_circuit_lock = threading.Lock()


# ── Public API ────────────────────────────────────────────────────────────

def fetch_cfb_hourly(lat: float, lon: float) -> Optional[list[dict]]:
    """Fetch normalized hourly NWS forecast for a CFB venue.

    Returns:
        list of period dicts on success (same shape as mlb.nws.extract_forecast)
        None on any failure — caller should fall back to WeatherAPI.

    Behavior:
        - If circuit breaker is open, returns None immediately (no request)
        - Otherwise paces calls with INTER_CALL_DELAY_SEC global throttle
        - Reports every outcome to nws_health for the rolling counter
        - On 429 (rate limit), trips the circuit breaker
    """
    if _circuit_is_open():
        log.debug(f"[cfb.nws] circuit open, skipping {lat},{lon}")
        return None

    try:
        hourly_url = _get_or_resolve_gridpoint(lat, lon)
        if not hourly_url:
            return None
        return _fetch_hourly(hourly_url)
    except Exception as e:
        log.warning(f"[cfb.nws] unexpected error for {lat},{lon}: {e}")
        nws_record("other_error", f"cfb {lat},{lon}", msg=str(e))
        return None


def circuit_status() -> dict:
    """Return current circuit-breaker state for the admin dashboard."""
    now = time.time()
    with _circuit_lock:
        opened_until = _circuit_open_until
    if opened_until <= now:
        return {"open": False, "seconds_until_reset": 0}
    return {"open": True, "seconds_until_reset": int(opened_until - now)}


def gridpoint_cache_size() -> int:
    """Number of permanently-cached venue gridpoint resolutions."""
    return len(_gridpoint_cache)


# ── Internals ─────────────────────────────────────────────────────────────

def _circuit_is_open() -> bool:
    with _circuit_lock:
        return time.time() < _circuit_open_until


def _trip_circuit() -> None:
    global _circuit_open_until
    with _circuit_lock:
        _circuit_open_until = time.time() + CIRCUIT_OPEN_SEC
    log.warning(
        f"[cfb.nws] circuit breaker tripped — skipping NWS for "
        f"{CIRCUIT_OPEN_SEC // 60} min, falling back to WeatherAPI"
    )


def _pace() -> None:
    """Sleep just long enough that consecutive NWS calls are spaced by
    INTER_CALL_DELAY_SEC. Pacing is global across the CFB module."""
    global _last_call_at
    with _pacing_lock:
        now = time.time()
        gap = now - _last_call_at
        if gap < INTER_CALL_DELAY_SEC:
            time.sleep(INTER_CALL_DELAY_SEC - gap)
        _last_call_at = time.time()


def _get_or_resolve_gridpoint(lat: float, lon: float) -> Optional[str]:
    """Resolve (lat,lon) → forecastHourly URL via /points endpoint.

    Cached forever — FBS stadium coordinates never change, so each venue
    only ever hits /points once per process lifetime.
    """
    key = (round(lat, 4), round(lon, 4))
    with _gridpoint_lock:
        cached = _gridpoint_cache.get(key)
    if cached:
        return cached

    _pace()
    url = NWS_POINTS_URL.format(lat=f"{lat:.4f}", lon=f"{lon:.4f}")
    try:
        resp = requests.get(url, headers=NWS_HEADERS, timeout=REQUEST_TIMEOUT_SEC)
    except requests.Timeout:
        nws_record("timeout", url)
        return None
    except Exception as e:
        nws_record("other_error", url, msg=str(e))
        return None

    if resp.status_code == 429:
        nws_record("rate_limit", url, code=429)
        _trip_circuit()
        return None
    if resp.status_code >= 500:
        nws_record("server_error", url, code=resp.status_code)
        return None
    if resp.status_code != 200:
        nws_record("other_error", url, code=resp.status_code)
        return None

    nws_record("ok", url)
    try:
        hourly_url = resp.json()["properties"]["forecastHourly"]
    except (KeyError, ValueError) as e:
        nws_record("other_error", url, msg=f"bad json: {e}")
        return None

    with _gridpoint_lock:
        _gridpoint_cache[key] = hourly_url
    return hourly_url


def _fetch_hourly(hourly_url: str) -> Optional[list[dict]]:
    """Fetch the hourly forecast and normalize via extract_forecast."""
    _pace()
    try:
        resp = requests.get(hourly_url, headers=NWS_HEADERS, timeout=REQUEST_TIMEOUT_SEC)
    except requests.Timeout:
        nws_record("timeout", hourly_url)
        return None
    except Exception as e:
        nws_record("other_error", hourly_url, msg=str(e))
        return None

    if resp.status_code == 429:
        nws_record("rate_limit", hourly_url, code=429)
        _trip_circuit()
        return None
    if resp.status_code >= 500:
        nws_record("server_error", hourly_url, code=resp.status_code)
        return None
    if resp.status_code != 200:
        nws_record("other_error", hourly_url, code=resp.status_code)
        return None

    nws_record("ok", hourly_url)
    try:
        raw = resp.json()["properties"]["periods"]
    except (KeyError, ValueError) as e:
        nws_record("other_error", hourly_url, msg=f"bad json: {e}")
        return None

    periods = [extract_forecast(p) for p in raw]
    return periods or None
