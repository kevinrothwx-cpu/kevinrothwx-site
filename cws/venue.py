"""cws.venue — the one venue."""

CHARLES_SCHWAB_FIELD = {
    "name":              "Charles Schwab Field Omaha",
    "city":              "Omaha, NE",
    "country":           "US",
    "lat":               41.2570,
    "lon":               -95.9251,
    "timezone":          "America/Chicago",
    "roof_type":         "open_air",
    "cf_bearing_degrees": 135,  # CF points SE (home plate in NW corner of field)
    "aliases":           ["Charles Schwab Field", "TD Ameritrade Park", "Omaha"],
}

# Calendar window: hard-coded for 2026. Originally Jun 12-24 but the
# tournament wrapped on Jun 21 (Kevin updated Jun 22). is_in_window
# returns False outside this range, which auto-hides the CWS sport-nav
# badge. Architecture (route, template, data) stays in place for next
# year's tournament — just update these dates when CWS 2027 schedule
# is announced.
CWS_2026_START = "2026-06-12"
CWS_2026_END   = "2026-06-21"
