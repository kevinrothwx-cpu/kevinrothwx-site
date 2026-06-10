"""
worldcup.stadium_notes - climatological context per World Cup venue.

Each entry is a short meteorologist's read on the stadium: roof status
first (the single most important factor for outdoor matches), then the
actual weather story for the venue during the World Cup window (June 11
through July 19, 2026).

Lookup keys must match the canonical venue name in worldcup.venues.
Missing venues just don't render a notes section on the match page.
"""

from __future__ import annotations


STADIUM_NOTES: dict[str, str] = {

    # ──────────────────────────────────────────────────────────────────
    # US venues with retractable roofs
    # ──────────────────────────────────────────────────────────────────

    "Mercedes-Benz Stadium": (
        "Retractable roof. Atlanta in summer regularly delivers low 80s "
        "temperatures, dewpoints near 70, and a near-daily afternoon "
        "thunderstorm pattern, so the pinwheel roof is more likely to be "
        "closed than open. When open, expect a humid, sticky feel and a "
        "light variable wind. The roof takes about 12 minutes to operate, "
        "so the call gets made well before kickoff."
    ),

    "AT&T Stadium": (
        "Retractable roof. North Texas in June and July routinely runs 95 "
        "to 105 degrees with heat indices well above the player-safety "
        "thresholds FIFA flags, so expect closed-roof matches by default. "
        "Open-roof play would only happen on the rare summer cool front or "
        "an evening kickoff with thunderstorm-cooled air in place."
    ),

    "NRG Stadium": (
        "Retractable roof. Houston during the World Cup window means Gulf "
        "moisture, dewpoints in the mid-70s, and wet-bulb temperatures that "
        "trip outdoor-play safety thresholds, so expect closed roof for "
        "nearly every match. The roof also shelters against the daily "
        "afternoon thunderstorm and lightning risk that defines a Houston "
        "summer afternoon."
    ),

    # ──────────────────────────────────────────────────────────────────
    # US venues with fixed canopies (field still open to weather)
    # ──────────────────────────────────────────────────────────────────

    "SoFi Stadium": (
        "Fixed translucent canopy over the seating bowl, but the sides are "
        "open so wind and outside air still reach the field. The Los "
        "Angeles basin's marine layer typically sits over Inglewood in the "
        "morning and burns off by afternoon kickoff. Expect mild mid-70s "
        "temperatures, low humidity, and a light westerly sea breeze. "
        "Comfortable conditions are the norm."
    ),

    "Hard Rock Stadium": (
        "Fixed canopy covers the upper deck, but the field itself is open "
        "to sky and weather. South Florida in June and July is the most "
        "challenging weather venue on the schedule: dewpoints near 75, "
        "heat indices in the upper 90s, and afternoon thunderstorms "
        "develop almost daily off the sea breeze. Lightning is the most "
        "likely match-disrupting factor."
    ),

    # ──────────────────────────────────────────────────────────────────
    # US open-air venues
    # ──────────────────────────────────────────────────────────────────

    "Gillette Stadium": (
        "Open-air stadium about 25 miles inland from the Atlantic. Summer "
        "matches in Foxborough typically run 75 to 82 degrees with "
        "moderate humidity and a southwest sea breeze that picks up by "
        "mid-afternoon. The main weather risk is a pop-up thunderstorm, "
        "more often a brief disruption than a sustained event."
    ),

    "Arrowhead Stadium": (
        "Open-air stadium in the heart of severe-weather country. Summer "
        "matches typically run upper 80s with humid southerly flow off the "
        "southern Plains feeding daily afternoon and evening thunderstorm "
        "development. Damaging wind and large hail are real possibilities "
        "during June and July squall lines. Watch the radar."
    ),

    "MetLife Stadium": (
        "Open-air stadium in the New York metro. Summer matches typically "
        "run mid-80s with humid southerly flow off the Mid-Atlantic and "
        "dewpoints around 70. Pop-up thunderstorms develop along the sea "
        "breeze most afternoons, and the urban-heat-island effect bumps "
        "evening temperatures a few degrees above the regional average."
    ),

    "Lincoln Financial Field": (
        "Open-air stadium roughly 50 miles inland from the Atlantic. "
        "Summer matches run hot and humid in the mid to upper 80s with a "
        "light urban-heat-island bump after sunset. The main weather risk "
        "is a severe afternoon thunderstorm tied to a southwesterly flow "
        "ahead of cold fronts that swing through the Mid-Atlantic in June "
        "and July."
    ),

    "Levi's Stadium": (
        "Open-air stadium in the South Bay. The signature feature is an "
        "afternoon onshore breeze that funnels through the bay around 3 "
        "to 4 PM local, often gusting 20 mph and dropping temperatures "
        "10 degrees in an hour. West-facing seats catch the full "
        "afternoon sun. Conditions are typically comfortable but "
        "variable through a match."
    ),

    "Lumen Field": (
        "Partial canopy covers most seats, but the field is open to the "
        "sky. Pacific Northwest summers are the driest part of the year "
        "in Seattle. Expect mild conditions in the 70s, low humidity by "
        "World Cup standards, and a steady south-southwesterly flow off "
        "Puget Sound. Rain is unlikely but always possible in this "
        "climate."
    ),

    # ──────────────────────────────────────────────────────────────────
    # Canadian venues
    # ──────────────────────────────────────────────────────────────────

    "BC Place": (
        "Retractable roof. Vancouver's summer climate is mild and dry by "
        "Canadian standards, with comfortable upper 60s to mid-70s "
        "temperatures and low humidity. The roof is more likely to be open "
        "than closed for World Cup matches, with the call driven mostly "
        "by precipitation on the radar."
    ),

    "BMO Field": (
        "Open-air stadium on Lake Ontario's waterfront. Summer matches "
        "typically run upper 70s to mid-80s with a moderating lake breeze "
        "that kicks in by mid-afternoon. Late-day thunderstorms are the "
        "main weather concern, especially during humid stretches in June "
        "and July when the lake breeze front becomes a focus for storm "
        "development."
    ),

    # ──────────────────────────────────────────────────────────────────
    # Mexican venues
    # ──────────────────────────────────────────────────────────────────

    "Estadio Azteca": (
        "Open-air stadium at 7,200 feet above sea level, where the air is "
        "roughly 20 percent thinner than at sea level. Lower air density "
        "affects ball flight, sustained running, and the feel of any wind "
        "on the pitch. June marks the start of Mexico City's rainy "
        "season: afternoon thunderstorms are common, and overnight "
        "temperatures drop into the 50s. Daytime matches typically run "
        "in the 70s."
    ),

    "Estadio Akron": (
        "Open-air stadium at roughly 5,100 feet above sea level. Air "
        "density is meaningfully reduced, though less dramatically than "
        "Mexico City. June begins Guadalajara's rainy season with "
        "afternoon and evening thunderstorms, and match-time temperatures "
        "typically run mild in the 70s. Cooler and stormier than "
        "Mexico's coastal venues."
    ),

    "Estadio BBVA": (
        "Partial canopy covers the seating bowl, with the field open to "
        "the sky. Northern Mexico in summer means hot, dry conditions: "
        "temperatures regularly push past 95 degrees with low humidity, "
        "much drier than anywhere else on the World Cup schedule. The "
        "Sierra Madre to the west occasionally triggers afternoon "
        "thunderstorms, but most matches will be hot and dry."
    ),
}


def get_stadium_notes(venue_name: str) -> str:
    """Return the climatological notes for a venue, or empty string if not in lookup."""
    if not venue_name:
        return ""
    return STADIUM_NOTES.get(venue_name, "")
