"""cws.venue — the one venue."""

CHARLES_SCHWAB_FIELD = {
    "name":              "Charles Schwab Field Omaha",
    "city":              "Omaha, NE",
    "country":           "US",
    "lat":               41.2570,
    "lon":               -95.9251,
    "timezone":          "America/Chicago",
    "roof_type":         "open_air",
    "cf_bearing_degrees": 30,   # CF is roughly NNE
    "aliases":           ["Charles Schwab Field", "TD Ameritrade Park", "Omaha"],
}

# Calendar window: hard-coded for 2026
CWS_2026_START = "2026-06-12"  # one day buffer before opening
CWS_2026_END   = "2026-06-24"
