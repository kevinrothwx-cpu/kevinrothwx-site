"""
OVERcast Wind Direction Module
===============================
Converts raw WIND_DIRECTION_DEGREES into park-relative wind buckets
(OUT / IN / CROSS) and human-readable direction labels.

Meteorological convention: WIND_DIRECTION_DEGREES is the direction
the wind is coming FROM (270° = wind coming from the west, blowing east).
"""

import math
from typing import Optional


# ── Core angle math ───────────────────────────────────────────────────

def angle_diff(a: float, b: float) -> float:
    """Smallest angular difference between two compass bearings (0–180)."""
    d = abs(a - b) % 360
    return min(d, 360 - d)


def signed_angle_diff(a: float, b: float) -> float:
    """
    Signed difference: how far a is from b, clockwise positive.
    Result is in (-180, 180].
    Useful for determining LF vs RF side of the field.
    """
    d = (a - b) % 360
    if d > 180:
        d -= 360
    return d


# ── Wind bucket classification ────────────────────────────────────────

def get_wind_bucket(
    wind_deg: float,
    cf_bearing: float,
    out_threshold: float = 50.0,
    in_threshold: float = 45.0,
) -> str:
    """
    Classify wind direction relative to park orientation.

    Args:
        wind_deg:       Meteorological wind direction (FROM direction).
        cf_bearing:     Compass bearing from home plate to center field.
        out_threshold:  Half-angle (degrees) for OUT classification.
        in_threshold:   Half-angle (degrees) for IN classification.

    Returns:
        "out" | "in" | "cross"
    """
    # Wind blowing OUT toward CF: wind coming FROM behind home plate
    out_center = (cf_bearing + 180) % 360
    # Wind blowing IN from CF: wind coming FROM center field direction
    in_center = cf_bearing

    if angle_diff(wind_deg, out_center) <= out_threshold:
        return "out"
    elif angle_diff(wind_deg, in_center) <= in_threshold:
        return "in"
    else:
        return "cross"


# ── Human-readable wind label ─────────────────────────────────────────

def get_wind_label(wind_deg: float, cf_bearing: float, wind_speed: float) -> str:
    """
    Return a descriptive wind label like 'Out to CF', 'Cross LF → RF',
    or 'In from LF'.

    LF is to the left of center (counterclockwise from CF when viewed
    from home plate), RF is to the right.
    """
    out_center = (cf_bearing + 180) % 360
    in_center = cf_bearing

    bucket = get_wind_bucket(wind_deg, cf_bearing)

    if wind_speed == 0:
        return "Calm"

    if bucket == "out":
        # Determine which part of the outfield
        signed = signed_angle_diff(wind_deg, out_center)
        if abs(signed) <= 15:
            return "Out to CF"
        elif signed > 0:
            return "Out to RF"
        else:
            return "Out to LF"

    elif bucket == "in":
        signed = signed_angle_diff(wind_deg, in_center)
        if abs(signed) <= 15:
            return "In from CF"
        elif signed > 0:
            return "In from RF"
        else:
            return "In from LF"

    else:  # cross
        # Determine cross direction: which way across the field
        # signed_angle_diff from out_center tells us LF→RF or RF→LF
        signed = signed_angle_diff(wind_deg, out_center)
        # Positive signed = wind is clockwise from out_center = toward RF side
        if signed > 0:
            return "Cross LF → RF"
        else:
            return "Cross RF → LF"


def get_wind_arrow(label: str) -> str:
    """Map a wind label to a unicode arrow for the UI."""
    arrows = {
        "Out to CF":       "↑",
        "Out to RF":       "↗",
        "Out to LF":       "↖",
        "In from CF":      "↓",
        "In from RF":      "↙",
        "In from LF":      "↘",
        "Cross LF → RF":   "→",
        "Cross RF → LF":   "←",
        "Calm":            "○",
    }
    return arrows.get(label, "→")


# ── Full wind info bundle ──────────────────────────────────────────────

def get_wind_info(
    wind_deg: Optional[float],
    cf_bearing: float,
    wind_speed: float = 0.0,
) -> dict:
    """
    Return the full wind info dict for a given game.
    Handles missing wind direction gracefully.
    """
    if wind_deg is None or math.isnan(wind_deg):
        return {
            "bucket": None,
            "label": "Wind direction unknown",
            "arrow": "?",
            "wind_speed": wind_speed,
        }

    bucket = get_wind_bucket(wind_deg, cf_bearing)
    label = get_wind_label(wind_deg, cf_bearing, wind_speed)
    arrow = get_wind_arrow(label)

    return {
        "bucket": bucket,
        "label": label,
        "arrow": arrow,
        "wind_speed": wind_speed,
    }



# ── Compass direction label ─────────────────────────────────────

_COMPASS_16 = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
               "S","SSW","SW","WSW","W","WNW","NW","NNW"]
_COMPASS_8  = ["N","NE","E","SE","S","SW","W","NW"]


def wind_compass(deg, points: int = 16) -> str:
    """
    Convert meteorological wind direction (FROM, 0-360°) to a compass label.

    points=16  →  N, NNE, NE, ENE, ...    (default; hourly forecast detail)
    points=8   →  N, NE, E, SE, S, SW, W, NW  (cheat-sheet brevity)

    Returns "" for None/NaN/Calm.
    """
    if deg is None:
        return ""
    try:
        import math
        d = float(deg) % 360
        if math.isnan(d):
            return ""
    except Exception:
        return ""

    labels = _COMPASS_16 if points == 16 else _COMPASS_8
    bucket = int((d + (180 / len(labels))) % 360 // (360 / len(labels)))
    return labels[bucket]
