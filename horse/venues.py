"""horse.venues — marquee US thoroughbred tracks.

Facts sourced from track websites + Equibase. Only tracks I can source
lat/lon and confirm are actively racing in 2026 are included. Others
can be added as needed.

Turf/dirt notes matter for handicappers reading the forecast — a rain
day at a dirt track ("sloppy" surface) plays very differently than a
rain day at a turf track ("yielding" or "soft").
"""

# slug -> venue dict
HORSE_TRACKS = {
    "churchill-downs": {
        "slug": "churchill-downs",
        "name": "Churchill Downs",
        "city": "Louisville, KY",
        "lat": 38.2075,
        "lon": -85.7783,
        "timezone": "America/Kentucky/Louisville",
        "surfaces": ["dirt (1-mile main)", "turf (7f inner)"],
        "notes": "Home of the Kentucky Derby (first Saturday in May) and the Kentucky Oaks. Spring meet late April to late June, September meet, then Fall meet in October and November.",
    },
    "belmont-park": {
        "slug": "belmont-park",
        "name": "Belmont Park",
        "city": "Elmont, NY",
        "lat": 40.7156,
        "lon": -73.7261,
        "timezone": "America/New_York",
        "surfaces": ["dirt (1.5-mile main)", "turf (widener and inner)"],
        "notes": "Traditional home of the Belmont Stakes. Undergoing a multi-year rebuild that has relocated the 2024 and 2025 Belmont Stakes to Saratoga.",
    },
    "pimlico": {
        "slug": "pimlico",
        "name": "Pimlico Race Course",
        "city": "Baltimore, MD",
        "lat": 39.3535,
        "lon": -76.6752,
        "timezone": "America/New_York",
        "surfaces": ["dirt (1-mile main)", "turf"],
        "notes": "Home of the Preakness Stakes (third Saturday of May). Middle jewel of the Triple Crown.",
    },
    "saratoga": {
        "slug": "saratoga",
        "name": "Saratoga Race Course",
        "city": "Saratoga Springs, NY",
        "lat": 43.0798,
        "lon": -73.7783,
        "timezone": "America/New_York",
        "surfaces": ["dirt (1.125-mile main)", "turf (Mellon inner + main turf)"],
        "notes": "Summer meet mid-July through Labor Day. Travers Stakes and Whitney Stakes headline the meet. Known as \"the graveyard of favorites.\"",
    },
    "del-mar": {
        "slug": "del-mar",
        "name": "Del Mar Racetrack",
        "city": "Del Mar, CA",
        "lat": 32.9739,
        "lon": -117.2649,
        "timezone": "America/Los_Angeles",
        "surfaces": ["dirt (1-mile main)", "turf (7/8-mile)"],
        "notes": "Coastal Southern California. Summer meet mid-July through early September, then Fall (Bing Crosby) meet in November. Pacific Classic headlines the summer.",
    },
    "santa-anita": {
        "slug": "santa-anita",
        "name": "Santa Anita Park",
        "city": "Arcadia, CA",
        "lat": 34.1408,
        "lon": -118.0464,
        "timezone": "America/Los_Angeles",
        "surfaces": ["dirt (1-mile main)", "turf (down-hill and inner turf)"],
        "notes": "Winter/spring meet late December through mid-June, then autumn meet Oct-Nov. Santa Anita Handicap, Santa Anita Derby, and multiple Breeders' Cup hosts.",
    },
    "keeneland": {
        "slug": "keeneland",
        "name": "Keeneland",
        "city": "Lexington, KY",
        "lat": 38.0442,
        "lon": -84.6117,
        "timezone": "America/Kentucky/Louisville",
        "surfaces": ["dirt (1.0625-mile main)", "turf"],
        "notes": "Short but elite spring (April) and fall (October) meets. Blue Grass Stakes is the flagship Derby prep.",
    },
    "oaklawn": {
        "slug": "oaklawn",
        "name": "Oaklawn Park",
        "city": "Hot Springs, AR",
        "lat": 34.4881,
        "lon": -93.0708,
        "timezone": "America/Chicago",
        "surfaces": ["dirt (1-mile main)"],
        "notes": "Winter and spring meet December through early May. Arkansas Derby is a key Kentucky Derby prep.",
    },
    "gulfstream": {
        "slug": "gulfstream",
        "name": "Gulfstream Park",
        "city": "Hallandale Beach, FL",
        "lat": 25.9805,
        "lon": -80.1408,
        "timezone": "America/New_York",
        "surfaces": ["dirt (1.125-mile main)", "turf"],
        "notes": "Championship (winter) meet December through March, then summer meet. Pegasus World Cup (late January) and Florida Derby (late March/early April) headline.",
    },
    "woodbine": {
        "slug": "woodbine",
        "name": "Woodbine Racetrack",
        "city": "Toronto, ON",
        "lat": 43.7069,
        "lon": -79.6011,
        "timezone": "America/Toronto",
        "surfaces": ["all-weather (Tapeta 1.5-mile main)", "turf (E.P. Taylor 1.5-mile)"],
        "notes": "Season April through December. Queen's Plate and Woodbine Mile headline. Only major North American thoroughbred track with a Tapeta main surface.",
        "nws_unsupported": True,  # Canadian venue
    },
}


def lookup_track(slug: str):
    """Case-insensitive slug lookup. Returns None on miss."""
    if not slug:
        return None
    return HORSE_TRACKS.get(slug.lower())
