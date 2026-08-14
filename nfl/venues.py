"""nfl.venues — 32 NFL stadium database with ESPN team IDs as keys.

Each entry: name, short, abbrev, conf (AFC/NFC), div (East/West/North/South),
color, nws_unsupported (always False — all US), stadium dict.

Roof types:
    "open"          — normal outdoor stadium
    "retractable"   — toggles, defaults Closed (MLB pattern)
    "fixed_dome"    — always closed, no weather impact
    "fixed_canopy"  — SoFi only, weather still matters

The `roof_summer_status` field on retractables sets the default toggle
state per MLB convention ("likely_closed" = default Closed active).
Retractable NFL venues are typically AC-cooled August-October when most
games hit, so default is Closed.
"""

from __future__ import annotations
from typing import Optional


NFL_TEAMS: dict[int, dict] = {
    # === AFC EAST ===
    2: {
        "name": "Buffalo Bills", "short": "Bills", "abbrev": "BUF",
        "conf": "AFC", "div": "East", "color": "#00338D",
        "nws_unsupported": False,
        "stadium": {
            "name": "Highmark Stadium", "city": "Orchard Park, NY",
            "lat": 42.7738, "lon": -78.7870,
            "timezone": "America/New_York",
            "cap": 71608, "field_bearing_degrees": 135, "roof_type": "open",
        },
    },
    15: {
        "name": "Miami Dolphins", "short": "Dolphins", "abbrev": "MIA",
        "conf": "AFC", "div": "East", "color": "#008E97",
        "nws_unsupported": False,
        "stadium": {
            "name": "Hard Rock Stadium", "city": "Miami Gardens, FL",
            "lat": 25.9580, "lon": -80.2389,
            "timezone": "America/New_York",
            "cap": 65326, "field_bearing_degrees": 135, "roof_type": "open",
        },
    },
    17: {
        "name": "New England Patriots", "short": "Patriots", "abbrev": "NE",
        "conf": "AFC", "div": "East", "color": "#002244",
        "nws_unsupported": False,
        "stadium": {
            "name": "Gillette Stadium", "city": "Foxborough, MA",
            "lat": 42.0909, "lon": -71.2643,
            "timezone": "America/New_York",
            "cap": 65878, "field_bearing_degrees": 157.5, "roof_type": "open",
        },
    },
    20: {
        "name": "New York Jets", "short": "Jets", "abbrev": "NYJ",
        "conf": "AFC", "div": "East", "color": "#125740",
        "nws_unsupported": False,
        "stadium": {
            "name": "MetLife Stadium", "city": "East Rutherford, NJ",
            "lat": 40.8136, "lon": -74.0744,
            "timezone": "America/New_York",
            "cap": 82500, "field_bearing_degrees": 180, "roof_type": "open",
        },
    },

    # === AFC NORTH ===
    33: {
        "name": "Baltimore Ravens", "short": "Ravens", "abbrev": "BAL",
        "conf": "AFC", "div": "North", "color": "#241773",
        "nws_unsupported": False,
        "stadium": {
            "name": "M&T Bank Stadium", "city": "Baltimore, MD",
            "lat": 39.2780, "lon": -76.6227,
            "timezone": "America/New_York",
            "cap": 71008, "field_bearing_degrees": 112.5, "roof_type": "open",
        },
    },
    4: {
        "name": "Cincinnati Bengals", "short": "Bengals", "abbrev": "CIN",
        "conf": "AFC", "div": "North", "color": "#FB4F14",
        "nws_unsupported": False,
        "stadium": {
            "name": "Paycor Stadium", "city": "Cincinnati, OH",
            "lat": 39.0955, "lon": -84.5161,
            "timezone": "America/New_York",
            "cap": 65515, "field_bearing_degrees": 135, "roof_type": "open",
        },
    },
    5: {
        "name": "Cleveland Browns", "short": "Browns", "abbrev": "CLE",
        "conf": "AFC", "div": "North", "color": "#311D00",
        "nws_unsupported": False,
        "stadium": {
            "name": "Huntington Bank Field", "city": "Cleveland, OH",
            "lat": 41.5061, "lon": -81.6995,
            "timezone": "America/New_York",
            "cap": 67431, "field_bearing_degrees": 45, "roof_type": "open",
        },
    },
    23: {
        "name": "Pittsburgh Steelers", "short": "Steelers", "abbrev": "PIT",
        "conf": "AFC", "div": "North", "color": "#FFB612",
        "nws_unsupported": False,
        "stadium": {
            "name": "Acrisure Stadium", "city": "Pittsburgh, PA",
            "lat": 40.4468, "lon": -80.0158,
            "timezone": "America/New_York",
            "cap": 68400, "field_bearing_degrees": 157.5, "roof_type": "open",
        },
    },

    # === AFC SOUTH ===
    34: {
        "name": "Houston Texans", "short": "Texans", "abbrev": "HOU",
        "conf": "AFC", "div": "South", "color": "#03202F",
        "nws_unsupported": False,
        "stadium": {
            "name": "NRG Stadium", "city": "Houston, TX",
            "lat": 29.6847, "lon": -95.4107,
            "timezone": "America/Chicago",
            "cap": 72220, "field_bearing_degrees": 180, "roof_type": "retractable",
            "roof_summer_status": "likely_closed",
        },
    },
    11: {
        "name": "Indianapolis Colts", "short": "Colts", "abbrev": "IND",
        "conf": "AFC", "div": "South", "color": "#002C5F",
        "nws_unsupported": False,
        "stadium": {
            "name": "Lucas Oil Stadium", "city": "Indianapolis, IN",
            "lat": 39.7601, "lon": -86.1639,
            "timezone": "America/Indiana/Indianapolis",
            "cap": 67000, "field_bearing_degrees": 45, "roof_type": "retractable",
            "roof_summer_status": "likely_closed",
        },
    },
    30: {
        "name": "Jacksonville Jaguars", "short": "Jaguars", "abbrev": "JAX",
        "conf": "AFC", "div": "South", "color": "#101820",
        "nws_unsupported": False,
        "stadium": {
            "name": "EverBank Stadium", "city": "Jacksonville, FL",
            "lat": 30.3239, "lon": -81.6373,
            "timezone": "America/New_York",
            "cap": 67838, "field_bearing_degrees": 22.5, "roof_type": "open",
        },
    },
    10: {
        "name": "Tennessee Titans", "short": "Titans", "abbrev": "TEN",
        "conf": "AFC", "div": "South", "color": "#0C2340",
        "nws_unsupported": False,
        "stadium": {
            "name": "Nissan Stadium", "city": "Nashville, TN",
            "lat": 36.1665, "lon": -86.7713,
            "timezone": "America/Chicago",
            "cap": 69143, "field_bearing_degrees": 157.5, "roof_type": "open",
        },
    },

    # === AFC WEST ===
    7: {
        "name": "Denver Broncos", "short": "Broncos", "abbrev": "DEN",
        "conf": "AFC", "div": "West", "color": "#FB4F14",
        "nws_unsupported": False,
        "stadium": {
            "name": "Empower Field at Mile High", "city": "Denver, CO",
            "lat": 39.7439, "lon": -105.0201,
            "timezone": "America/Denver",
            "cap": 76125, "field_bearing_degrees": 180, "roof_type": "open",
        },
    },
    12: {
        "name": "Kansas City Chiefs", "short": "Chiefs", "abbrev": "KC",
        "conf": "AFC", "div": "West", "color": "#E31837",
        "nws_unsupported": False,
        "stadium": {
            "name": "GEHA Field at Arrowhead Stadium", "city": "Kansas City, MO",
            "lat": 39.0489, "lon": -94.4839,
            "timezone": "America/Chicago",
            "cap": 76416, "field_bearing_degrees": 135, "roof_type": "open",
        },
    },
    13: {
        "name": "Las Vegas Raiders", "short": "Raiders", "abbrev": "LV",
        "conf": "AFC", "div": "West", "color": "#000000",
        "nws_unsupported": False,
        "stadium": {
            "name": "Allegiant Stadium", "city": "Paradise, NV",
            "lat": 36.0908, "lon": -115.1830,
            "timezone": "America/Los_Angeles",
            "cap": 65000, "field_bearing_degrees": None, "roof_type": "fixed_dome",
        },
    },
    24: {
        "name": "Los Angeles Chargers", "short": "Chargers", "abbrev": "LAC",
        "conf": "AFC", "div": "West", "color": "#0080C6",
        "nws_unsupported": False,
        "stadium": {
            "name": "SoFi Stadium", "city": "Inglewood, CA",
            "lat": 33.9534, "lon": -118.3387,
            "timezone": "America/Los_Angeles",
            "cap": 70240, "field_bearing_degrees": None, "roof_type": "fixed_canopy",
        },
    },

    # === NFC EAST ===
    6: {
        "name": "Dallas Cowboys", "short": "Cowboys", "abbrev": "DAL",
        "conf": "NFC", "div": "East", "color": "#003594",
        "nws_unsupported": False,
        "stadium": {
            "name": "AT&T Stadium", "city": "Arlington, TX",
            "lat": 32.7473, "lon": -97.0945,
            "timezone": "America/Chicago",
            "cap": 80000, "field_bearing_degrees": 67.5, "roof_type": "retractable",
            "roof_summer_status": "likely_closed",
        },
    },
    19: {
        "name": "New York Giants", "short": "Giants", "abbrev": "NYG",
        "conf": "NFC", "div": "East", "color": "#0B2265",
        "nws_unsupported": False,
        "stadium": {
            "name": "MetLife Stadium", "city": "East Rutherford, NJ",
            "lat": 40.8136, "lon": -74.0744,
            "timezone": "America/New_York",
            "cap": 82500, "field_bearing_degrees": 180, "roof_type": "open",
        },
    },
    21: {
        "name": "Philadelphia Eagles", "short": "Eagles", "abbrev": "PHI",
        "conf": "NFC", "div": "East", "color": "#004C54",
        "nws_unsupported": False,
        "stadium": {
            "name": "Lincoln Financial Field", "city": "Philadelphia, PA",
            "lat": 39.9008, "lon": -75.1675,
            "timezone": "America/New_York",
            "cap": 69596, "field_bearing_degrees": 180, "roof_type": "open",
        },
    },
    28: {
        "name": "Washington Commanders", "short": "Commanders", "abbrev": "WAS",
        "conf": "NFC", "div": "East", "color": "#5A1414",
        "nws_unsupported": False,
        "stadium": {
            "name": "Northwest Stadium", "city": "Landover, MD",
            "lat": 38.9078, "lon": -76.8645,
            "timezone": "America/New_York",
            "cap": 67617, "field_bearing_degrees": 135, "roof_type": "open",
        },
    },

    # === NFC NORTH ===
    3: {
        "name": "Chicago Bears", "short": "Bears", "abbrev": "CHI",
        "conf": "NFC", "div": "North", "color": "#0B162A",
        "nws_unsupported": False,
        "stadium": {
            "name": "Soldier Field", "city": "Chicago, IL",
            "lat": 41.8623, "lon": -87.6167,
            "timezone": "America/Chicago",
            "cap": 61500, "field_bearing_degrees": 180, "roof_type": "open",
        },
    },
    8: {
        "name": "Detroit Lions", "short": "Lions", "abbrev": "DET",
        "conf": "NFC", "div": "North", "color": "#0076B6",
        "nws_unsupported": False,
        "stadium": {
            "name": "Ford Field", "city": "Detroit, MI",
            "lat": 42.3400, "lon": -83.0456,
            "timezone": "America/Detroit",
            "cap": 65000, "field_bearing_degrees": None, "roof_type": "fixed_dome",
        },
    },
    9: {
        "name": "Green Bay Packers", "short": "Packers", "abbrev": "GB",
        "conf": "NFC", "div": "North", "color": "#203731",
        "nws_unsupported": False,
        "stadium": {
            "name": "Lambeau Field", "city": "Green Bay, WI",
            "lat": 44.5013, "lon": -88.0622,
            "timezone": "America/Chicago",
            "cap": 81441, "field_bearing_degrees": 180, "roof_type": "open",
        },
    },
    16: {
        "name": "Minnesota Vikings", "short": "Vikings", "abbrev": "MIN",
        "conf": "NFC", "div": "North", "color": "#4F2683",
        "nws_unsupported": False,
        "stadium": {
            "name": "U.S. Bank Stadium", "city": "Minneapolis, MN",
            "lat": 44.9737, "lon": -93.2581,
            "timezone": "America/Chicago",
            "cap": 66860, "field_bearing_degrees": None, "roof_type": "fixed_dome",
        },
    },

    # === NFC SOUTH ===
    1: {
        "name": "Atlanta Falcons", "short": "Falcons", "abbrev": "ATL",
        "conf": "NFC", "div": "South", "color": "#A71930",
        "nws_unsupported": False,
        "stadium": {
            "name": "Mercedes-Benz Stadium", "city": "Atlanta, GA",
            "lat": 33.7553, "lon": -84.4006,
            "timezone": "America/New_York",
            "cap": 71000, "field_bearing_degrees": 90, "roof_type": "retractable",
            "roof_summer_status": "likely_closed",
        },
    },
    29: {
        "name": "Carolina Panthers", "short": "Panthers", "abbrev": "CAR",
        "conf": "NFC", "div": "South", "color": "#0085CA",
        "nws_unsupported": False,
        "stadium": {
            "name": "Bank of America Stadium", "city": "Charlotte, NC",
            "lat": 35.2258, "lon": -80.8528,
            "timezone": "America/New_York",
            "cap": 74867, "field_bearing_degrees": 135, "roof_type": "open",
        },
    },
    18: {
        "name": "New Orleans Saints", "short": "Saints", "abbrev": "NO",
        "conf": "NFC", "div": "South", "color": "#D3BC8D",
        "nws_unsupported": False,
        "stadium": {
            "name": "Caesars Superdome", "city": "New Orleans, LA",
            "lat": 29.9511, "lon": -90.0812,
            "timezone": "America/Chicago",
            "cap": 73208, "field_bearing_degrees": None, "roof_type": "fixed_dome",
        },
    },
    27: {
        "name": "Tampa Bay Buccaneers", "short": "Buccaneers", "abbrev": "TB",
        "conf": "NFC", "div": "South", "color": "#D50A0A",
        "nws_unsupported": False,
        "stadium": {
            "name": "Raymond James Stadium", "city": "Tampa, FL",
            "lat": 27.9759, "lon": -82.5033,
            "timezone": "America/New_York",
            "cap": 65890, "field_bearing_degrees": 180, "roof_type": "open",
        },
    },

    # === NFC WEST ===
    22: {
        "name": "Arizona Cardinals", "short": "Cardinals", "abbrev": "ARI",
        "conf": "NFC", "div": "West", "color": "#97233F",
        "nws_unsupported": False,
        "stadium": {
            "name": "State Farm Stadium", "city": "Glendale, AZ",
            "lat": 33.5276, "lon": -112.2626,
            "timezone": "America/Phoenix",
            "cap": 63400, "field_bearing_degrees": 135, "roof_type": "retractable",
            "roof_summer_status": "likely_closed",
        },
    },
    14: {
        "name": "Los Angeles Rams", "short": "Rams", "abbrev": "LAR",
        "conf": "NFC", "div": "West", "color": "#003594",
        "nws_unsupported": False,
        "stadium": {
            "name": "SoFi Stadium", "city": "Inglewood, CA",
            "lat": 33.9534, "lon": -118.3387,
            "timezone": "America/Los_Angeles",
            "cap": 70240, "field_bearing_degrees": None, "roof_type": "fixed_canopy",
        },
    },
    25: {
        "name": "San Francisco 49ers", "short": "49ers", "abbrev": "SF",
        "conf": "NFC", "div": "West", "color": "#AA0000",
        "nws_unsupported": False,
        "stadium": {
            "name": "Levi's Stadium", "city": "Santa Clara, CA",
            "lat": 37.4030, "lon": -121.9698,
            "timezone": "America/Los_Angeles",
            "cap": 68500, "field_bearing_degrees": 157.5, "roof_type": "open",
        },
    },
    26: {
        "name": "Seattle Seahawks", "short": "Seahawks", "abbrev": "SEA",
        "conf": "NFC", "div": "West", "color": "#002244",
        "nws_unsupported": False,
        "stadium": {
            "name": "Lumen Field", "city": "Seattle, WA",
            "lat": 47.5952, "lon": -122.3316,
            "timezone": "America/Los_Angeles",
            "cap": 68740, "field_bearing_degrees": 180, "roof_type": "open",
        },
    },
}


