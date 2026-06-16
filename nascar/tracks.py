"""
nascar.tracks — NASCAR Cup Series venues.

Track types affect how weather matters:
  - oval: wind speed > direction (single grandstand, sustained wind)
  - superspeedway: same as oval but extreme speeds amplify wind impact
  - road_course: wind direction matters more (multiple corner types)
  - street_course: urban effects, building deflection

Lat/lon are start-finish line / pit road area.
"""

NASCAR_TRACKS = {
    # ── SUPERSPEEDWAYS ────────────────────────────────────────
    "Daytona International Speedway": {
        "city": "Daytona Beach, FL", "country": "US",
        "lat": 29.1856, "lon": -81.0698,
        "timezone": "America/New_York",
        "track_type": "superspeedway", "length_miles": 2.5,
        "aliases": ["Daytona"],
    },
    "Talladega Superspeedway": {
        "city": "Lincoln, AL", "country": "US",
        "lat": 33.5650, "lon": -86.0656,
        "timezone": "America/Chicago",
        "track_type": "superspeedway", "length_miles": 2.66,
        "aliases": ["Talladega"],
    },

    # ── INTERMEDIATE OVALS ───────────────────────────────────
    "Atlanta Motor Speedway": {
        "city": "Hampton, GA", "country": "US",
        "lat": 33.3850, "lon": -84.3170,
        "timezone": "America/New_York",
        "track_type": "intermediate_oval", "length_miles": 1.54,
        "aliases": ["Atlanta"],
    },
    "Las Vegas Motor Speedway": {
        "city": "Las Vegas, NV", "country": "US",
        "lat": 36.2722, "lon": -115.0078,
        "timezone": "America/Los_Angeles",
        "track_type": "intermediate_oval", "length_miles": 1.5,
        "aliases": ["Vegas", "Las Vegas"],
    },
    "Texas Motor Speedway": {
        "city": "Fort Worth, TX", "country": "US",
        "lat": 33.0381, "lon": -97.2811,
        "timezone": "America/Chicago",
        "track_type": "intermediate_oval", "length_miles": 1.5,
        "aliases": ["Texas"],
    },
    "Charlotte Motor Speedway": {
        "city": "Concord, NC", "country": "US",
        "lat": 35.3500, "lon": -80.6831,
        "timezone": "America/New_York",
        "track_type": "intermediate_oval", "length_miles": 1.5,
        "aliases": ["Charlotte"],
    },
    "Kansas Speedway": {
        "city": "Kansas City, KS", "country": "US",
        "lat": 39.1156, "lon": -94.8331,
        "timezone": "America/Chicago",
        "track_type": "intermediate_oval", "length_miles": 1.5,
    },
    "Michigan International Speedway": {
        "city": "Brooklyn, MI", "country": "US",
        "lat": 42.0708, "lon": -84.2422,
        "timezone": "America/Detroit",
        "track_type": "intermediate_oval", "length_miles": 2.0,
        "aliases": ["Michigan"],
    },
    "Homestead-Miami Speedway": {
        "city": "Homestead, FL", "country": "US",
        "lat": 25.4525, "lon": -80.4097,
        "timezone": "America/New_York",
        "track_type": "intermediate_oval", "length_miles": 1.5,
        "aliases": ["Homestead"],
    },
    "Pocono Raceway": {
        "city": "Long Pond, PA", "country": "US",
        "lat": 41.0556, "lon": -75.5111,
        "timezone": "America/New_York",
        "track_type": "intermediate_oval", "length_miles": 2.5,
        "aliases": ["Pocono"],
    },

    # ── SHORT TRACKS ─────────────────────────────────────────
    "Bristol Motor Speedway": {
        "city": "Bristol, TN", "country": "US",
        "lat": 36.5158, "lon": -82.2569,
        "timezone": "America/New_York",
        "track_type": "short_oval", "length_miles": 0.533,
        "aliases": ["Bristol"],
    },
    "Martinsville Speedway": {
        "city": "Ridgeway, VA", "country": "US",
        "lat": 36.6342, "lon": -79.8506,
        "timezone": "America/New_York",
        "track_type": "short_oval", "length_miles": 0.526,
        "aliases": ["Martinsville"],
    },
    "Richmond Raceway": {
        "city": "Richmond, VA", "country": "US",
        "lat": 37.5933, "lon": -77.4203,
        "timezone": "America/New_York",
        "track_type": "short_oval", "length_miles": 0.75,
        "aliases": ["Richmond"],
    },
    "Phoenix Raceway": {
        "city": "Avondale, AZ", "country": "US",
        "lat": 33.3744, "lon": -112.3074,
        "timezone": "America/Phoenix",
        "track_type": "short_oval", "length_miles": 1.0,
        "aliases": ["Phoenix"],
    },
    "Dover Motor Speedway": {
        "city": "Dover, DE", "country": "US",
        "lat": 39.1893, "lon": -75.5300,
        "timezone": "America/New_York",
        "track_type": "short_oval", "length_miles": 1.0,
        "aliases": ["Dover"],
    },
    "New Hampshire Motor Speedway": {
        "city": "Loudon, NH", "country": "US",
        "lat": 43.3625, "lon": -71.4639,
        "timezone": "America/New_York",
        "track_type": "short_oval", "length_miles": 1.058,
        "aliases": ["New Hampshire", "Loudon"],
    },
    "Iowa Speedway": {
        "city": "Newton, IA", "country": "US",
        "lat": 41.5894, "lon": -93.1339,
        "timezone": "America/Chicago",
        "track_type": "short_oval", "length_miles": 0.875,
    },
    "Nashville Superspeedway": {
        "city": "Lebanon, TN", "country": "US",
        "lat": 36.1306, "lon": -86.4119,
        "timezone": "America/Chicago",
        "track_type": "intermediate_oval", "length_miles": 1.333,
        "aliases": ["Nashville"],
    },

    # ── ROAD COURSES ─────────────────────────────────────────
    "Sonoma Raceway": {
        "city": "Sonoma, CA", "country": "US",
        "lat": 38.1611, "lon": -122.4583,
        "timezone": "America/Los_Angeles",
        "track_type": "road_course", "length_miles": 1.99,
        "aliases": ["Sonoma"],
    },
    "Watkins Glen International": {
        "city": "Watkins Glen, NY", "country": "US",
        "lat": 42.3417, "lon": -76.9269,
        "timezone": "America/New_York",
        "track_type": "road_course", "length_miles": 2.45,
        "aliases": ["The Glen", "Watkins Glen"],
    },
    "Circuit of the Americas": {
        "city": "Austin, TX", "country": "US",
        "lat": 30.1328, "lon": -97.6411,
        "timezone": "America/Chicago",
        "track_type": "road_course", "length_miles": 3.426,
        "aliases": ["COTA"],
    },
    "Chicago Street Course": {
        "city": "Chicago, IL", "country": "US",
        "lat": 41.8826, "lon": -87.6226,
        "timezone": "America/Chicago",
        "track_type": "street_course", "length_miles": 2.2,
        "aliases": ["Chicago"],
    },
    # New for 2026: NASCAR Cup race at Naval Air Station North Island in
    # Coronado, San Diego. Temporary street circuit on the Navy base.
    # Lat/lon approximate; layout/length subject to final confirmation.
    "Coronado Street Course": {
        "city": "Coronado, CA", "country": "US",
        "lat": 32.6900, "lon": -117.2150,
        "timezone": "America/Los_Angeles",
        "track_type": "street_course", "length_miles": 2.0,
        "aliases": ["Coronado", "San Diego", "Naval Base Coronado"],
    },

    # ── OTHER OVALS ──────────────────────────────────────────
    "Indianapolis Motor Speedway": {
        "city": "Speedway, IN", "country": "US",
        "lat": 39.7950, "lon": -86.2347,
        "timezone": "America/Indiana/Indianapolis",
        "track_type": "superspeedway", "length_miles": 2.5,
        "aliases": ["Indy", "Brickyard"],
    },
    "Darlington Raceway": {
        "city": "Darlington, SC", "country": "US",
        "lat": 34.4972, "lon": -79.9214,
        "timezone": "America/New_York",
        "track_type": "intermediate_oval", "length_miles": 1.366,
        "aliases": ["Darlington"],
    },
    "World Wide Technology Raceway": {
        "city": "Madison, IL", "country": "US",
        "lat": 38.6519, "lon": -90.1392,
        "timezone": "America/Chicago",
        "track_type": "intermediate_oval", "length_miles": 1.25,
        "aliases": ["Gateway", "WWT Raceway", "St. Louis"],
    },
    "Auto Club Speedway": {
        "city": "Fontana, CA", "country": "US",
        "lat": 34.0883, "lon": -117.5000,
        "timezone": "America/Los_Angeles",
        "track_type": "intermediate_oval", "length_miles": 2.0,
        "aliases": ["Fontana"],
    },
}


TRACK_NAME_TO_CANONICAL = {}
for canon, meta in NASCAR_TRACKS.items():
    TRACK_NAME_TO_CANONICAL[canon.lower()] = canon
    for alias in meta.get("aliases", []):
        TRACK_NAME_TO_CANONICAL[alias.lower()] = canon


def lookup_track(name: str):
    if not name:
        return None
    n = name.lower().strip()
    if n in TRACK_NAME_TO_CANONICAL:
        canon = TRACK_NAME_TO_CANONICAL[n]
        return {**NASCAR_TRACKS[canon], "_canonical_name": canon}
    for canon_lower, canon in TRACK_NAME_TO_CANONICAL.items():
        if n.startswith(canon_lower) or canon_lower.startswith(n):
            return {**NASCAR_TRACKS[canon], "_canonical_name": canon}
    return None
