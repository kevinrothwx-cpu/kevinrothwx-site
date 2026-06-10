"""
golf.wind_impact — classify forecast wind relative to each hole.

Mirrors mlb.wind's OUT/IN/CROSS treatment, applied per hole:
  helping — wind blows toward the green (within ±45° of play direction)
  hurting — wind blows back toward the tee (within ±45° of the reverse)
  cross   — everything else

Meteorological convention: wind_deg is the direction the wind is coming
FROM (270° = west wind, blowing east). Play direction is the tee→green
bearing, so we compare against the wind's TO direction.
"""

from __future__ import annotations

import math
from typing import Optional

HELPING_HALF_ANGLE = 45.0   # |relative angle| <= this  → helping
HURTING_HALF_ANGLE = 45.0   # |relative angle| >= 180 - this → hurting


def relative_angle(hole_bearing: float, wind_from_deg: float) -> float:
    """
    Signed angle between the wind's TO direction and the hole's play
    direction, in [-180, 180]. 0 = dead tailwind, ±180 = dead headwind.
    """
    wind_to = (wind_from_deg + 180.0) % 360.0
    return ((wind_to - hole_bearing) + 540.0) % 360.0 - 180.0


def hole_wind_impact(hole_bearing: float, wind_from_deg: Optional[float]) -> str:
    """Classify one hole: 'helping' | 'hurting' | 'cross' | 'unknown'."""
    if wind_from_deg is None:
        return "unknown"
    try:
        rel = abs(relative_angle(float(hole_bearing), float(wind_from_deg)))
    except (TypeError, ValueError):
        return "unknown"
    if math.isnan(rel):
        return "unknown"
    if rel <= HELPING_HALF_ANGLE:
        return "helping"
    if rel >= 180.0 - HURTING_HALF_ANGLE:
        return "hurting"
    return "cross"


def attach_wind_impact(course_map: dict, wind_from_deg: Optional[float]) -> dict:
    """Set hole['impact'] on every hole of a prepared course map (in place)."""
    for h in course_map.get("holes", []):
        h["impact"] = hole_wind_impact(h["bearing"], wind_from_deg)
    return course_map


def circular_mean_deg(degrees: list[float]) -> Optional[float]:
    """
    Vector-average a list of compass directions (avoids the 350°/10°
    arithmetic-mean trap). Returns 0–359 int, or None if undefined.
    """
    if not degrees:
        return None
    x = sum(math.cos(math.radians(d)) for d in degrees)
    y = sum(math.sin(math.radians(d)) for d in degrees)
    if abs(x) < 1e-9 and abs(y) < 1e-9:
        return None  # perfectly opposing winds — no meaningful mean
    return round(math.degrees(math.atan2(y, x))) % 360
