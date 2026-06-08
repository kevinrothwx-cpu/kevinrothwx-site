"""
OVERcast Park Metadata
======================
Static lookup table for every MLB park in the dataset.

cf_bearing_degrees:
    Compass bearing (0–359) from home plate to center field.
    0 = CF is due north of home plate
    90 = CF is due east of home plate
    etc.

    Used to classify wind as OUT / IN / CROSS relative to the field.

roof_type:
    "open_air"     — no roof, always included in default slate
    "retractable"  — roof may be open or closed, excluded by default
    "fixed_dome"   — always climate-controlled, always excluded

lat / lon:
    Approximate coordinates of the ballpark (home plate area).
    Used to query the NWS forecast API.
    NOTE: Rogers Centre (Toronto) is outside NWS coverage — NWS only
    covers the contiguous US, Alaska, and Hawaii.

timezone:
    IANA timezone string for the park's local time.
    Used to format game start times in the slate output.

park_alias:
    List of alternate names this park has gone by in the dataset,
    so we can normalize old names → canonical name.
"""

PARK_METADATA = {

    # ── AMERICAN LEAGUE EAST ───────────────────────────────────────────
    "Fenway Park": {
        "mlbam_ids": [3],
        "city": "Boston, MA",
        "team": "Boston Red Sox",
        "roof_type": "open_air",
        "cf_bearing_degrees": 45,    # CF is NE — verified by Kevin Mar 2026
        "lat": 42.3467, "lon": -71.0972,
        "timezone": "America/New_York",
        "asos_station": "KBOS",      # Logan Intl, ~2 mi NE — assumed
        "aliases": [],
    },
    "Yankee Stadium": {
        "mlbam_ids": [3313],
        "city": "Bronx, NY",
        "team": "New York Yankees",
        "roof_type": "open_air",
        "cf_bearing_degrees": 80,    # CF is E — verified by Kevin Mar 2026
        "lat": 40.8296, "lon": -73.9262,
        "timezone": "America/New_York",
        "asos_station": "KLGA",      # LaGuardia, ~7 mi SE — verified Mar 2026
        "aliases": [],
    },
    "Oriole Park at Camden Yards": {
        "mlbam_ids": [2],
        "city": "Baltimore, MD",
        "team": "Baltimore Orioles",
        "roof_type": "open_air",
        "cf_bearing_degrees": 30,    # CF is NNE — verified by Kevin Mar 2026
        "lat": 39.2839, "lon": -76.6218,
        "timezone": "America/New_York",
        "asos_station": "KBWI",      # BWI, ~6 mi S — assumed
        "aliases": [],
    },
    "Rogers Centre": {
        "mlbam_ids": [14],
        "city": "Toronto, ON",
        "team": "Toronto Blue Jays",
        "roof_type": "retractable",
        "cf_bearing_degrees": 50,
        "lat": 43.6414, "lon": -79.3894,
        "timezone": "America/Toronto",
        "aliases": [],
        # NOTE: NWS does not cover Canada — skip weather lookup for this park
        "nws_unsupported": True,
    },
    "Tropicana Field": {
        "mlbam_ids": [12],
        "city": "St. Petersburg, FL",
        "team": "Tampa Bay Rays",
        "roof_type": "fixed_dome",
        "cf_bearing_degrees": 40,
        "lat": 27.7683, "lon": -82.6534,
        "timezone": "America/New_York",
        "aliases": [],
    },

    # ── AMERICAN LEAGUE CENTRAL ────────────────────────────────────────
    "Guaranteed Rate Field": {
        "mlbam_ids": [4],
        "city": "Chicago, IL",
        "team": "Chicago White Sox",
        "roof_type": "open_air",
        "cf_bearing_degrees": 130,   # CF is SE — verified by Kevin Mar 2026
        "lat": 41.8300, "lon": -87.6339,
        "timezone": "America/Chicago",
        "asos_station": "KMDW",      # Midway, ~3 mi SW — assumed (same source as Wrigley)
        "aliases": ["U.S. Cellular Field", "Rate Field"],
    },
    "Progressive Field": {
        "mlbam_ids": [5],
        "city": "Cleveland, OH",
        "team": "Cleveland Guardians",
        "roof_type": "open_air",
        "cf_bearing_degrees": 0,     # CF is N — verified by Kevin Mar 2026
        "lat": 41.4962, "lon": -81.6852,
        "timezone": "America/New_York",
        "asos_station": "KCLE",      # Cleveland Hopkins, ~12 mi SW — assumed
        "aliases": [],
    },
    "Comerica Park": {
        "mlbam_ids": [2394],
        "city": "Detroit, MI",
        "team": "Detroit Tigers",
        "roof_type": "open_air",
        "cf_bearing_degrees": 165,   # CF is SSE — verified by Kevin Mar 2026
        "lat": 42.3390, "lon": -83.0485,
        "timezone": "America/Detroit",
        "asos_station": "KDET",      # Coleman A. Young Municipal, ~4 mi NE — assumed
        "aliases": [],
    },
    "Kauffman Stadium": {
        "mlbam_ids": [7],
        "city": "Kansas City, MO",
        "team": "Kansas City Royals",
        "roof_type": "open_air",
        "cf_bearing_degrees": 45,    # CF is NE
        "lat": 39.0517, "lon": -94.4803,
        "timezone": "America/Chicago",
        "asos_station": "KMKC",      # Charles B. Wheeler Downtown, ~5 mi NW — verified Mar 2026
        "aliases": [],
    },
    "Target Field": {
        "mlbam_ids": [3312],
        "city": "Minneapolis, MN",
        "team": "Minnesota Twins",
        "roof_type": "open_air",
        "cf_bearing_degrees": 90,    # CF is E — verified by Kevin Mar 2026
        "lat": 44.9817, "lon": -93.2781,
        "timezone": "America/Chicago",
        "asos_station": "KMSP",      # Minneapolis-St. Paul Intl, ~11 mi SW — assumed
        "aliases": [],
    },

    # ── AMERICAN LEAGUE WEST ───────────────────────────────────────────
    "Minute Maid Park": {
        "mlbam_ids": [239],
        "city": "Houston, TX",
        "team": "Houston Astros",
        "roof_type": "retractable",
        "cf_bearing_degrees": 45,
        "lat": 29.7573, "lon": -95.3555,
        "timezone": "America/Chicago",
        "aliases": ["Daikin Park"],
    },
    "Angel Stadium": {
        "mlbam_ids": [1],
        "city": "Anaheim, CA",
        "team": "Los Angeles Angels",
        "roof_type": "open_air",
        "cf_bearing_degrees": 40,    # CF is NNE/NE — verified by Kevin Mar 2026 (40°)
        "lat": 33.8003, "lon": -117.8827,
        "timezone": "America/Los_Angeles",
        "asos_station": "KSNA",      # John Wayne/Orange County, ~4 mi S — assumed
        "aliases": ["Angel Stadium of Anaheim"],
    },
    "Oakland Coliseum": {
        "mlbam_ids": [10],
        "city": "Oakland, CA",
        "team": "Oakland Athletics",
        "roof_type": "open_air",
        "cf_bearing_degrees": 325,   # CF is NW
        "lat": 37.7516, "lon": -122.2005,
        "timezone": "America/Los_Angeles",
        "aliases": ["O.co Coliseum"],
        "active": False,  # A's moved to Sutter Health Park (Sacramento) for 2025 season
    },
    "T-Mobile Park": {
        "mlbam_ids": [680],
        "city": "Seattle, WA",
        "team": "Seattle Mariners",
        "roof_type": "open_air",     # roof has open sides even when closed — wind/temp matter (Kevin confirmed Mar 2026)
        "cf_bearing_degrees": 45,    # CF is NE — verified by Kevin Mar 2026
        "lat": 47.5914, "lon": -122.3325,
        "timezone": "America/Los_Angeles",
        "asos_station": "KBFI",      # Boeing Field, ~2 mi S — verified Mar 2026 (KSEA/KRNT both wrong)
        "aliases": ["Safeco Field"],
    },
    "Globe Life Field": {
        "mlbam_ids": [5325],
        "city": "Arlington, TX",
        "team": "Texas Rangers",
        "roof_type": "retractable",
        "cf_bearing_degrees": 50,
        "lat": 32.7473, "lon": -97.0832,
        "timezone": "America/Chicago",
        "aliases": [],
    },
    "Globe Life Park in Arlington": {
        "mlbam_ids": [13],
        "city": "Arlington, TX",
        "team": "Texas Rangers (old park)",
        "roof_type": "open_air",
        "cf_bearing_degrees": 50,
        "lat": 32.7512, "lon": -97.0832,
        "timezone": "America/Chicago",
        "aliases": [],
        "active": False,  # Rangers moved to Globe Life Field (retractable) for 2020 season
    },

    # ── NATIONAL LEAGUE EAST ──────────────────────────────────────────
    "Truist Park": {
        "mlbam_ids": [4705],
        "city": "Cumberland, GA",
        "team": "Atlanta Braves",
        "roof_type": "open_air",
        "cf_bearing_degrees": 160,   # CF is SSE — verified by Kevin Mar 2026
        "lat": 33.8908, "lon": -84.4678,
        "timezone": "America/New_York",
        "asos_station": "KATL",      # Hartsfield-Jackson, ~13 mi SE — verified Mar 2026 (PDK/FTY/RYY all wrong)
        "aliases": ["SunTrust Park"],
    },
    "Wrigley Field": {
        "mlbam_ids": [17],
        "city": "Chicago, IL",
        "team": "Chicago Cubs",
        "roof_type": "open_air",
        "cf_bearing_degrees": 40,    # CF is NNE/NE — verified by Kevin Mar 2026 (40°)
        "lat": 41.9484, "lon": -87.6553,
        "timezone": "America/Chicago",
        "asos_station": "KMDW",      # Midway, ~13 mi SW — verified Mar 2026 (KORD wrong, lake effect)
        "aliases": [],
    },
    "loanDepot park": {
        "mlbam_ids": [4169],
        "city": "Miami, FL",
        "team": "Miami Marlins",
        "roof_type": "retractable",
        "cf_bearing_degrees": 25,
        "lat": 25.7781, "lon": -80.2197,
        "timezone": "America/New_York",
        "aliases": ["Marlins Park"],
    },
    "Citi Field": {
        "mlbam_ids": [3289],
        "city": "Queens, NY",
        "team": "New York Mets",
        "roof_type": "open_air",
        "cf_bearing_degrees": 30,    # CF is NNE — verified by Kevin Mar 2026
        "lat": 40.7571, "lon": -73.8458,
        "timezone": "America/New_York",
        "asos_station": "KLGA",      # LaGuardia, ~2.5 mi NE — verified Mar 2026
        "aliases": [],
    },
    "Citizens Bank Park": {
        "mlbam_ids": [2681],
        "city": "Philadelphia, PA",
        "team": "Philadelphia Phillies",
        "roof_type": "open_air",
        "cf_bearing_degrees": 10,    # CF is N — verified by Kevin Mar 2026
        "lat": 39.9061, "lon": -75.1665,
        "timezone": "America/New_York",
        "asos_station": "KPHL",      # Philadelphia Intl, ~4 mi SW — assumed
        "aliases": [],
    },
    "Nationals Park": {
        "mlbam_ids": [3309],
        "city": "Washington, DC",
        "team": "Washington Nationals",
        "roof_type": "open_air",
        "cf_bearing_degrees": 30,    # CF is NNE — verified by Kevin Mar 2026
        "lat": 38.8730, "lon": -77.0074,
        "timezone": "America/New_York",
        "asos_station": "KDCA",      # Reagan National, ~3 mi N — assumed
        "aliases": [],
    },

    # ── NATIONAL LEAGUE CENTRAL ────────────────────────────────────────
    "Great American Ball Park": {
        "mlbam_ids": [2602],
        "city": "Cincinnati, OH",
        "team": "Cincinnati Reds",
        "roof_type": "open_air",
        "cf_bearing_degrees": 125,   # CF is SE — verified by Kevin Mar 2026
        "lat": 39.0979, "lon": -84.5065,
        "timezone": "America/New_York",
        "asos_station": "KLUK",      # Cincinnati Municipal Lunken, ~5 mi E — assumed
        "aliases": [],
    },
    "Coors Field": {
        "mlbam_ids": [19],
        "city": "Denver, CO",
        "team": "Colorado Rockies",
        "roof_type": "open_air",
        "cf_bearing_degrees": 0,     # CF is N — verified by Kevin Mar 2026
        "lat": 39.7559, "lon": -104.9942,
        "timezone": "America/Denver",
        "asos_station": "KDEN",      # Denver Intl, ~23 mi NE — verified Mar 2026 (APA/BJC both wrong)
        "aliases": [],
    },
    "American Family Field": {
        "mlbam_ids": [32],
        "city": "Milwaukee, WI",
        "team": "Milwaukee Brewers",
        "roof_type": "retractable",
        "cf_bearing_degrees": 135,   # CF is SE — verified by Kevin May 2026
        "lat": 43.0280, "lon": -87.9712,
        "timezone": "America/Chicago",
        "asos_station": "KMKE",      # Milwaukee Mitchell Intl, ~7 mi SE — assumed
        "aliases": ["Miller Park"],
    },
    "PNC Park": {
        "mlbam_ids": [31],
        "city": "Pittsburgh, PA",
        "team": "Pittsburgh Pirates",
        "roof_type": "open_air",
        "cf_bearing_degrees": 125,   # CF is SE — verified by Kevin Mar 2026
        "lat": 40.4469, "lon": -80.0057,
        "timezone": "America/New_York",
        "asos_station": "KAGC",      # Allegheny County, ~8 mi SE — assumed
        "aliases": [],
    },
    "Busch Stadium": {
        "mlbam_ids": [2889],
        "city": "St. Louis, MO",
        "team": "St. Louis Cardinals",
        "roof_type": "open_air",
        "cf_bearing_degrees": 75,    # CF is ENE — verified by Kevin Mar 2026
        "lat": 38.6226, "lon": -90.1928,
        "timezone": "America/Chicago",
        "asos_station": "KSTL",      # Lambert-St. Louis Intl, ~14 mi NW — assumed
        "aliases": [],
    },

    # ── NATIONAL LEAGUE WEST ──────────────────────────────────────────
    "Chase Field": {
        "mlbam_ids": [15],
        "city": "Phoenix, AZ",
        "team": "Arizona Diamondbacks",
        "roof_type": "retractable",
        "cf_bearing_degrees": 50,
        "lat": 33.4453, "lon": -112.0667,
        "timezone": "America/Phoenix",  # Arizona does not observe DST
        "aliases": [],
    },
    "Dodger Stadium": {
        "mlbam_ids": [22],
        "city": "Los Angeles, CA",
        "team": "Los Angeles Dodgers",
        "roof_type": "open_air",
        "cf_bearing_degrees": 35,    # CF is NNE — verified by Kevin Mar 2026
        "lat": 34.0739, "lon": -118.2400,
        "timezone": "America/Los_Angeles",
        "asos_station": "KBUR",      # Burbank Bob Hope, ~5 mi N — assumed
        "aliases": [
            # Uniqlo naming rights variants (2026+) — MLB API may return any of these
            "Uniqlo Field at Dodger Stadium",
            "UNIQLO FIELD AT DODGER STADIUM",
            "uniqlo field at dodger stadium",
            "Uniqlo Field",
            "UNIQLO FIELD",
            "Dodger Stadium presented by Uniqlo",
            "Dodger Stadium - Uniqlo",
            "Dodger Stadium (Uniqlo Field)",
        ],
    },
    "Petco Park": {
        "mlbam_ids": [2680],
        "city": "San Diego, CA",
        "team": "San Diego Padres",
        "roof_type": "open_air",
        "cf_bearing_degrees": 0,     # CF is N — verified by Kevin Mar 2026
        "lat": 32.7076, "lon": -117.1570,
        "timezone": "America/Los_Angeles",
        "asos_station": "KSAN",      # San Diego Intl, ~2 mi NW — assumed
        "aliases": [],
    },
    "Oracle Park": {
        "mlbam_ids": [2395],
        "city": "San Francisco, CA",
        "team": "San Francisco Giants",
        "roof_type": "open_air",
        "cf_bearing_degrees": 90,    # CF is E — verified by Kevin Mar 2026 (McCovey Cove behind CF)
        "lat": 37.7786, "lon": -122.3893,
        "timezone": "America/Los_Angeles",
        "asos_station": "KSFO",      # San Francisco Intl, ~13 mi S — verified Mar 2026 (KOAK wrong)
        "aliases": ["AT&T Park"],
    },

    # ── NEW / LIMITED HISTORY ─────────────────────────────────────────
    "Sutter Health Park": {
        "mlbam_ids": [2529],
        "city": "Sacramento, CA",
        "team": "Oakland Athletics",
        "roof_type": "open_air",
        "cf_bearing_degrees": 45,    # CF is NE — verified by Kevin Mar 2026
        "lat": 38.5802, "lon": -121.5005,
        "timezone": "America/Los_Angeles",
        "asos_station": "KSMF",      # Sacramento Intl, ~10 mi NW — assumed
        "aliases": [],
    },

    # ── EXCLUDE: SPRING TRAINING / SPECIAL VENUES ────────────────────
    # These are handled by exclusion in the data cleaning step.
    # George M. Steinbrenner Field, Sahlen Field, TD Ballpark,
    # Field of Dreams, Bristol Motor Speedway, London Stadium,
    # Estadio de Beisbol Monterrey, Estadio Alfredo Harp Helu,
    # Hiram Bithorn Stadium, Fort Bragg Field, Rickwood Field,
    # Journey Bank Ballpark, Muncy Bank Ballpark, BB&T Ballpark,
    # TD Ameritrade Park
}


