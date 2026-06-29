"""cfb.analysis — auto-generated weather summary for CFB games.

PURE WEATHER FACTS ONLY. No football-impact speculation.

The summary appears at the bottom of /ncaaf/<date>/<slug>. It's also what
AI Overview / ChatGPT / Perplexity / Claude extract and cite, so we keep
it tightly scoped to weather facts only. Football-outcome analysis is
PropFinder / OVERcast territory; we don't speculate about kicking accuracy,
ball handling, gameplans, or anything game-adjacent here.

Strategy (per Kevin's brand stance):
- No generative AI for text content
- Deterministic rule-based templating from forecast values
- Every sentence is a meteorologist-defensible statement
- AI-SEO win comes from structured factual content + credentialed byline
"""

from __future__ import annotations
from typing import Optional


_WIND_DIR_LONG = {
    "N":   "the north",
    "NNE": "the north-northeast",
    "NE":  "the northeast",
    "ENE": "the east-northeast",
    "E":   "the east",
    "ESE": "the east-southeast",
    "SE":  "the southeast",
    "SSE": "the south-southeast",
    "S":   "the south",
    "SSW": "the south-southwest",
    "SW":  "the southwest",
    "WSW": "the west-southwest",
    "W":   "the west",
    "WNW": "the west-northwest",
    "NW":  "the northwest",
    "NNW": "the north-northwest",
}


def generate_analysis(game: dict) -> dict:
    """Return {headline, paragraph, tags} for a CFB game.

    Pure weather facts. Two sentences typical: temp + wind, then precip
    (only if notable). Indoor games get a one-line dome notice instead.
    """
    venue = game.get("venue") or {}
    roof = (venue.get("roof_type") or "").lower()
    forecast = game.get("forecast")

    if roof in ("fixed_dome", "fixed-dome"):
        return {
            "headline": "Domed venue, no weather impact.",
            "paragraph": "Game played inside a fixed dome. Outdoor weather has no effect on play.",
            "tags": ["indoor"],
        }

    if not forecast:
        return {"headline": "Forecast unavailable.", "paragraph": "", "tags": []}

    temp       = _safe_int(forecast.get("temp"))
    wind_speed = _safe_int(forecast.get("wind_speed"))
    wind_deg   = forecast.get("wind_deg")
    precip_pct = _safe_int(forecast.get("precip_pct"))
    short_fc   = (forecast.get("short_forecast") or "").lower()

    snow_likely = (
        "snow" in short_fc or
        (temp is not None and temp <= 32 and precip_pct is not None and precip_pct >= 30)
    )

    parts: list[str] = []

    if temp is not None and wind_speed is not None:
        wind_dir = _deg_to_compass(wind_deg) if wind_deg is not None else ""
        wind_dir_long = _WIND_DIR_LONG.get(wind_dir, "")
        wind_modifier = ""
        if wind_speed < 6:
            wind_modifier = "light "
        elif wind_speed >= 16:
            wind_modifier = "sustained "
        wind_phrase = f"{wind_modifier}{wind_speed} mph wind"
        if wind_dir_long:
            wind_phrase += f" from {wind_dir_long}"
        parts.append(f"Temperature {temp} degrees at kickoff with {wind_phrase}.")
    elif temp is not None:
        parts.append(f"Temperature {temp} degrees at kickoff.")

    if precip_pct is not None:
        if precip_pct >= 60:
            precip_word = "Snow showers" if snow_likely else "Showers"
            parts.append(f"{precip_word} likely, {precip_pct}% chance through the game window.")
        elif precip_pct >= 30:
            precip_word = "snow" if snow_likely else "rain"
            parts.append(f"Scattered {precip_word} possible, {precip_pct}% chance.")
        elif precip_pct < 15:
            parts.append("Minimal precipitation through the game window.")

    paragraph = " ".join(parts)

    headline_parts: list[str] = []
    if temp is not None:
        headline_parts.append(f"{temp} degrees")
    if wind_speed is not None and wind_speed >= 18:
        headline_parts.append(f"{wind_speed} mph wind")
    if precip_pct is not None and precip_pct >= 60:
        headline_parts.append("snow likely" if snow_likely else "showers likely")

    headline = (", ".join(headline_parts) + " at kickoff.") if headline_parts else "Forecast at kickoff."

    tags: list[str] = []
    if temp is not None:
        if temp <= 32:
            tags.append("cold")
        elif temp >= 85:
            tags.append("hot")
    if wind_speed is not None and wind_speed >= 18:
        tags.append("wind")
    if precip_pct is not None and precip_pct >= 60:
        tags.append("snow" if snow_likely else "rain")
    if not tags:
        tags = ["routine"]

    return {"headline": headline, "paragraph": paragraph, "tags": tags}


def _safe_int(v) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _deg_to_compass(deg) -> str:
    try:
        d = float(deg)
    except (TypeError, ValueError):
        return ""
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return dirs[int((d + 11.25) / 22.5) % 16]
