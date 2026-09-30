"""partner_api — weather-only JSON feed for outside partners (2026-09-30).

First consumer: Establish The Run's weekly "The Rundown" table.
Partner-facing doc: docs/PARTNER_API_v1.md (safe to send to partners).

WHY A SEPARATE MODULE (not a flag on api.py):
    api.py is the OVERcast contract. It carries odds (from our paid Odds API
    plan, which we must not pass on), Kevin's write-ups, and freeze internals.
    Partners get none of that. Keeping this in its own blueprint, with its
    own URLs and its own keys, means:
      - OVERcast's /api/v1 code path is untouched by anything here.
      - A partner key cannot open /api/v1 (different env var), and an
        OVERcast key cannot open these endpoints.
      - The partner shape can stay small and stable while v1 evolves.

WHAT IT DOES NOT DO:
    - Never builds a slate. Reads the warm cache with allow_build=False, so
      partner traffic can never trigger NWS / HRRR / Odds API calls or a
      slow rebuild inside a request. The warmers and page views keep the
      cache fresh exactly as before.
    - Never writes anything.
    - No odds, no write-ups, no HRRR, no field bearings (NFL bearings are
      not audited yet), no internal error strings.

DATA LICENSING:
    NWS forecasts are public domain. Forecasts from WeatherAPI.com
    (international venues, and US games where NWS failed and we fell back)
    are included because INCLUDE_NON_NWS_FORECASTS is True (Kevin's call,
    2026-09-30). Set it False to withhold them; those games then come
    through as forecast_status "unavailable". WeatherAPI periods carry no
    gust, so gust_mph is null for those games.

KEYS:
    Env var MSW_PARTNER_KEYS, same format as MSW_API_KEYS:
        MSW_PARTNER_KEYS=etr:<long random secret>,other:<secret>
    Partner sends the secret in the X-API-Key header. No keys configured =
    endpoints return 503 (nothing exposed). Remove a key to revoke it.
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from datetime import datetime
from functools import wraps
from typing import Optional

from flask import Blueprint, g, jsonify, request

from api import (
    _iso_utc,
    _round_int,
    build_meta,
    json_response_with_etag,
    precip_type_from,
)


partner_bp = Blueprint("partner_api_v1", __name__, url_prefix="/api/partner/v1")

API_VERSION = "partner-v1"
RATE_LIMIT_PER_MIN = 30
INCLUDE_NON_NWS_FORECASTS = True   # Kevin, 2026-09-30: include international games

ATTRIBUTION_URLS = {
    "nfl": "https://mysportsweather.com/nfl",
    "cfb": "https://mysportsweather.com/ncaaf",
}
ATTRIBUTION_TEXT = "Weather by MySportsWeather.com"


# ── Auth ──────────────────────────────────────────────────────────────────

def _load_partner_keys() -> dict[str, str]:
    """Return {sha256(secret): partner_name} from MSW_PARTNER_KEYS."""
    raw = os.environ.get("MSW_PARTNER_KEYS", "").strip()
    out: dict[str, str] = {}
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        name, secret = token.split(":", 1) if ":" in token else ("partner", token)
        secret = secret.strip()
        if not secret:
            continue
        out[hashlib.sha256(secret.encode("utf-8")).hexdigest()] = name.strip() or "partner"
    return out


_PARTNER_KEYS = _load_partner_keys()


def _require_partner_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _PARTNER_KEYS:
            return jsonify({"error": "api_disabled",
                            "message": "Partner API is not enabled."}), 503
        supplied = (request.headers.get("X-API-Key") or "").strip()
        name = _PARTNER_KEYS.get(
            hashlib.sha256(supplied.encode("utf-8")).hexdigest()) if supplied else None
        if not name:
            return jsonify({"error": "unauthorized",
                            "message": "Missing or invalid X-API-Key header."}), 401
        g.partner_name = name
        return fn(*args, **kwargs)
    return wrapper


# ── Rate limit (per partner, per minute, in-memory) ───────────────────────

_rate_lock = threading.Lock()
_rate_windows: dict[str, dict] = {}


def _rate_limited(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        name = getattr(g, "partner_name", None) or "unknown"
        now = time.time()
        with _rate_lock:
            w = _rate_windows.get(name)
            if w is None or now - w["start"] >= 60.0:
                _rate_windows[name] = {"start": now, "count": 1}
            elif w["count"] >= RATE_LIMIT_PER_MIN:
                retry = int(60.0 - (now - w["start"])) + 1
                resp = jsonify({"error": "rate_limited",
                                "message": f"Max {RATE_LIMIT_PER_MIN} requests per minute.",
                                "retry_after_seconds": retry})
                resp.status_code = 429
                resp.headers["Retry-After"] = str(retry)
                return resp
            else:
                w["count"] += 1
        return fn(*args, **kwargs)
    return wrapper


# ── Serializers ───────────────────────────────────────────────────────────

_COMPASS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")


def _utc_iso(value) -> Optional[str]:
    """Always 'YYYY-MM-DDTHH:MM:SSZ'. api._iso_utc passes strings through
    untouched, and NWS start times are local-offset strings
    ('...T13:00:00-04:00'), so parse those and convert."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return _iso_utc(value) if isinstance(value, datetime) else None


