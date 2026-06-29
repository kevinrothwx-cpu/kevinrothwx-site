"""tennis.daily_summary — auto-generated weather summary for one Slam day.

PURE WEATHER FACTS ONLY. Same brand discipline as cfb/analysis.py — no
speculation about player performance, match length, court speed, etc.
Just the day's weather story plus what it means for outdoor vs roofed-
court playability (the tennis-specific meteorologist edge).

Used in /tennis/<slam_id>/<date> per-day detail page. Appears at the
bottom of the page as the SEO content block that AI search engines
extract and cite to mysportsweather.com.

Output: {"headline": str, "paragraph": str}
"""

from __future__ import annotations

from typing import Optional


def generate_daily_summary(day: dict, venue: dict) -> dict:
    """Return {headline, paragraph} for a Slam day.

    `day` shape: {"date_label", "summary": {...}, "hourly": [{...}, ...]}
    `venue` shape: SLAM_VENUES entry (has roof_note, total_courts,
                   roofed_courts, name, city)
    """
    summary = (day.get("summary") or {})
    hourly = day.get("hourly") or []

    high = _safe_int(summary.get("high_temp"))
    low = _safe_int(summary.get("low_temp"))
    wind = _safe_int(summary.get("avg_wind"))
    max_precip = _safe_int(summary.get("max_precip"))

    if not hourly and high is None:
        return {
            "headline": "Forecast pending.",
            "paragraph": "Daily weather forecast for this day will appear here as the date approaches.",
        }

    # Sentence 1: temp range + wind
    parts: list[str] = []
    if high is not None and low is not None:
        parts.append(f"High of {high}°F, low of {low}°F.")
    elif high is not None:
        parts.append(f"High of {high}°F.")
    if wind is not None:
        if wind < 6:
            parts.append(f"Light wind around {wind} mph.")
        elif wind >= 18:
            parts.append(f"Sustained wind near {wind} mph.")
        else:
            parts.append(f"Wind around {wind} mph.")

    # Sentence 2: precip story (when does it rain, how much)
    if max_precip is not None and max_precip >= 60 and hourly:
        rain_hours = _rain_hour_window(hourly, threshold=50)
        if rain_hours:
            parts.append(f"Showers likely between {rain_hours}, peak {max_precip}% chance.")
        else:
            parts.append(f"Showers likely, peak {max_precip}% chance.")
    elif max_precip is not None and max_precip >= 30:
        parts.append(f"Scattered showers possible, peak {max_precip}% chance.")
    elif max_precip is not None and max_precip < 15:
        parts.append("Minimal precipitation through play hours.")

    # Sentence 3: court playability — tennis-specific meteorologist edge.
    # Only mention if there's actual precip risk that day.
    if max_precip is not None and max_precip >= 50:
        roofed = _safe_int(venue.get("roofed_courts"))
        total = _safe_int(venue.get("total_courts"))
        if roofed and total:
            outers = total - roofed
            parts.append(
                f"Matches on the {roofed} roofed courts will continue uninterrupted; "
                f"the {outers} outer courts may be delayed during the precipitation window."
            )

    paragraph = " ".join(parts)

    # Headline: brief one-liner
    head_parts: list[str] = []
    if high is not None:
        head_parts.append(f"High {high}°F")
    if wind is not None and wind >= 15:
        head_parts.append(f"{wind} mph wind")
    if max_precip is not None and max_precip >= 60:
        head_parts.append(f"showers likely ({max_precip}%)")
    elif max_precip is not None and max_precip < 15:
        head_parts.append("dry")

    headline = ", ".join(head_parts) + "." if head_parts else "Daily forecast."

    return {"headline": headline, "paragraph": paragraph}


def _safe_int(v) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _rain_hour_window(hourly: list[dict], threshold: int = 50) -> str:
    """Find the contiguous-ish window of hours where precip >= threshold
    and return a human-readable 'X PM to Y PM' string. Empty if no window."""
    candidates = []
    for p in hourly:
        pct = _safe_int(p.get("precip_pct")) or 0
        if pct >= threshold:
            label = p.get("hour_local") or ""
            if label:
                candidates.append(label)
    if not candidates:
        return ""
    if len(candidates) == 1:
        return candidates[0]
    return f"{candidates[0]} and {candidates[-1]}"
