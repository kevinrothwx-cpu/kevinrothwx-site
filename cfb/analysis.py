"""
cfb.analysis — auto-generated meteorologist analysis for CFB games.

Strategy (per Kevin's brand stance discussed mid-session): we do NOT use
generative AI to write text content. That contradicts the "Built by a
meteorologist, not AI" positioning across the site. Instead we use
deterministic rule-based templating to produce 2-4 sentences of analysis
per game from the forecast values.

These paragraphs are:
- Factually accurate (derived from forecast numbers, not invented)
- Meteorologically-correct (use real weather impact rules on football)
- Citable by AI Overviews / Perplexity / Claude / ChatGPT — they parse our
  structured factual claims and cite them with Kevin's byline
- Brand-consistent — Kevin can stand behind every sentence as a meteorologist

The AI-SEO win is in the structured factual content + the credentialed
byline (E-E-A-T). AI tools that summarize sports weather content will
preferentially cite a credentialed source over a generic weather widget.

Input: game dict from cfb/slate.py (schedule + forecast attached).
Output: dict with:
  - "headline": one-sentence summary of key weather story
  - "paragraph": 2-4 sentence analysis paragraph
  - "tags": list of meteorologist-edge category tags ("cold-game",
    "high-wind", "snow-game", etc.) for use in card highlighting and
    schema.org keyword markup
"""

from __future__ import annotations

from typing import Optional


# ── Thresholds ────────────────────────────────────────────────────────────

COLD_TEMP        = 32   # Below freezing: kicking + ball handling concerns
FREEZING_TEMP    = 25   # Severe cold: hand warmers, hypothermia risk
HOT_TEMP         = 85   # Hot game: heat exhaustion, cramping
SEVERE_HOT_TEMP  = 92   # Heat advisory: significant performance impact

HIGH_WIND_MPH    = 18   # Affects passing efficiency, especially long throws
SEVERE_WIND_MPH  = 25   # Major impact on kicking + passing game

HIGH_PRECIP_PCT  = 60   # Likely to affect ball handling
HEAVY_PRECIP_PCT = 80   # Definitely a wet-field game


# ── Public API ────────────────────────────────────────────────────────────

