"""
weather_spotlight — cross-sport homepage highlight of the day's biggest
weather game.

Public API:
    get_current() -> dict | None
        Return the currently-featured game (or None if no game meets the
        threshold). Handles the 6-hour lock, kickoff release, and re-pick.
        Called from the / route on every homepage render — safe to call
        frequently, most calls hit the in-memory lock.

Design (locked with Kevin 2026-08-06):
    - Single game (not top-3)
    - Locked for 6 hours minimum so it doesn't flicker between page loads
    - Continue refreshing the FORECAST on the locked game each request
      (so temp/rain% stay live even though the pick is locked)
    - Release the lock when the featured game's kickoff arrives, then
      re-pick from remaining upcoming games
    - Hide entirely if no game scores above threshold — no weak picks
    - Disk-backed persistence via persistence module (survives deploys)

Scoring (starts simple, can refine):
    Wind speed:
        15-20 mph → 10 pts
        21-30 mph → 25 pts
        31+ mph   → 45 pts
        Gusts +5 more if gust >= wind + 8
    Precip probability:
        60-79% → 20 pts
        80+%   → 40 pts
    Temperature extremes:
        95-99°F  → 15 pts
        100+°F   → 30 pts
        <=32°F   → 20 pts
        <=20°F   → 40 pts
    Storm risk (short_forecast contains "thunder" / "storm"):
        +15 pts

    THRESHOLD_SCORE = 25 — below this, we hide the strip.
    Weak weather day is better than featuring a mild game.

Sports covered in v1:
    MLB (in-season workhorse). Other sport adapters plug in via
    SPORT_ADAPTERS; add them by writing a function that returns a list
    of Candidate dicts.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from persistence import load_json, save_json, parse_dt


_DISK_FILE = "weather_spotlight_lock.json"
_LOCK_HOURS = 6
_THRESHOLD_SCORE = 25

EASTERN_TZ = ZoneInfo("America/New_York")


# Per-sport lookahead window (in days, inclusive of today) — how far ahead
# each sport is allowed to feature a game. Kevin's rule (2026-08-06):
#   MLB plays daily → today only (never feature tomorrow's game while today
#      still has games happening — confusing)
#   CFB / NFL games are weekly events → 4 days ahead is fine (Tuesday can
#      preview a Saturday game since that's the marquee)
#   Weekly sports (PGA / NASCAR / MLS on Wed-Sat cadence) → 2 days, tighter
#      than football but wider than daily. Tunable per sport.
SPORT_LOOKAHEAD_DAYS = {
    "mlb":    0,   # today only
    "cfb":    4,   # up to 4 days ahead (Tue → Sat)
    "nfl":    4,   # up to 4 days ahead
    "mls":    2,   # small window
    "pga":    2,
    "nascar": 2,
}


def _date_strs_for_sport(sport_key: str) -> list[str]:
    """Return today + lookahead date strings (YYYY-MM-DD) allowed for a
    given sport's Spotlight candidacy."""
    days_ahead = SPORT_LOOKAHEAD_DAYS.get(sport_key, 0)
    base = datetime.now(EASTERN_TZ)
    return [(base + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(days_ahead + 1)]

# Persisted lock: {"selection_key": str, "locked_until_utc": datetime, "game": dict}
_lock_state: dict = {}
_state_lock = threading.Lock()


def _load_from_disk() -> None:
    """Load persisted lock state on module import."""
    raw = load_json(_DISK_FILE, default={})
    if not isinstance(raw, dict):
        return
    if "locked_until_utc" in raw and isinstance(raw["locked_until_utc"], str):
        raw["locked_until_utc"] = parse_dt(raw["locked_until_utc"])
    if "game" in raw and isinstance(raw["game"], dict):
        # Convert any datetime strings back
        g = raw["game"]
        for key in ("kickoff_utc",):
            if key in g and isinstance(g[key], str):
                g[key] = parse_dt(g[key])
    with _state_lock:
        _lock_state.clear()
        _lock_state.update(raw)


def _persist() -> None:
    """Atomic write of current lock to disk."""
    with _state_lock:
        snapshot = dict(_lock_state)
    save_json(_DISK_FILE, snapshot)


_load_from_disk()


# ── Scoring ─────────────────────────────────────────────────────────────────

def _score_forecast(f: dict) -> int:
    """Given a forecast dict with temp/wind_speed/precip_pct/gust/short_forecast,
    return an integer weather-impact score."""
    if not f:
        return 0
    score = 0

    wind = f.get("wind_speed") or 0
    gust = f.get("gust")
    if wind >= 31:
        score += 45
    elif wind >= 21:
        score += 25
    elif wind >= 15:
        score += 10
    if gust and wind and gust >= wind + 8:
        score += 5

    precip = f.get("precip_pct") or 0
    if precip >= 80:
        score += 40
    elif precip >= 60:
        score += 20

    temp = f.get("temp")
    if temp is not None:
        if temp >= 100:
            score += 30
        elif temp >= 95:
            score += 15
        if temp <= 20:
            score += 40
        elif temp <= 32:
            score += 20

    short = (f.get("short_forecast") or "").lower()
    if "thunder" in short or "storm" in short:
        score += 15

    return score


def _story_line(f: dict) -> str:
    """One-line summary describing why this game is weather-notable.
    Prioritizes the most severe factor first."""
    if not f:
        return ""
    wind  = f.get("wind_speed") or 0
    gust  = f.get("gust")
    precip = f.get("precip_pct") or 0
    temp  = f.get("temp")
    short = f.get("short_forecast") or ""

    parts = []
    if precip >= 60:
        parts.append(f"{precip}% rain chance during game hours")
    if wind >= 15:
        gust_txt = f" (gusts to {int(gust)})" if gust and gust >= wind + 5 else ""
        parts.append(f"{int(wind)} mph winds{gust_txt}")
    if temp is not None and (temp >= 95 or temp <= 32):
        parts.append(f"{int(temp)}°F at first pitch")
    if "thunder" in short.lower() or "storm" in short.lower():
        parts.append("thunderstorm risk")

    if not parts:
        # Fell through — still show something readable
        pieces = []
        if temp is not None: pieces.append(f"{int(temp)}°F")
        if wind: pieces.append(f"{int(wind)} mph")
        if precip: pieces.append(f"{precip}% rain")
        return " · ".join(pieces)

    # Cap to two clauses so the strip stays scannable
    return ". ".join(parts[:2]).rstrip('.') + "."


# ── Sport adapters ──────────────────────────────────────────────────────────

def _mlb_candidates(now_utc: datetime) -> list[dict]:
    """MLB adapter — Kevin's rule is today-only for baseball (see
    SPORT_LOOKAHEAD_DAYS["mlb"] = 0)."""
    try:
        import mlb.cache as mlb_cache
    except Exception as e:
        print(f"[spotlight] mlb import failed: {e}", flush=True)
        return []

    out: list[dict] = []
    for date_str in _date_strs_for_sport("mlb"):
        slate, _meta = mlb_cache.get_slate(date_str, allow_build=False)
        if not slate:
            continue
        for g in slate:
            fp = g.get("first_pitch_utc")
            if not fp:
                continue
            # Only upcoming — skip games already started
            if fp <= now_utc:
                continue
            f = g.get("forecast")
            if not f:
                continue
            park = g.get("park") or {}
            venue_name = park.get("name") or g.get("venue") or "MLB game"
            city       = park.get("city") or ""
            away = g.get("away_name") or g.get("away_abbr") or ""
            home = g.get("home_name") or g.get("home_abbr") or ""
            slug = g.get("slug") or ""
            out.append({
                "sport":       "mlb",
                "sport_label": "MLB",
                "key":         f"mlb-{date_str}-{slug}",
                "title":       f"{away} @ {home}",
                "venue":       venue_name,
                "venue_city":  city,
                "kickoff_utc": fp,
                "kickoff_local_str": g.get("first_pitch_eastern_str") or "",
                "url_path":    f"/mlb/{date_str}/{slug}" if slug else "/mlb",
                "forecast":    dict(f),  # copy so we can freeze the picked snapshot
                "score":       _score_forecast(f),
            })
    return out


# Ordered list of sport-adapter callables. Add more sports by appending here.
SPORT_ADAPTERS = [
    _mlb_candidates,
    # _cfb_candidates,  # add when CFB season starts
    # _nfl_candidates,  # add when NFL preseason picks up
    # _mls_candidates,
    # _pga_candidates,
    # _nascar_candidates,
]


# ── Selection + lock management ─────────────────────────────────────────────

def _all_candidates(now_utc: datetime) -> list[dict]:
    """Gather candidates from every registered sport adapter."""
    out = []
    for adapter in SPORT_ADAPTERS:
        try:
            out.extend(adapter(now_utc))
        except Exception as e:
            print(f"[spotlight] adapter {adapter.__name__} failed: {e}", flush=True)
    return out


def _pick_best(candidates: list[dict]) -> Optional[dict]:
    """Return the highest-scoring candidate that clears the threshold, or None."""
    if not candidates:
        return None
    scored = sorted(candidates, key=lambda c: c["score"], reverse=True)
    top = scored[0]
    if top["score"] < _THRESHOLD_SCORE:
        return None
    return top


def _refresh_locked_game_forecast(now_utc: datetime) -> None:
    """When we have a locked pick, re-look up its current forecast so the
    numbers stay live even though the pick is stable. Only the forecast
    snapshot updates; the game identity is locked."""
    with _state_lock:
        current = _lock_state.get("game")
        key     = _lock_state.get("selection_key")
    if not current or not key:
        return
    fresh = _all_candidates(now_utc)
    for c in fresh:
        if c.get("key") == key:
            # Update just the forecast + score; keep everything else
            with _state_lock:
                _lock_state["game"]["forecast"] = c["forecast"]
                _lock_state["game"]["score"]    = c["score"]
                # Also update story line since forecast changed
                _lock_state["game"]["story"]    = _story_line(c["forecast"])
            _persist()
            return


def get_current() -> Optional[dict]:
    """Return the currently-featured game dict, or None if the strip should
    hide. Handles lock TTL, kickoff release, and re-pick automatically."""
    now_utc = datetime.now(timezone.utc)

    with _state_lock:
        locked_game = dict(_lock_state.get("game", {})) if _lock_state.get("game") else None
        locked_until = _lock_state.get("locked_until_utc")

    # Release the lock if kickoff has arrived on the locked game
    if locked_game:
        kickoff = locked_game.get("kickoff_utc")
        if kickoff and kickoff <= now_utc:
            _clear_lock()
            locked_game = None

    # Honor the 6-hour lock if still active
    if locked_game and locked_until and now_utc < locked_until:
        _refresh_locked_game_forecast(now_utc)
        with _state_lock:
            return dict(_lock_state.get("game", {})) or None

    # Lock expired or never set — re-pick
    candidates = _all_candidates(now_utc)
    top = _pick_best(candidates)
    if not top:
        # Nothing weather-notable; clear any stale lock and return None
        _clear_lock()
        return None

    # Enrich with story line, freeze the pick with lock window
    top["story"] = _story_line(top["forecast"])
    new_lock_until = now_utc + timedelta(hours=_LOCK_HOURS)
    # Never lock past kickoff — if kickoff is within 6h, cap the lock at kickoff
    if top.get("kickoff_utc") and top["kickoff_utc"] < new_lock_until:
        new_lock_until = top["kickoff_utc"]

    with _state_lock:
        _lock_state.clear()
        _lock_state["selection_key"]    = top["key"]
        _lock_state["locked_until_utc"] = new_lock_until
        _lock_state["game"]             = top
    _persist()

    return dict(top)


def _clear_lock() -> None:
    with _state_lock:
        _lock_state.clear()
    _persist()