def _compass(deg) -> Optional[str]:
    """16-point compass text for a direction in degrees. None when unknown
    (calm hours with no resolvable direction come through as None)."""
    d = _round_int(deg)
    if d is None:
        return None
    return _COMPASS[int(((d % 360) + 11.25) // 22.5) % 16]


def _forecast(period: dict, kickoff: bool = False) -> dict:
    """One hour of weather. For the kickoff snapshot, precip_pct is the
    kickoff-hour chance; the whole-game max is reported separately."""
    temp_f = _round_int(period.get("temp"))
    if kickoff and period.get("precip_pct_kickoff") is not None:
        precip = _round_int(period.get("precip_pct_kickoff"))
    else:
        precip = _round_int(period.get("precip_pct"))
    conditions = period.get("short_forecast")
    return {
        "time_utc": _utc_iso(period.get("start_time")),
        "temp_f": temp_f,
        "wind_mph": _round_int(period.get("wind_speed")),
        "wind_dir": _compass(period.get("wind_deg")),
        "wind_deg": _round_int(period.get("wind_deg")),
        "gust_mph": _round_int(period.get("gust")),
        "precip_pct": precip if precip is not None else 0,
        "precip_type": precip_type_from(conditions, temp_f, precip),
        "conditions": conditions,
    }


def _team(t: dict) -> dict:
    t = t or {}
    return {"name": t.get("name"), "abbrev": t.get("abbrev") or t.get("short")}


def _source_allowed(source: str) -> bool:
    s = (source or "").lower()
    if s.startswith("nws"):
        return True
    return INCLUDE_NON_NWS_FORECASTS and s.startswith("weatherapi")


def _game(game: dict, sport: str) -> dict:
    venue = game.get("venue") or {}
    roof = (venue.get("roof_type") or venue.get("roof") or "open").lower()
    forecast = game.get("forecast")

    kickoff_fc = None
    hourly_out: list[dict] = []
    game_max = None
    if roof == "fixed_dome":
        status = "indoor"
    elif not forecast or not _source_allowed(game.get("weather_source")):
        status = "unavailable"
    else:
        status = "ok"
        kickoff_fc = _forecast(forecast, kickoff=True)
        for p in game.get("hourly") or []:
            row = _forecast(p)
            row["in_game"] = bool(p.get("is_game_hour"))
            hourly_out.append(row)
        in_game = [r["precip_pct"] for r in hourly_out if r["in_game"]]
        if in_game:
            game_max = max(in_game)
        else:
            game_max = _round_int(forecast.get("precip_pct"))

    return {
        "event_id": str(game.get("event_id") or game.get("id") or ""),
        "sport": sport,
        "week": game.get("week"),
        "away": _team(game.get("away")),
        "home": _team(game.get("home")),
        "kickoff_utc": _utc_iso(game.get("kickoff_utc")),
        "venue": {
            "name": venue.get("name"),
            "city": venue.get("city"),
            "country": venue.get("country") or "US",
            "lat": venue.get("lat"),
            "lon": venue.get("lon"),
            "timezone": venue.get("timezone") or venue.get("tz"),
            "roof_type": roof,
        },
        "forecast_status": status,
        "kickoff_forecast": kickoff_fc,
        "game_max_precip_pct": game_max,
        "hourly": hourly_out,
    }


def _slate_payload(games, meta, sport: str) -> dict:
    out_games = []
    for gm in games or []:
        try:
            out_games.append(_game(gm, sport))
        except Exception as e:
            # One malformed game must not take down the whole feed.
            print(f"[partner_api] skipped {sport} game "
                  f"{gm.get('event_id') if isinstance(gm, dict) else '?'}: "
                  f"{type(e).__name__}: {e}", flush=True)
    m = build_meta((meta or {}).get("built_at_utc"))   # no sport → no odds block
    m["api_version"] = API_VERSION
    return {
        "attribution": {
            "text": ATTRIBUTION_TEXT,
            "url": ATTRIBUTION_URLS[sport],
            "required": True,
        },
        "games": out_games,
        "meta": m,
    }


def _respond(payload: dict):
    resp = json_response_with_etag(payload)
    resp.headers["X-Robots-Tag"] = "noindex"
    return resp


# ── Endpoints ─────────────────────────────────────────────────────────────

@partner_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "api_version": API_VERSION,
                    "enabled": bool(_PARTNER_KEYS)})


@partner_bp.route("/nfl/slate", methods=["GET"])
@_require_partner_key
@_rate_limited
def nfl_slate():
    from nfl.cache import get_nfl_slate
    games, meta = get_nfl_slate(allow_build=False)
    return _respond(_slate_payload(games, meta, "nfl"))


@partner_bp.route("/cfb/slate", methods=["GET"])
@_require_partner_key
@_rate_limited
def cfb_slate():
    from cfb.cache import get_cfb_slate
    games, meta = get_cfb_slate(allow_build=False)
    return _respond(_slate_payload(games, meta, "cfb"))


def register(app):
    app.register_blueprint(partner_bp)


# EOF-CANARY 2026-09-30-partner-api
