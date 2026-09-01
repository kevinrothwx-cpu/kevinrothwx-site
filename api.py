"""api — MSW forecast JSON API v1 for OVERcast integration.

Contract: docs/FORECAST_API_CONTRACT_v1.md — read that first. This module
implements the endpoints defined there.

Design:
    - Read-only. Never mutates cache or writes anything.
    - Serializes the existing slate cache (nfl/cfb) into the contract shape.
    - Auth via X-API-Key header (keys from MSW_API_KEYS env var).
    - Rate limit: 60 req/min per key, in-memory per-worker.
    - ETag / 304 support for cheap consumer polling.
    - Meta block includes built_at_utc + next_refresh_at_utc so consumers
      can time their next poll to right after MSW's next warmer cycle.

Endpoints:
    GET /api/v1/nfl/slate
    GET /api/v1/nfl/game/<event_id>
    GET /api/v1/cfb/slate
    GET /api/v1/cfb/game/<event_id>
    GET /api/v1/health          — liveness check (no auth required)
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional

from flask import Blueprint, jsonify, request, Response


# ── Blueprint ─────────────────────────────────────────────────────────────

api_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


# ── Auth ──────────────────────────────────────────────────────────────────
#
# Keys are loaded from env var MSW_API_KEYS at startup. Format:
#   MSW_API_KEYS=overcast:sha256hexstring,other:sha256hexstring
# The name prefix is optional and used only for logging; keys can also
# be bare secrets separated by commas.
#
# We hash-compare so a leaked env dump doesn't immediately reveal the raw
# secret. Consumers send the raw secret in the X-API-Key header.

def _load_api_keys() -> dict[str, str]:
    """Return {sha256(key): name} for every configured key."""
    raw = os.environ.get("MSW_API_KEYS", "").strip()
    if not raw:
        return {}
    out: dict[str, str] = {}
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            name, secret = token.split(":", 1)
        else:
            name, secret = "unnamed", token
        digest = hashlib.sha256(secret.strip().encode("utf-8")).hexdigest()
        out[digest] = name.strip()
    return out


_API_KEYS = _load_api_keys()


def _authorized_name(header_value: Optional[str]) -> Optional[str]:
    """Return the consumer name if the header value matches a configured
    key, or None."""
    if not header_value:
        return None
    digest = hashlib.sha256(header_value.strip().encode("utf-8")).hexdigest()
    return _API_KEYS.get(digest)


def require_api_key(fn):
    """Decorator that rejects requests without a valid X-API-Key header."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Empty key config = API disabled entirely (safer default than open).
        if not _API_KEYS:
            return jsonify({
                "error": "api_disabled",
                "message": "API is not configured on this deployment. "
                           "Set MSW_API_KEYS env var to enable.",
            }), 503
        name = _authorized_name(request.headers.get("X-API-Key"))
        if not name:
            return jsonify({
                "error": "unauthorized",
                "message": "Missing or invalid X-API-Key header.",
            }), 401
        # Attach consumer name to the request for downstream use / logging.
        request.consumer_name = name
        return fn(*args, **kwargs)
    return wrapper


# ── Rate limit (per-key, per-minute, in-memory) ───────────────────────────

_rate_lock = threading.Lock()
_rate_windows: dict[str, dict] = {}  # consumer_name → {"count": int, "window_start": float}
RATE_LIMIT_PER_MIN = 60


