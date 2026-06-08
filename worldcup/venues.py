"""
worldcup.venues — 16 stadiums hosting matches in the 2026 FIFA World Cup.

Fields per venue:
    name            canonical stadium name
    city            display city
    country         "US" | "MX" | "CA"
    lat / lon       approximate stadium center
    timezone        IANA timezone string
    roof_type       "open_air" | "retractable" | "fixed_dome"
    nws_unsupported True for Mexico + Canada (use WeatherAPI fallback)
    aliases         alternative names ESPN or FIFA might use
"""

WORLD_CUP_VENUES = {

    # ── UNITED STATES (11) ─────────────────────────────────────
    "Mercedes-Benz Stadium": {
        "city": "Atlanta, GA",
        "country": "US",
        "lat": 33.7553, "lon": -84.4006,
        "timezone": "America/New_York",
        "roof_type": "retractable",
        "aliases": ["Mercedes Benz Stadium"],
    },
    "Gillette Stadium": {
        "city": "Foxborough, MA",
        "country": "US",
        "lat": 42.0909, "lon": -71.2643,
        "timezone": "America/New_York",
        "roof_type": "open_air",
        "aliases": ["Boston Stadium"],
    },
    "AT&T Stadium": {
        "city": "Arlington, TX",
        "country": "US",
        "lat": 32.7479, "lon": -97.0934,
        "timezone": "America/Chicago",
        "roof_type": "retractable",
        "roof_summer_status": "likely_closed",
        "roof_note": "Texas summer heat — roof likely closed",
        "aliases": ["Dallas Stadium", "AT&T"],
    },
    "NRG Stadium": {
        "city": "Houston, TX",
        "country": "US",
        "lat": 29.6847, "lon": -95.4107,
        "timezone": "America/Chicago",
        "roof_type": "retractable",
        "roof_summer_status": "likely_closed",
        "roof_note": "Houston summer heat — roof likely closed for World Cup matches",
        "aliases": ["Houston Stadium"],
    },
    "Arrowhead Stadium": {
        "city": "Kansas City, MO",
        "country": "US",
        "lat": 39.0490, "lon": -94.4839,
        "timezone": "America/Chicago",
        "roof_type": "open_air",
        "aliases": ["Kansas City Stadium", "GEHA Field at Arrowhead Stadium"],
    },
    "SoFi Stadium": {
        "city": "Inglewood, CA",
        "country": "US",
        "lat": 33.9534, "lon": -118.3387,
        "timezone": "America/Los_Angeles",
        "roof_type": "fixed_canopy",
        "roof_note": "Fixed translucent canopy with open sides — wind matters, rain mostly blocked",
        "aliases": ["Los Angeles Stadium"],
    },
    "Hard Rock Stadium": {
        "city": "Miami Gardens, FL",
        "country": "US",
        "lat": 25.9580, "lon": -80.2389,
        "timezone": "America/New_York",
        "roof_type": "open_air",
        "aliases": ["Miami Stadium"],
    },
    "MetLife Stadium": {
        "city": "East Rutherford, NJ",
        "country": "US",
        "lat": 40.8135, "lon": -74.0745,
        "timezone": "America/New_York",
        "roof_type": "open_air",
        "aliases": ["New York New Jersey Stadium", "NY/NJ Stadium"],
    },
    "Lincoln Financial Field": {
        "city": "Philadelphia, PA",
        "country": "US",
        "lat": 39.9008, "lon": -75.1675,
        "timezone": "America/New_York",
        "roof_type": "open_air",
        "aliases": ["Philadelphia Stadium"],
    },
    "Levi's Stadium": {
        "city": "Santa Clara, CA",
        "country": "US",
        "lat": 37.4032, "lon": -121.9698,
        "timezone": "America/Los_Angeles",
        "roof_type": "open_air",
        "aliases": ["San Francisco Bay Area Stadium", "Levis Stadium"],
    },
    "Lumen Field": {
        "city": "Seattle, WA",
        "country": "US",
        "lat": 47.5952, "lon": -122.3316,
        "timezone": "America/Los_Angeles",
        "roof_type": "open_air",
        "aliases": ["Seattle Stadium"],
    },

    # ── CANADA (2) — NWS does not cover Canada ──────────────────
    "BMO Field": {
        "city": "Toronto, ON",
        "country": "CA",
        "lat": 43.6328, "lon": -79.4187,
        "timezone": "America/Toronto",
        "roof_type": "open_air",
        "nws_unsupported": True,
        "aliases": ["Toronto Stadium"],
    },
    "BC Place": {
        "city": "Vancouver, BC",
        "country": "CA",
        "lat": 49.2767, "lon": -123.1118,
        "timezone": "America/Vancouver",
        "roof_type": "retractable",
        "nws_unsupported": True,
        "aliases": ["Vancouver Stadium"],
    },

    # ── MEXICO (3) — NWS does not cover Mexico ──────────────────
    "Estadio Azteca": {
        "city": "Mexico City, MX",
        "country": "MX",
        "lat": 19.3029, "lon": -99.1503,
        "timezone": "America/Mexico_City",
        "roof_type": "open_air",
        "nws_unsupported": True,
        "aliases": ["Mexico City Stadium", "Estadio Banorte"],
    },
    "Estadio Akron": {
        "city": "Zapopan, MX",
        "country": "MX",
        "lat": 20.6816, "lon": -103.4622,
        "timezone": "America/Mexico_City",
        "roof_type": "open_air",
        "nws_unsupported": True,
        "aliases": ["Guadalajara Stadium", "Estadio Chivas"],
    },
    "Estadio BBVA": {
        "city": "Guadalupe, MX",
        "country": "MX",
        "lat": 25.6692, "lon": -100.2447,
        "timezone": "America/Monterrey",
        "roof_type": "open_air",
        "nws_unsupported": True,
        "aliases": ["Monterrey Stadium", "Estadio BBVA Bancomer"],
    },
}


# Reverse lookup (lowercase): venue name + aliases → canonical name
VENUE_NAME_TO_CANONICAL = {}
for canon, meta in WORLD_CUP_VENUES.items():
    VENUE_NAME_TO_CANONICAL[canon.lower()] = canon
    for alias in meta.get("aliases", []):
        VENUE_NAME_TO_CANONICAL[alias.lower()] = canon


def lookup_venue(name: str):
    """Resolve any venue name (incl. aliases) to its metadata dict."""
    if not name:
        return None
    canonical = VENUE_NAME_TO_CANONICAL.get(name.lower())
    if not canonical:
        return None
    return {**WORLD_CUP_VENUES[canonical], "_canonical_name": canonical}
