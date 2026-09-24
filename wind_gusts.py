"""
wind_gusts — when a gust number earns space on a summary card.

WHY THIS EXISTS (2026-09-24)
    NWS does publish gusts, but NOT on the /forecast/hourly endpoint that
    fills our tables. They live on the raw gridpoint grid, reported in km/h
    across variable-length ISO-8601 spans (one value can cover PT3H), so
    they have to be fetched separately and expanded per hour.

    Verified live against Lambeau Field on 2026-09-24: NWS gave 7/6/5/3/3
    mph for 7-11 PM ET while the NBM high-res feed gave 7/5/4/4/4, which
    cross-validates both sources.

KEVIN'S RULE (2026-09-24)
    A gust appears on a CARD only when BOTH are true:

        sustained wind >= 10 mph
        gust - sustained >= 5 mph

    A 7 mph gust on a 2 mph wind is noise. Printing it on the sixty calm
    games cheapens the number on the four where it decides the game.

    The HOURLY TABLES are deliberately NOT filtered. Kevin wants a gust on
    every hour there, so a reader can follow the trend even on a calm day.
    That asymmetry is intentional — do not "fix" it into consistency.

WHY THE RULE LIVES HERE AND NOT IN JINJA
    It was already in Jinja, twice, and the two copies had already drifted:
    ncaaf/_macros.html carried a hand-rolled `gust >= wind + 5` with no
    10 mph floor, and nfl/_macros.html had no threshold at all. Both were
    dead code — nothing ever populated `gust` for those sports — so the
    drift was invisible. One Python definition, two templates reading one
    boolean, keeps them from diverging again once data is flowing.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

# Kevin's thresholds. Both must be satisfied.
GUST_MIN_SUSTAINED_MPH = 10
GUST_MIN_EXCESS_MPH = 5

_KMH_TO_MPH = 0.621371
_ISO_HOURS_RE = re.compile(r"PT(\d+)H")


def gust_is_notable(wind_speed, gust) -> bool:
    """True when this wind/gust pair earns a spot on a summary card.

    Never raises. Missing or non-numeric values read as "not notable",
    which is the safe direction: a card silently omits the gust rather
    than rendering "None mph"."""
    if wind_speed is None or gust is None:
        return False
    try:
        w = float(wind_speed)
        g = float(gust)
    except (TypeError, ValueError):
        return False
    return w >= GUST_MIN_SUSTAINED_MPH and (g - w) >= GUST_MIN_EXCESS_MPH


def annotate_card_gust(forecast: Optional[dict]) -> Optional[dict]:
    """Stamp forecast['gust_notable'] so templates read a boolean instead
    of re-deriving the rule. Mutates and returns the same dict."""
    if not forecast:
        return forecast
    try:
        forecast["gust_notable"] = gust_is_notable(
            forecast.get("wind_speed"), forecast.get("gust")
        )
    except Exception:
        forecast["gust_notable"] = False
    return forecast


def expand_gust_series(gust_obj: Optional[dict]) -> dict[str, int]:
    """Turn an NWS gridpoint windGust object into {iso_utc_hour: mph}.

    NWS gives entries like:
        {"validTime": "2026-09-24T01:00:00+00:00/PT1H", "value": 7.408}

    The span can be longer than an hour, so each entry is expanded into
    every hour it covers. Values arrive in km/h (uom 'wmoUnit:km_h-1') and
    are converted to whole mph.

    Returns {} on anything malformed rather than raising — a missing gust
    row is a cosmetic loss, not a reason to fail a slate build.

    NOTE: mlb/nws.py has an equivalent private implementation predating
    this one, still used by golf, NASCAR and tennis. Left alone on purpose;
    refactoring a working in-season path to share this is a quiet-week job.
    """
    if not gust_obj:
        return {}
    try:
        values = gust_obj.get("values") or []
        is_kmh = "km_h-1" in (gust_obj.get("uom") or "")
        out: dict[str, int] = {}
        for entry in values:
            valid_time = entry.get("validTime", "")
            val = entry.get("value")
            if val is None or "/" not in valid_time:
                continue
            time_str, duration_str = valid_time.split("/", 1)
            try:
                start = datetime.fromisoformat(time_str)
            except ValueError:
                continue
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            start_utc = start.astimezone(timezone.utc).replace(
                minute=0, second=0, microsecond=0
            )
            m = _ISO_HOURS_RE.match(duration_str or "")
            hours = int(m.group(1)) if m else 1
            mph = round(float(val) * (_KMH_TO_MPH if is_kmh else 1.0))
            for h in range(hours):
                out[(start_utc + timedelta(hours=h)).isoformat()] = mph
        return out
    except Exception:
        return {}


def attach_gusts_to_periods(periods: Optional[list],
                            gusts: Optional[dict]) -> Optional[list]:
    """Fill each period's 'gust' from an expanded {iso_hour: mph} map.

    Only fills periods whose gust is still None, so a value already set by
    HRRR or another source wins. Mutates in place and returns the list."""
    if not periods or not gusts:
        return periods
    for p in periods:
        try:
            if p.get("gust") is not None:
                continue
            st_raw = p.get("start_time")
            if not st_raw:
                continue
            st = datetime.fromisoformat(st_raw)
            if st.tzinfo is None:
                st = st.replace(tzinfo=timezone.utc)
            st_utc = st.astimezone(timezone.utc).replace(
                minute=0, second=0, microsecond=0
            )
            p["gust"] = gusts.get(st_utc.isoformat())
        except Exception:
            continue
    return periods