def rate_limited(fn):
    """Decorator applying the 60/min limit per consumer key."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        consumer = getattr(request, "consumer_name", None) or "anonymous"
        now = time.time()
        window = 60.0
        with _rate_lock:
            entry = _rate_windows.get(consumer)
            if entry is None or now - entry["window_start"] >= window:
                _rate_windows[consumer] = {"count": 1, "window_start": now}
                remaining = RATE_LIMIT_PER_MIN - 1
            elif entry["count"] >= RATE_LIMIT_PER_MIN:
                retry_after = int(window - (now - entry["window_start"])) + 1
                resp = jsonify({
                    "error": "rate_limited",
                    "message": f"Max {RATE_LIMIT_PER_MIN} requests per minute per API key.",
                    "retry_after_seconds": retry_after,
                })
                resp.status_code = 429
                resp.headers["Retry-After"] = str(retry_after)
                return resp
            else:
                entry["count"] += 1
                remaining = RATE_LIMIT_PER_MIN - entry["count"]
        response = fn(*args, **kwargs)
        # Attach rate-limit headers so consumers can throttle themselves.
        if isinstance(response, tuple):
            body, status = response[0], response[1]
            if hasattr(body, "headers"):
                body.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_PER_MIN)
                body.headers["X-RateLimit-Remaining"] = str(remaining)
            return response
        if hasattr(response, "headers"):
            response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_PER_MIN)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
    return wrapper


# ── ETag / 304 helper ─────────────────────────────────────────────────────

def compute_etag(payload_dict: dict) -> str:
    """SHA-256 of the canonical JSON of payload minus meta.etag (would be
    circular). Prefixed with 'sha256:' per contract."""
    scrub = dict(payload_dict)
    if isinstance(scrub.get("meta"), dict):
        m = dict(scrub["meta"])
        m.pop("etag", None)
        scrub["meta"] = m
    canonical = json.dumps(scrub, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def json_response_with_etag(payload_dict: dict) -> Response:
    """Emit JSON with computed ETag; return 304 if If-None-Match matches."""
    etag = compute_etag(payload_dict)
    if isinstance(payload_dict.get("meta"), dict):
        payload_dict["meta"]["etag"] = etag
    inm = request.headers.get("If-None-Match")
    if inm and inm.strip() == etag:
        resp = Response(status=304)
        resp.headers["ETag"] = etag
        return resp
    resp = jsonify(payload_dict)
    resp.headers["ETag"] = etag
    resp.headers["Cache-Control"] = "no-cache, must-revalidate"
    return resp


# ── precip_type derivation (contract v1 rule) ─────────────────────────────

def precip_type_from(short_forecast: Optional[str],
                     temp_f: Optional[float],
                     precip_pct: Optional[float]) -> str:
    """Derive contract precip_type enum from NWS short_forecast + temp.

    Rules (contract v1):
        precip_pct < 10 → "none"
        freezing/sleet keywords → "freezing"
        rain AND snow keywords, or "wintry mix" / "rain/snow" → "mix"
        snow keywords only → "snow"
        rain/shower/drizzle/thunderstorm keywords only → "rain"
        Vague text + elevated precip_pct → temperature fallback:
            ≤ 28°F → snow, 28-33°F → mix, else rain.
    """
    if precip_pct is None or precip_pct < 10:
        return "none"
    text = (short_forecast or "").lower()

    # Freezing / sleet first — some strings ("freezing rain") contain "rain"
    if any(kw in text for kw in ("freezing", "sleet", "ice pellets")):
        return "freezing"

    has_rain = any(kw in text for kw in ("rain", "shower", "drizzle", "thunderstorm", "t-storm"))
    has_snow = any(kw in text for kw in ("snow", "flurries", "blizzard"))

    if "wintry mix" in text or "rain/snow" in text or "rain and snow" in text:
        return "mix"
    if has_rain and has_snow:
        return "mix"
    if has_snow:
        return "snow"
    if has_rain:
        return "rain"

    # Vague text — use temperature as tiebreaker
    if temp_f is not None:
        if temp_f <= 28:
            return "snow"
        if temp_f <= 33:
            return "mix"
        return "rain"

    return "none"


# ── Serializers (translate internal dicts to contract shape) ──────────────

def _iso_utc(dt) -> Optional[str]:
    """Serialize a datetime to ISO 8601 UTC with Z suffix. Returns None on
    None/invalid input."""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt  # already serialized
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _round_int(x) -> Optional[int]:
    """Contract: MSW rounds to integer at API boundary."""
    if x is None:
        return None
    try:
        return int(round(float(x)))
    except (TypeError, ValueError):
        return None


def serialize_forecast(period: Optional[dict], is_kickoff_hour: bool = False) -> Optional[dict]:
    """Translate one internal forecast/hourly dict into a contract Forecast.
    Returns None when input is None."""
    if period is None:
        return None
    temp_f = _round_int(period.get("temp"))
    precip_pct = _round_int(period.get("precip_pct"))
    short_forecast = period.get("short_forecast")
    return {
        "start_time_utc": _iso_utc(
            period.get("hour_local_dt")  # some builders use this
            or period.get("start_time")
        ),
        "temp_f": temp_f,
        "feels_like_f": _round_int(period.get("feels_like")),
        "wind_speed_mph": _round_int(period.get("wind_speed")),
        "wind_deg": _round_int(period.get("wind_deg")),
        "gust_mph": _round_int(period.get("gust") or period.get("gust_mph")),
        "precip_pct": precip_pct if precip_pct is not None else 0,
        "precip_type": precip_type_from(short_forecast, temp_f, precip_pct),
        "short_forecast": short_forecast,
        "humidity_pct": _round_int(period.get("humidity")),
        "dew_point_f": _round_int(period.get("dew_point") or period.get("dew")),
        "is_kickoff_hour": bool(is_kickoff_hour or period.get("is_game_hour")),
    }


def serialize_team(team: dict) -> dict:
    return {
        "team_id": team.get("team_id"),
        "name": team.get("name"),
        "short": team.get("short"),
        "abbrev": team.get("abbrev"),
        "conf": team.get("conf"),
        "logo_url": team.get("logo_url") or "",
    }


def serialize_venue(venue: dict) -> dict:
    """Translate internal stadium dict to contract Venue. NFL uses roof_type
    + timezone + cap; CFB uses roof + tz + cap; MLS uses stadium.roof_type."""
    if not venue:
        return {}
    roof = venue.get("roof_type") or venue.get("roof") or "open"
    tz = venue.get("timezone") or venue.get("tz")
    cap = venue.get("capacity") or venue.get("cap")
    return {
        "name": venue.get("name"),
        "city": venue.get("city"),
        "lat": venue.get("lat"),
        "lon": venue.get("lon"),
        "timezone": tz,
        "roof_type": roof,
        "capacity": cap,
        "nws_unsupported": bool(venue.get("nws_unsupported", False)),
        "country": venue.get("country") or "US",
        # Compass bearing the field runs, endzone to endzone. 0 = N/S,
        # 90 = E/W. Either endzone is valid, so 0 and 180 describe the same
        # field. Combine with wind_direction_degrees for a field-relative
        # wind: (wind_to - field_bearing + 90) % 360.
        #
        # null means UNKNOWN, not "no wind" — do not treat it as 0. All 134
        # CFB home venues are covered (3 fixed domes are null because indoor
        # wind is meaningless), but 13 neutral-site venues are genuinely
        # unmeasured. Check roof_type to tell the two cases apart.
        "field_bearing_degrees": venue.get("field_bearing_degrees"),
    }


def serialize_odds(odds: Optional[dict]) -> Optional[dict]:
    """Translate the internal odds dict to the contract Odds block.

    None when no book posted a total for this game — normal, not an error.
    Check meta.odds.error to distinguish "unpriced" from "pipeline down".

    `frozen` marks the kickoff snapshot: once a game starts, The Odds API
    serves LIVE in-game totals, which are stale garbage between our 25-min
    polls. We freeze the last pre-kickoff total and serve that instead, so
    `current` stays a genuine closing line rather than drifting mid-game.
    """
    if not odds:
        return None
    return {
        "total_current": odds.get("current"),
        "total_opening": odds.get("opening"),
        "delta": odds.get("delta"),
        "book": odds.get("book_display"),
        "book_key": odds.get("book_key") or None,
        "frozen": bool(odds.get("frozen")),
    }


def serialize_writeup(writeup: Optional[dict]) -> Optional[dict]:
    if not writeup:
        return None
    return {
        "text": writeup.get("text"),
        "color": writeup.get("color"),
        "updated_at_utc": _iso_utc(writeup.get("updated_at_utc")),
    }


def serialize_game(game: dict, sport: str, frozen_lookup=None) -> dict:
    """Translate an internal game dict to a contract Game.

    Args:
        game: internal slate dict from nfl/cfb slate builder
        sport: "nfl" | "cfb"
        frozen_lookup: optional callable(event_id) → freeze dict, so we can
                       populate frozen_at_utc. Pass nfl.forecast_freeze.get
                       or cfb.forecast_freeze.get.
    """
    event_id = str(game.get("event_id") or game.get("id") or "")
    forecast = game.get("forecast")
    hourly = game.get("hourly") or []
    hrrr_hourly = game.get("hrrr_hourly") or []

    # Kickoff snapshot serialization
    forecast_at_kickoff = serialize_forecast(forecast, is_kickoff_hour=True)

    # Frozen_at lookup
    is_frozen = bool(game.get("is_frozen"))
    frozen_at_utc = None
    if is_frozen and frozen_lookup and event_id:
        try:
            f = frozen_lookup(event_id)
            if f:
                frozen_at_utc = _iso_utc(f.get("frozen_at_utc"))
        except Exception:
            pass

    return {
        "event_id": event_id,
        "sport": sport,
        "season_type": game.get("season_type"),
        "season_type_label": game.get("season_type_label"),
        "week": game.get("week"),
        "home": serialize_team(game.get("home") or {}),
        "away": serialize_team(game.get("away") or {}),
        "venue": serialize_venue(game.get("venue") or {}),
        "kickoff_utc": _iso_utc(game.get("kickoff_utc")),
        "kickoff_local_str": game.get("kickoff_eastern_str") or game.get("kickoff_local_str"),
        "status": game.get("status"),
        "slug": game.get("slug"),
        "forecast_at_kickoff": forecast_at_kickoff,
        "hourly": [serialize_forecast(p) for p in hourly],
        "hrrr_hourly": [serialize_forecast(p) for p in hrrr_hourly],
        "weather_source": game.get("weather_source"),
        "weather_error": game.get("weather_error"),
        "is_frozen": is_frozen,
        "frozen_at_utc": frozen_at_utc,
        "writeup": serialize_writeup(game.get("writeup")),
        "odds": serialize_odds(game.get("odds")),
    }


def build_odds_meta(sport: str) -> dict:
    """Odds pipeline health for one sport.

    Lets a consumer tell "no book posted this game" (game.odds is null but
    ok=true) from "our odds fetch is failing" (ok=false + error), which is
    the only case where falling back to their own odds source is correct.

    ok=null means this process has not attempted a fetch yet — a freshly
    booted instance serving a warm-boot slate. Treat as unknown, not down.

    NFL caveat: an empty upstream payload reports ok=true, game_count=0.
    The schedule fetch it shares swallows its own errors, so a real outage
    is indistinguishable from the legitimately empty offseason. Sustained
    game_count=0 during the season is the signal worth alerting on.
    """
    try:
        if sport == "nfl":
            from nfl.odds import get_last_odds_status
        else:
            from cfb.odds import get_last_odds_status
        st = get_last_odds_status()
    except Exception:
        return {"ok": None, "error": None,
                "updated_utc": None, "game_count": 0}
    return {
        "ok": st.get("ok"),
        "error": st.get("error"),
        "updated_utc": _iso_utc(st.get("fetched_utc")),
        "game_count": st.get("game_count") or 0,
    }


def build_meta(built_at_utc, refresh_seconds: int = 25 * 60,
               sport: Optional[str] = None) -> dict:
    """Assemble the Meta block. etag added by json_response_with_etag."""
    built = built_at_utc if isinstance(built_at_utc, datetime) else None
    if built and built.tzinfo is None:
        built = built.replace(tzinfo=timezone.utc)
    next_refresh = (built + timedelta(seconds=refresh_seconds)) if built else None
    meta = {
        "built_at_utc": _iso_utc(built),
        "next_refresh_at_utc": _iso_utc(next_refresh),
        "etag": None,  # filled by json_response_with_etag
        "api_version": "v1",
    }
    if sport:
        meta["odds"] = build_odds_meta(sport)
    return meta


# ── Endpoints ─────────────────────────────────────────────────────────────

@api_bp.route("/health", methods=["GET"])
def health():
    """Liveness check — no auth. Returns 200 and a simple ok payload."""
    return jsonify({
        "status": "ok",
        "api_version": "v1",
        "server_time_utc": _iso_utc(datetime.now(timezone.utc)),
        "auth_configured": bool(_API_KEYS),
    })


@api_bp.route("/nfl/slate", methods=["GET"])
@require_api_key
@rate_limited
def nfl_slate():
    from nfl.cache import get_nfl_slate
    from nfl import forecast_freeze as nfl_freeze
    games, meta = get_nfl_slate()
    built_at = (meta or {}).get("built_at_utc")
    payload = {
        "games": [serialize_game(g, "nfl", nfl_freeze.get) for g in (games or [])],
        "meta": build_meta(built_at, sport="nfl"),
    }
    return json_response_with_etag(payload)


@api_bp.route("/nfl/game/<event_id>", methods=["GET"])
@require_api_key
@rate_limited
def nfl_game(event_id):
    from nfl.cache import get_nfl_slate
    from nfl import forecast_freeze as nfl_freeze
    games, meta = get_nfl_slate()
    match = next((g for g in (games or []) if str(g.get("event_id") or g.get("id")) == str(event_id)), None)
    if not match:
        return jsonify({
            "error": "not_found",
            "message": f"NFL event_id {event_id} not on current slate.",
        }), 404
    payload = {
        "game": serialize_game(match, "nfl", nfl_freeze.get),
        "meta": build_meta((meta or {}).get("built_at_utc"), sport="nfl"),
    }
    return json_response_with_etag(payload)


@api_bp.route("/cfb/slate", methods=["GET"])
@require_api_key
@rate_limited
def cfb_slate():
    from cfb.cache import get_cfb_slate
    from cfb import forecast_freeze as cfb_freeze
    games, meta = get_cfb_slate()
    built_at = (meta or {}).get("built_at_utc")
    payload = {
        "games": [serialize_game(g, "cfb", cfb_freeze.get) for g in (games or [])],
        "meta": build_meta(built_at, sport="cfb"),
    }
    return json_response_with_etag(payload)


@api_bp.route("/cfb/game/<event_id>", methods=["GET"])
@require_api_key
@rate_limited
def cfb_game(event_id):
    from cfb.cache import get_cfb_slate
    from cfb import forecast_freeze as cfb_freeze
    games, meta = get_cfb_slate()
    match = next((g for g in (games or []) if str(g.get("event_id") or g.get("id")) == str(event_id)), None)
    if not match:
        return jsonify({
            "error": "not_found",
            "message": f"CFB event_id {event_id} not on current slate.",
        }), 404
    payload = {
        "game": serialize_game(match, "cfb", cfb_freeze.get),
        "meta": build_meta((meta or {}).get("built_at_utc"), sport="cfb"),
    }
    return json_response_with_etag(payload)


def register(app):
    """Register the API blueprint on a Flask app instance."""
    app.register_blueprint(api_bp)


# EOF-CANARY 2026-07-04-api-v1-build