def get_team(team_id: int) -> Optional[dict]:
    return NFL_TEAMS.get(int(team_id) if team_id else 0)


def get_stadium(team_id: int) -> Optional[dict]:
    team = get_team(team_id)
    return team["stadium"] if team else None


def teams_by_conf(conf: str) -> list[dict]:
    """conf: 'AFC' or 'NFC'"""
    return [t for t in NFL_TEAMS.values() if t["conf"] == conf]


def is_dome(team_id: int) -> bool:
    s = get_stadium(team_id)
    return bool(s and s["roof_type"] == "fixed_dome")


def is_retractable(team_id: int) -> bool:
    s = get_stadium(team_id)
    return bool(s and s["roof_type"] == "retractable")


# ── International venues ──────────────────────────────────────────────────
#
# NFL International Series venues. When ESPN reports a game with a
# non-US venue country, the schedule fetcher swaps in one of these
# instead of using the home team's US stadium. Every entry has
# nws_unsupported=True so the slate builder routes them through
# WeatherAPI (NWS only covers US territory).

INTERNATIONAL_VENUES: dict[str, dict] = {
    "tottenham": {"name": "Tottenham Hotspur Stadium", "city": "London, UK",
                  "lat": 51.6042, "lon": -0.0666, "timezone": "Europe/London",
                  "roof_type": "open", "capacity": 62850,
                  "nws_unsupported": True, "country": "GB"},
    "wembley":   {"name": "Wembley Stadium", "city": "London, UK",
                  "lat": 51.5560, "lon": -0.2795, "timezone": "Europe/London",
                  "roof_type": "retractable", "capacity": 90000,
                  "nws_unsupported": True, "country": "GB"},
    "azteca":    {"name": "Estadio Azteca", "city": "Mexico City, MX",
                  "lat": 19.3029, "lon": -99.1505, "timezone": "America/Mexico_City",
                  "roof_type": "open", "capacity": 87000,
                  "nws_unsupported": True, "country": "MX"},
    "frankfurt": {"name": "Deutsche Bank Park", "city": "Frankfurt, DE",
                  "lat": 50.0687, "lon": 8.6456, "timezone": "Europe/Berlin",
                  "roof_type": "retractable", "capacity": 51500,
                  "nws_unsupported": True, "country": "DE"},
    "munich":    {"name": "Allianz Arena", "city": "Munich, DE",
                  "lat": 48.2188, "lon": 11.6247, "timezone": "Europe/Berlin",
                  "roof_type": "open", "capacity": 75000,
                  "nws_unsupported": True, "country": "DE"},
    "berlin":    {"name": "Olympiastadion", "city": "Berlin, DE",
                  "lat": 52.5147, "lon": 13.2394, "timezone": "Europe/Berlin",
                  "roof_type": "open", "capacity": 74475,
                  "nws_unsupported": True, "country": "DE"},
    "sao-paulo": {"name": "Arena Corinthians", "city": "Sao Paulo, BR",
                  "lat": -23.5453, "lon": -46.4742, "timezone": "America/Sao_Paulo",
                  "roof_type": "open", "capacity": 49000,
                  "nws_unsupported": True, "country": "BR"},
    "dublin":    {"name": "Croke Park", "city": "Dublin, IE",
                  "lat": 53.3608, "lon": -6.2511, "timezone": "Europe/Dublin",
                  "roof_type": "open", "capacity": 82300,
                  "nws_unsupported": True, "country": "IE"},
    "madrid":    {"name": "Estadio Santiago Bernabeu", "city": "Madrid, ES",
                  "lat": 40.4531, "lon": -3.6883, "timezone": "Europe/Madrid",
                  "roof_type": "retractable", "capacity": 78000,
                  "nws_unsupported": True, "country": "ES"},
    "melbourne": {"name": "Melbourne Cricket Ground", "city": "Melbourne, AU",
                  "lat": -37.8199, "lon": 144.9834, "timezone": "Australia/Melbourne",
                  "roof_type": "open", "capacity": 100024,
                  "nws_unsupported": True, "country": "AU"},
}


def lookup_international_venue(fullname, city, country=None) -> Optional[dict]:
    """Match an ESPN international venue payload to our override table.

    Match order:
      1. Fullname substring match ("Tottenham Hotspur Stadium")
      2. City substring match ("London", "Mexico City")
      3. Country code fallback (only when exactly one venue in that country)
    """
    fn = (fullname or "").lower()
    ci = (city or "").lower()
    co = (country or "").strip().upper()

    for slug, v in INTERNATIONAL_VENUES.items():
        if v["name"].lower() in fn or slug in fn:
            return dict(v)

    for slug, v in INTERNATIONAL_VENUES.items():
        v_city = v["city"].split(",")[0].strip().lower()
        if v_city and v_city in ci:
            return dict(v)

    if co:
        matches = [v for v in INTERNATIONAL_VENUES.values() if v["country"] == co]
        if len(matches) == 1:
            return dict(matches[0])

    return None


# EOF-CANARY 2026-07-04-cfb-recovery
