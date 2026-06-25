"""tennis.venues — the 4 Grand Slam venues.

Each venue is at a fixed location and the same physical site every year, so
hard-coding is the right call (no point hitting an ESPN scoreboard for
something that hasn't moved since the 1800s in Wimbledon's case).

Roof data is meteorologist-edge content: tennis is the only major sport
where the venue's weather-resilience depends on which court a match is
played on. We surface this as static metadata so the page can say things
like "3 of 22 courts have retractable roofs — outer-court matches likely
delayed if rain materializes."

nws_unsupported=True on the three international venues skips the NWS layer
and goes straight to WeatherAPI (mirrors worldcup/ international handling).
"""

SLAM_VENUES = {
    # ──────────────────────────────────────────────────────────────────
    "australian_open": {
        "name":            "Melbourne Park",
        "city":            "Melbourne, Australia",
        "country":         "AU",
        "lat":             -37.8225,
        "lon":              145.0078,
        "timezone":        "Australia/Melbourne",
        "nws_unsupported": True,
        "roofed_courts":   3,
        "total_courts":    24,
        "roof_note":       "Rod Laver Arena, Margaret Court Arena, and John Cain Arena have retractable roofs.",
    },
    # ──────────────────────────────────────────────────────────────────
    "french_open": {
        "name":            "Stade Roland Garros",
        "city":            "Paris, France",
        "country":         "FR",
        "lat":              48.8467,
        "lon":               2.2474,
        "timezone":        "Europe/Paris",
        "nws_unsupported": True,
        "roofed_courts":   2,
        "total_courts":    18,
        "roof_note":       "Philippe-Chatrier (since 2020) and Suzanne-Lenglen (since 2024) have retractable roofs. The 16 outer courts are exposed.",
    },
    # ──────────────────────────────────────────────────────────────────
    "wimbledon": {
        "name":            "All England Lawn Tennis & Croquet Club",
        "city":            "London, United Kingdom",
        "country":         "GB",
        "lat":              51.4344,
        "lon":              -0.2143,
        "timezone":        "Europe/London",
        "nws_unsupported": True,
        "roofed_courts":   2,
        "total_courts":    18,
        "roof_note":       "Centre Court (roof since 2009) and No. 1 Court (roof since 2019). The 16 outer courts have no protection from rain.",
    },
    # ──────────────────────────────────────────────────────────────────
    "us_open": {
        "name":            "USTA Billie Jean King National Tennis Center",
        "city":            "New York, NY",
        "country":         "US",
        "lat":              40.7503,
        "lon":              -73.8454,
        "timezone":        "America/New_York",
        "nws_unsupported": False,  # CONUS → NWS works, HRRR too
        "roofed_courts":   2,
        "total_courts":    22,
        "roof_note":       "Arthur Ashe (roof since 2016) and Louis Armstrong (roof since 2018). Other courts including Grandstand are uncovered.",
    },
}


def get_venue(slam_id: str) -> dict | None:
    """Return the venue meta for a Slam ID, or None if unknown."""
    return SLAM_VENUES.get(slam_id)