def generate_analysis(game: dict) -> dict:
    """Generate the analysis dict for a single game.

    Returns:
        {
            "headline": str (1 sentence),
            "paragraph": str (2-4 sentences),
            "tags": list[str],
        }
        Or, when no weather data is available, a minimal dict with a
        "Forecast pending" placeholder.
    """
    f = game.get("forecast")
    venue = game.get("venue") or {}

    if not f:
        return {
            "headline": "Forecast pending.",
            "paragraph": "Live weather forecast for this game will appear here as kickoff approaches.",
            "tags": [],
        }

    # Indoor games — weather is largely irrelevant
    roof = venue.get("roof")
    if roof in ("fixed_dome", "retractable"):
        # Note: retractable could still be relevant if open, but our v1 data
        # doesn't track open/closed state. Treat as indoor for safety.
        indoor_word = "Indoors" if roof == "fixed_dome" else "Likely indoors"
        return {
            "headline": f"{indoor_word} at {venue.get('name', 'this venue')}; weather neutral.",
            "paragraph": (
                f"This game is scheduled to play under cover at "
                f"{venue.get('name', 'the venue')}. Weather conditions outside "
                f"will not affect play."
            ),
            "tags": ["indoor"],
        }

    temp = _safe_int(f.get("temp"))
    wind = _safe_int(f.get("wind_speed"))
    pop = _safe_int(f.get("precip_pct"))
    short_fc = (f.get("short_forecast") or "").lower()
    feels_like = _safe_int(f.get("feels_like"))
    gust = _safe_int(f.get("gust"))

    tags: list[str] = []
    sentences: list[str] = []
    headline_parts: list[str] = []

    # ── Temperature ─────────────────────────────────────────────────────
    temp_sentence = ""
    if temp is not None:
        if temp <= FREEZING_TEMP:
            tags.append("freezing")
            tags.append("cold-game")
            headline_parts.append(f"sub-freezing {temp}°F")
            extra = f" Feels-like {feels_like}°F." if feels_like is not None and feels_like < temp - 3 else ""
            temp_sentence = (
                f"Temperature {temp}°F at kickoff, well below freezing.{extra} "
                f"Field-goal accuracy drops measurably under {COLD_TEMP}°F and "
                f"fumble risk elevates with cold ball handling."
            )
        elif temp <= COLD_TEMP:
            tags.append("cold-game")
            headline_parts.append(f"cold {temp}°F")
            extra = f" Feels-like {feels_like}°F." if feels_like is not None and feels_like < temp - 3 else ""
            temp_sentence = (
                f"Temperature near freezing at {temp}°F.{extra} Cold-weather "
                f"kicking historically less accurate at extended ranges."
            )
        elif temp >= SEVERE_HOT_TEMP:
            tags.append("heat-advisory")
            tags.append("hot-game")
            headline_parts.append(f"heat {temp}°F")
            extra = f" Feels-like {feels_like}°F." if feels_like is not None and feels_like > temp + 3 else ""
            temp_sentence = (
                f"Heat advisory in effect with kickoff temperature {temp}°F.{extra} "
                f"Hydration breaks and cramping concerns through the second half."
            )
        elif temp >= HOT_TEMP:
            tags.append("hot-game")
            headline_parts.append(f"warm {temp}°F")
            temp_sentence = f"Warm conditions at kickoff with temperature {temp}°F."

    if temp_sentence:
        sentences.append(temp_sentence)

    # ── Wind ─────────────────────────────────────────────────────────────
    wind_sentence = ""
    if wind is not None:
        gust_clause = f" with gusts to {gust} mph" if gust and gust >= wind + 5 else ""
        if wind >= SEVERE_WIND_MPH:
            tags.append("severe-wind")
            tags.append("wind-game")
            headline_parts.append(f"severe wind {wind} mph")
            wind_sentence = (
                f"Sustained {wind} mph wind{gust_clause} creates a major "
                f"factor for passing efficiency and field-goal kicking. Expect "
                f"both offenses to lean toward the run game."
            )
        elif wind >= HIGH_WIND_MPH:
            tags.append("wind-game")
            headline_parts.append(f"wind {wind} mph")
            wind_sentence = (
                f"Sustained {wind} mph wind{gust_clause} introduces a notable "
                f"effect on deep passing routes and long field-goal attempts."
            )
    if wind_sentence:
        sentences.append(wind_sentence)

    # ── Precipitation ────────────────────────────────────────────────────
    precip_sentence = ""
    if pop is not None and pop >= HIGH_PRECIP_PCT:
        is_snow = "snow" in short_fc
        is_mix = "mix" in short_fc or ("snow" in short_fc and "rain" in short_fc)
        is_storm = "thunder" in short_fc or "storm" in short_fc

        if is_storm:
            tags.append("storm-risk")
            tags.append("lightning-risk")
            headline_parts.append("storms")
            precip_sentence = (
                f"Thunderstorm probability {pop}% at kickoff window. Lightning "
                f"delays possible and game flow may be interrupted."
            )
        elif is_snow and not is_mix:
            tags.append("snow-game")
            headline_parts.append("snow")
            heavy = "Heavy" if pop >= HEAVY_PRECIP_PCT else "Likely"
            precip_sentence = (
                f"{heavy} snow expected, probability {pop}%. Accumulation may "
                f"affect footing and ball handling; expect run-heavy gameplan."
            )
        elif is_mix:
            tags.append("mixed-precip")
            headline_parts.append("rain to snow")
            precip_sentence = (
                f"Mixed precipitation expected, probability {pop}%. Watch for "
                f"transitions between rain and snow during the game window."
            )
        else:
            tags.append("rain-game")
            headline_parts.append("rain")
            heavy = "Heavy" if pop >= HEAVY_PRECIP_PCT else "Likely"
            precip_sentence = (
                f"{heavy} rain expected, probability {pop}%. Wet ball + slick "
                f"footing favor the run game and elevate fumble risk."
            )

    if precip_sentence:
        sentences.append(precip_sentence)

    # ── Default sentence for routine/clear games ─────────────────────────
    if not sentences:
        tags.append("clear")
        sentences.append(
            f"Routine weather expected at kickoff: {temp}°F with {wind} mph "
            f"wind. Minimal effect on the game expected from atmospheric "
            f"conditions."
        )

    paragraph = " ".join(sentences)

    # ── Headline ─────────────────────────────────────────────────────────
    if headline_parts:
        headline = "Weather notes: " + ", ".join(headline_parts) + "."
    else:
        headline = "Routine weather; no significant impact expected."

    return {
        "headline": headline,
        "paragraph": paragraph,
        "tags": tags,
    }


# ── Internal helpers ──────────────────────────────────────────────────────

def _safe_int(v) -> Optional[int]:
    """Defensive int conversion. Returns None for anything that can't be cast."""
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
