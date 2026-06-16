"""
golf.courses — PGA Tour course metadata.

Phase 1 covers the highest-frequency venues. Courses we don't yet have
mapped will surface a "Course pending mapping" message rather than break
the page. Add new courses as tournaments approach.
"""

PGA_COURSES = {

    # ── MAJORS ────────────────────────────────────────────────────
    "Augusta National Golf Club": {
        "city": "Augusta, GA", "country": "US",
        "lat": 33.5031, "lon": -82.0226,
        "timezone": "America/New_York",
    },
    "Pinehurst Resort & Country Club": {
        "city": "Pinehurst, NC", "country": "US",
        "lat": 35.1948, "lon": -79.4664,
        "timezone": "America/New_York",
    },
    "Oakmont Country Club": {
        "city": "Oakmont, PA", "country": "US",
        "lat": 40.5246, "lon": -79.8245,
        "timezone": "America/New_York",
    },
    "Bethpage Black Course": {
        "city": "Farmingdale, NY", "country": "US",
        "lat": 40.7374, "lon": -73.4582,
        "timezone": "America/New_York",
    },
    "Quail Hollow Club": {
        "city": "Charlotte, NC", "country": "US",
        "lat": 35.1559, "lon": -80.8285,
        "timezone": "America/New_York",
    },
    "Royal Liverpool Golf Club": {
        "city": "Hoylake, England", "country": "UK",
        "lat": 53.3848, "lon": -3.1814,
        "timezone": "Europe/London",
        "nws_unsupported": True,
    },
    "Royal Troon Golf Club": {
        "city": "Troon, Scotland", "country": "UK",
        "lat": 55.5379, "lon": -4.6477,
        "timezone": "Europe/London",
        "nws_unsupported": True,
    },
    "Shinnecock Hills Golf Club": {
        "city": "Southampton, NY", "country": "US",
        "lat": 40.8944, "lon": -72.4528,
        "timezone": "America/New_York",
        "aliases": ["Shinnecock Hills", "Shinnecock"],
    },
    "Royal Birkdale Golf Club": {
        "city": "Southport, England", "country": "UK",
        "lat": 53.6286, "lon": -3.0303,
        "timezone": "Europe/London",
        "nws_unsupported": True,
        "aliases": ["Royal Birkdale", "Birkdale"],
    },

    # ── REGULAR PGA TOUR STAPLES ─────────────────────────────────
    "TPC Sawgrass": {
        "city": "Ponte Vedra Beach, FL", "country": "US",
        "lat": 30.1981, "lon": -81.3947,
        "timezone": "America/New_York",
    },
    "Pebble Beach Golf Links": {
        "city": "Pebble Beach, CA", "country": "US",
        "lat": 36.5681, "lon": -121.9494,
        "timezone": "America/Los_Angeles",
    },
    "Riviera Country Club": {
        "city": "Pacific Palisades, CA", "country": "US",
        "lat": 34.0560, "lon": -118.5081,
        "timezone": "America/Los_Angeles",
    },
    "Torrey Pines Golf Course": {
        "city": "La Jolla, CA", "country": "US",
        "lat": 32.8961, "lon": -117.2530,
        "timezone": "America/Los_Angeles",
    },
    "TPC Scottsdale": {
        "city": "Scottsdale, AZ", "country": "US",
        "lat": 33.6364, "lon": -111.9111,
        "timezone": "America/Phoenix",
    },
    "Bay Hill Club and Lodge": {
        "city": "Orlando, FL", "country": "US",
        "lat": 28.4555, "lon": -81.5128,
        "timezone": "America/New_York",
    },
    "PGA National Resort": {
        "city": "Palm Beach Gardens, FL", "country": "US",
        "lat": 26.8345, "lon": -80.1469,
        "timezone": "America/New_York",
    },
    "Innisbrook Resort (Copperhead Course)": {
        "city": "Palm Harbor, FL", "country": "US",
        "lat": 28.1303, "lon": -82.7283,
        "timezone": "America/New_York",
    },
    "Memorial Park Golf Course": {
        "city": "Houston, TX", "country": "US",
        "lat": 29.7748, "lon": -95.4233,
        "timezone": "America/Chicago",
    },
    "Colonial Country Club": {
        "city": "Fort Worth, TX", "country": "US",
        "lat": 32.7100, "lon": -97.3720,
        "timezone": "America/Chicago",
    },
    "Muirfield Village Golf Club": {
        "city": "Dublin, OH", "country": "US",
        "lat": 40.1467, "lon": -83.1500,
        "timezone": "America/New_York",
    },
    "TPC River Highlands": {
        "city": "Cromwell, CT", "country": "US",
        "lat": 41.5786, "lon": -72.6792,
        "timezone": "America/New_York",
    },
    "TPC Twin Cities": {
        "city": "Blaine, MN", "country": "US",
        "lat": 45.1719, "lon": -93.2208,
        "timezone": "America/Chicago",
    },
    "Detroit Golf Club": {
        "city": "Detroit, MI", "country": "US",
        "lat": 42.4253, "lon": -83.1147,
        "timezone": "America/Detroit",
    },
    "Detroit Country Club (Country Club of Detroit)": {
        "city": "Grosse Pointe Farms, MI", "country": "US",
        "lat": 42.4108, "lon": -82.9089,
        "timezone": "America/Detroit",
    },
    "TPC Deere Run": {
        "city": "Silvis, IL", "country": "US",
        "lat": 41.5247, "lon": -90.4011,
        "timezone": "America/Chicago",
    },
    "Renaissance Club": {
        "city": "North Berwick, Scotland", "country": "UK",
        "lat": 56.0489, "lon": -2.7611,
        "timezone": "Europe/London",
        "nws_unsupported": True,
        "aliases": ["The Renaissance Club"],
    },
    "TPC Southwind": {
        "city": "Memphis, TN", "country": "US",
        "lat": 35.0567, "lon": -89.8497,
        "timezone": "America/Chicago",
    },
    "Olympia Fields Country Club": {
        "city": "Olympia Fields, IL", "country": "US",
        "lat": 41.5031, "lon": -87.6878,
        "timezone": "America/Chicago",
    },
    "East Lake Golf Club": {
        "city": "Atlanta, GA", "country": "US",
        "lat": 33.7387, "lon": -84.3253,
        "timezone": "America/New_York",
    },
    "Castle Pines Golf Club": {
        "city": "Castle Rock, CO", "country": "US",
        "lat": 39.4044, "lon": -104.8722,
        "timezone": "America/Denver",
    },
    "Sedgefield Country Club": {
        "city": "Greensboro, NC", "country": "US",
        "lat": 36.0467, "lon": -79.8369,
        "timezone": "America/New_York",
        "aliases": ["Sedgefield"],
    },
    "Bellerive Country Club": {
        "city": "Town and Country, MO", "country": "US",
        "lat": 38.6447, "lon": -90.4347,
        "timezone": "America/Chicago",
        "aliases": ["Bellerive"],
    },
    "The Cliffs at Walnut Cove": {
        "city": "Asheville, NC", "country": "US",
        "lat": 35.4456, "lon": -82.5631,
        "timezone": "America/New_York",
        "aliases": ["Walnut Cove", "Cliffs at Walnut Cove"],
    },
    "Medinah CC (No. 3)": {
        "city": "Medinah, IL", "country": "US",
        "lat": 41.9789, "lon": -88.0420,
        "timezone": "America/Chicago",
        "aliases": ["Medinah Country Club", "Medinah CC", "Medinah Country Club (No. 3)"],
    },

    # ── FALL/SILLY SEASON ────────────────────────────────────────
    "Sea Island Resort (Seaside Course)": {
        "city": "St. Simons Island, GA", "country": "US",
        "lat": 31.1769, "lon": -81.3939,
        "timezone": "America/New_York",
        "aliases": ["Sea Island Golf Club (Seaside Course)", "Sea Island"],
    },
    "Country Club of Jackson": {
        "city": "Jackson, MS", "country": "US",
        "lat": 32.3622, "lon": -90.1614,
        "timezone": "America/Chicago",
    },
    "El Camaleón Golf Club": {
        "city": "Playa del Carmen, Mexico", "country": "MX",
        "lat": 20.6486, "lon": -87.1131,
        "timezone": "America/Cancun",
        "nws_unsupported": True,
    },
    "Plantation Course at Kapalua": {
        "city": "Lahaina, HI", "country": "US",
        "lat": 21.0027, "lon": -156.6614,
        "timezone": "Pacific/Honolulu",
    },
    "Waialae Country Club": {
        "city": "Honolulu, HI", "country": "US",
        "lat": 21.2683, "lon": -157.7689,
        "timezone": "Pacific/Honolulu",
    },
    "Black Desert Resort": {
        "city": "Ivins, UT", "country": "US",
        "lat": 37.1561, "lon": -113.6917,
        "timezone": "America/Denver",
        "aliases": ["Black Desert"],
    },
    "Omni Barton Creek Resort": {
        "city": "Austin, TX", "country": "US",
        "lat": 30.2811, "lon": -97.8489,
        "timezone": "America/Chicago",
        "aliases": ["Barton Creek", "Omni Barton Creek", "Omni Barton Creek Resort & Spa"],
    },
    "Tiburon Golf Club": {
        "city": "Naples, FL", "country": "US",
        "lat": 26.2569, "lon": -81.7464,
        "timezone": "America/New_York",
        "aliases": ["Tiburón Golf Club", "Tiburon"],
    },

    # ── INTERNATIONAL (NWS unsupported, weather via WeatherAPI) ──
    "Yokohama Country Club": {
        "city": "Yokohama", "country": "JP",
        "lat": 35.5066, "lon": 139.5847,
        "timezone": "Asia/Tokyo",
        "nws_unsupported": True,
    },
    "Port Royal Golf Course": {
        "city": "Southampton, Bermuda", "country": "BM",
        "lat": 32.2553, "lon": -64.8869,
        "timezone": "Atlantic/Bermuda",
        "nws_unsupported": True,
    },
    "Vidanta Vallarta": {
        "city": "Nuevo Vallarta", "country": "MX",
        "lat": 20.7000, "lon": -105.2667,
        "timezone": "America/Mexico_City",
        "nws_unsupported": True,
    },
    "El Cardonal at Diamante": {
        "city": "Los Cabos", "country": "MX",
        "lat": 23.0086, "lon": -109.9408,
        "timezone": "America/Mazatlan",
        "nws_unsupported": True,
        "aliases": ["El Cardonal", "Diamante"],
    },
    "Albany GC": {
        "city": "Nassau", "country": "BS",
        "lat": 24.9911, "lon": -77.5664,
        "timezone": "America/Nassau",
        "nws_unsupported": True,
        "aliases": ["Albany"],
    },

    # ── CANADA / INTERNATIONAL ───────────────────────────────────
    "TPC Toronto at Osprey Valley": {
        "city": "Caledon, ON", "country": "CA",
        "lat": 43.8517, "lon": -80.0344,  # Heathlands Course area
        "timezone": "America/Toronto",
        "nws_unsupported": True,  # NWS does not cover Canada
        "aliases": ["TPC Toronto", "Osprey Valley", "TPC Toronto Osprey Valley"],
    },
}


# Build lowercase lookup for fuzzy matching against API venue names.
# Includes canonical names AND all listed aliases per course.
COURSE_NAME_TO_CANONICAL = {}
for canon, meta in PGA_COURSES.items():
    COURSE_NAME_TO_CANONICAL[canon.lower()] = canon
    for alias in meta.get("aliases", []):
        COURSE_NAME_TO_CANONICAL[alias.lower()] = canon


def lookup_course(name: str):
    """Resolve a course name to its metadata. Tries exact then prefix match."""
    if not name:
        return None
    n = name.lower().strip()
    if n in COURSE_NAME_TO_CANONICAL:
        canon = COURSE_NAME_TO_CANONICAL[n]
        return {**PGA_COURSES[canon], "_canonical_name": canon}
    # Fuzzy: prefix match (helps when API uses "TPC Sawgrass" vs "TPC Sawgrass - The Players Stadium Course")
    for canon_lower, canon in COURSE_NAME_TO_CANONICAL.items():
        if n.startswith(canon_lower) or canon_lower.startswith(n):
            return {**PGA_COURSES[canon], "_canonical_name": canon}
    return None