# Build reverse lookup: any park name (including aliases) → canonical name.
# Stored in lowercase so lookups are case-insensitive — use .get(venue.lower()).
PARK_NAME_TO_CANONICAL = {}
for canonical, meta in PARK_METADATA.items():
    PARK_NAME_TO_CANONICAL[canonical.lower()] = canonical
    for alias in meta.get("aliases", []):
        PARK_NAME_TO_CANONICAL[alias.lower()] = canonical


# Special / non-MLB venues to drop entirely
EXCLUDED_VENUES = {
    # International / special event venues — no historical data, weather irrelevant
    "Tokyo Dome",               # Japan Series opener (Dodgers/Cubs etc.) — fixed dome
    "Gocheok Sky Dome",         # Seoul Series — fixed dome
    "London Stadium",           # London Series — open air but no historical data
    "Estadio de Beisbol Monterrey",
    "Estadio Alfredo Harp Helu",
    "Hiram Bithorn Stadium",
    # Special domestic event venues
    "Field of Dreams",
    "Bristol Motor Speedway",
    "Fort Bragg Field",
    "Rickwood Field",
    # Spring training / minor league venues
    "George M. Steinbrenner Field",
    "Sahlen Field",
    "TD Ballpark",
    "Journey Bank Ballpark",
    "Muncy Bank Ballpark",
    "BB&T Ballpark",
    "TD Ameritrade Park",
}

# Parks with retractable or fixed roofs
RETRACTABLE_PARKS = {
    name for name, meta in PARK_METADATA.items()
    if meta["roof_type"] == "retractable"
}

DOME_PARKS = {
    name for name, meta in PARK_METADATA.items()
    if meta["roof_type"] == "fixed_dome"
}

LIMITED_HISTORY_THRESHOLD = 150  # games; below this = "Limited park history"
