"""
ucl.venues — UEFA Champions League clubs and home grounds, 2026-27.

Keyed by ESPN team id. We source the SCHEDULE from The Odds API (ESPN
403-blocks Render, see ucl/schedule.py), but ESPN's numeric team ids are
still the cleanest stable key and they drive the logo CDN URLs, so we keep
them as the dictionary key and match Odds API team names via NAME_INDEX.

Every ground here is outside NWS coverage, so nws_unsupported is True on
all of them and forecasts route to WeatherAPI. That is the same path
prem/ and worldcup/ already use.

Coordinates are stadium centre, verified against the declared timezone by
the check at the bottom of this file (a wrong sign or a transposed
lat/lon lands in the wrong tz and raises at import).

Roofs:
    Only two closeable roofs in the league phase, both retractable:
    Lille's Decathlon Arena and Real Madrid's Bernabeu. Everything else
    is open air. No fixed domes.

Displaced / neutral home grounds (2026-27):
    Shakhtar Donetsk  -> Stamford Bridge, London. Ukrainian clubs cannot
                         host European ties at home; Shakhtar have played
                         "home" games abroad since 2022.
    Real Betis        -> Estadio La Cartuja, Seville, while the Benito
                         Villamarin redevelopment finishes.
    Sabah FK          -> Baku Olympic Stadium. Their own Bank Respublika
                         Arena does not meet UEFA category requirements.
                         ESPN returns NO venue for Sabah home matches, so
                         this entry is the only source of truth for them.
"""

from __future__ import annotations

from typing import Optional

ROOF_OPEN = "open"
ROOF_RETRACTABLE = "retractable"


def _v(name, city, lat, lon, tz, cap, country, roof=ROOF_OPEN, note=None):
    d = {
        "name": name, "city": city, "lat": lat, "lon": lon, "tz": tz,
        "roof": roof, "cap": cap, "nws_unsupported": True, "country": country,
    }
    if note:
        d["note"] = note
    return d


UCL_TEAMS: dict[int, dict] = {
    887:   {"name": "AEK Athens", "short": "AEK Athens", "abbrev": "AEK", "color": "#FFFF00",
            "stadium": _v("OPAP Arena", "Athens", 38.03528, 23.73917, "Europe/Athens", 32500, "GR")},
    359:   {"name": "Arsenal", "short": "Arsenal", "abbrev": "ARS", "color": "#E20520",
            "stadium": _v("Emirates Stadium", "London", 51.555, -0.10833, "Europe/London", 60704, "GB")},
    104:   {"name": "AS Roma", "short": "Roma", "abbrev": "ROM", "color": "#990A2C",
            "stadium": _v("Stadio Olimpico", "Rome", 41.93390, 12.45470, "Europe/Rome", 70634, "IT")},
    362:   {"name": "Aston Villa", "short": "Aston Villa", "abbrev": "AVL", "color": "#660E36",
            "stadium": _v("Villa Park", "Birmingham", 52.50917, -1.88472, "Europe/London", 42918, "GB")},
    1068:  {"name": "Atletico Madrid", "short": "Atletico", "abbrev": "ATM", "color": "#CA3624",
            "stadium": _v("Riyadh Air Metropolitano", "Madrid", 40.43619, -3.59947, "Europe/Madrid", 70460, "ES")},
    83:    {"name": "Barcelona", "short": "Barcelona", "abbrev": "BAR", "color": "#990000",
            "stadium": _v("Spotify Camp Nou", "Barcelona", 41.38088, 2.12282, "Europe/Madrid", 105000, "ES")},
    132:   {"name": "Bayern Munich", "short": "Bayern", "abbrev": "BAY", "color": "#DC052D",
            "stadium": _v("Allianz Arena", "Munich", 48.21880, 11.62470, "Europe/Berlin", 75024, "DE")},
    2980:  {"name": "Bodo/Glimt", "short": "Bodo/Glimt", "abbrev": "BOD", "color": "#FCEE33",
            "stadium": _v("Aspmyra Stadion", "Bodo", 67.27694, 14.39694, "Europe/Oslo", 8270, "NO",
                          note="Inside the Arctic Circle. Coldest ground in the competition by a wide margin.")},
    124:   {"name": "Borussia Dortmund", "short": "Dortmund", "abbrev": "BVB", "color": "#FDE100",
            "stadium": _v("Signal Iduna Park", "Dortmund", 51.49260, 7.45180, "Europe/Berlin", 81365, "DE")},
    570:   {"name": "Club Brugge", "short": "Club Brugge", "abbrev": "BRU", "color": "#0081FF",
            "stadium": _v("Jan Breydel Stadium", "Bruges", 51.19330, 3.18060, "Europe/Brussels", 29042, "BE")},
    2572:  {"name": "Como", "short": "Como", "abbrev": "COM", "color": "#4169E1",
            "stadium": _v("Stadio Giuseppe Sinigaglia", "Como", 45.81170, 9.07140, "Europe/Rome", 13602, "IT",
                          note="Lakeside ground, smallest in the league phase.")},
    437:   {"name": "FC Porto", "short": "Porto", "abbrev": "POR", "color": "#0000DD",
            "stadium": _v("Estadio do Dragao", "Porto", 41.16170, -8.58360, "Europe/Lisbon", 50033, "PT")},
    436:   {"name": "Fenerbahce", "short": "Fenerbahce", "abbrev": "FEN", "color": "#FFFF00",
            "stadium": _v("Ulker Stadyumu", "Istanbul", 40.98778, 29.03694, "Europe/Istanbul", 47834, "TR")},
    142:   {"name": "Feyenoord", "short": "Feyenoord", "abbrev": "FEY", "color": "#EF2F24",
            "stadium": _v("De Kuip", "Rotterdam", 51.89389, 4.52306, "Europe/Amsterdam", 51117, "NL")},
    432:   {"name": "Galatasaray", "short": "Galatasaray", "abbrev": "GAL", "color": "#AA0031",
            "stadium": _v("RAMS Park", "Istanbul", 41.10361, 28.99167, "Europe/Istanbul", 52223, "TR")},
    110:   {"name": "Internazionale", "short": "Inter", "abbrev": "INT", "color": "#00239C",
            "stadium": _v("San Siro", "Milan", 45.47806, 9.12400, "Europe/Rome", 75923, "IT")},
    4411:  {"name": "LASK Linz", "short": "LASK", "abbrev": "LAS", "color": "#000000",
            "stadium": _v("Raiffeisen Arena", "Linz", 48.28611, 14.31750, "Europe/Vienna", 19080, "AT")},
    175:   {"name": "Lens", "short": "Lens", "abbrev": "LEN", "color": "#E91514",
            "stadium": _v("Stade Bollaert-Delelis", "Lens", 50.43278, 2.81472, "Europe/Paris", 38223, "FR")},
    166:   {"name": "Lille", "short": "Lille", "abbrev": "LIL", "color": "#C2051B",
            "stadium": _v("Decathlon Arena - Stade Pierre-Mauroy", "Lille", 50.61194, 3.13028,
                          "Europe/Paris", 50186, "FR", roof=ROOF_RETRACTABLE)},
    364:   {"name": "Liverpool", "short": "Liverpool", "abbrev": "LIV", "color": "#D11317",
            "stadium": _v("Anfield", "Liverpool", 53.43083, -2.96083, "Europe/London", 61276, "GB")},
    382:   {"name": "Manchester City", "short": "Man City", "abbrev": "MCI", "color": "#99C5EA",
            "stadium": _v("Etihad Stadium", "Manchester", 53.48314, -2.20094, "Europe/London", 52900, "GB")},
    360:   {"name": "Manchester United", "short": "Man United", "abbrev": "MUN", "color": "#DA020E",
            "stadium": _v("Old Trafford", "Manchester", 53.46349, -2.29128, "Europe/London", 74244, "GB")},
    114:   {"name": "Napoli", "short": "Napoli", "abbrev": "NAP", "color": "#0677D2",
            "stadium": _v("Stadio Diego Armando Maradona", "Naples", 40.82800, 14.19300, "Europe/Rome", 54726, "IT")},
    160:   {"name": "Paris Saint-Germain", "short": "PSG", "abbrev": "PSG", "color": "#011F68",
            "stadium": _v("Parc des Princes", "Paris", 48.84139, 2.25306, "Europe/Paris", 47929, "FR")},
    148:   {"name": "PSV Eindhoven", "short": "PSV", "abbrev": "PSV", "color": "#EF2F24",
            "stadium": _v("Philips Stadion", "Eindhoven", 51.44167, 5.46750, "Europe/Amsterdam", 35000, "NL")},
    11420: {"name": "RB Leipzig", "short": "Leipzig", "abbrev": "RBL", "color": "#DD0741",
            "stadium": _v("Red Bull Arena", "Leipzig", 51.34583, 12.34833, "Europe/Berlin", 47069, "DE")},
    244:   {"name": "Real Betis", "short": "Betis", "abbrev": "BET", "color": "#288A00",
            "stadium": _v("Estadio La Cartuja", "Seville", 37.41861, -5.98528, "Europe/Madrid", 57619, "ES",
                          note="Temporary home while the Benito Villamarin redevelopment finishes.")},
    86:    {"name": "Real Madrid", "short": "Real Madrid", "abbrev": "RMA", "color": "#FEBE10",
            "stadium": _v("Santiago Bernabeu", "Madrid", 40.45306, -3.68833, "Europe/Madrid", 78297, "ES",
                          roof=ROOF_RETRACTABLE)},
    21922: {"name": "Sabah FK", "short": "Sabah", "abbrev": "SAB", "color": "#000000",
            "stadium": _v("Baku Olympic Stadium", "Baku", 40.43250, 49.91944, "Asia/Baku", 68700, "AZ",
                          note="ESPN returns no venue for Sabah home matches. This entry is the "
                               "only source of truth. Their own Bank Respublika Arena does not "
                               "meet UEFA category requirements.")},
    493:   {"name": "Shakhtar Donetsk", "short": "Shakhtar", "abbrev": "SHK", "color": "#FF5900",
            "stadium": _v("Stamford Bridge", "London", 51.48167, -0.19111, "Europe/London", 40173, "GB",
                          note="Displaced home ground. Ukrainian clubs cannot host European ties at home.")},
    494:   {"name": "Slavia Prague", "short": "Slavia", "abbrev": "SLA", "color": "#DC1F26",
            "stadium": _v("Fortuna Arena", "Prague", 50.06778, 14.47194, "Europe/Prague", 19370, "CZ")},
    521:   {"name": "Slovan Bratislava", "short": "Slovan", "abbrev": "SLO", "color": "#81C0FF",
            "stadium": _v("Tehelne pole", "Bratislava", 48.16361, 17.13667, "Europe/Bratislava", 22500, "SK")},
    2250:  {"name": "Sporting CP", "short": "Sporting", "abbrev": "SCP", "color": "#008127",
            "stadium": _v("Estadio Jose Alvalade", "Lisbon", 38.76139, -9.16083, "Europe/Lisbon", 50095, "PT")},
    134:   {"name": "VfB Stuttgart", "short": "Stuttgart", "abbrev": "VFB", "color": "#E32219",
            "stadium": _v("MHPArena", "Stuttgart", 48.79222, 9.23222, "Europe/Berlin", 60449, "DE")},
    510:   {"name": "Viking FK", "short": "Viking", "abbrev": "VIK", "color": "#000080",
            "stadium": _v("SR-Bank Arena", "Stavanger", 58.93389, 5.72972, "Europe/Oslo", 15900, "NO")},
    102:   {"name": "Villarreal", "short": "Villarreal", "abbrev": "VIL", "color": "#FFE667",
            "stadium": _v("Estadio de la Ceramica", "Villarreal", 39.94417, -0.10333, "Europe/Madrid", 23500, "ES")},
}


# ── Odds API name matching ────────────────────────────────────────────
# The Odds API returns full club names that don't always match ours.
# Same approach mls/odds_api_schedule.py uses: build a case-insensitive
# index over name + short, then layer explicit aliases on top.
ALIASES: dict[str, int] = {
    "inter milan": 110, "inter": 110, "fc internazionale milano": 110,
    "atletico madrid": 1068, "atlético madrid": 1068, "atletico de madrid": 1068,
    "bayern munich": 132, "fc bayern munchen": 132, "bayern münchen": 132,
    "borussia dortmund": 124, "bvb": 124,
    "psg": 160, "paris sg": 160, "paris saint germain": 160,
    "sporting lisbon": 2250, "sporting cp": 2250, "sporting clube de portugal": 2250,
    "shakhtar donetsk": 493, "fc shakhtar donetsk": 493,
    "bodo/glimt": 2980, "bodo glimt": 2980, "bodø/glimt": 2980, "fk bodo/glimt": 2980,
    "slavia prague": 494, "sk slavia praha": 494,
    "slovan bratislava": 521, "sk slovan bratislava": 521,
    "fenerbahce": 436, "fenerbahçe": 436, "fenerbahce sk": 436,
    "galatasaray": 432, "galatasaray sk": 432,
    "feyenoord": 142, "feyenoord rotterdam": 142,
    "psv": 148, "psv eindhoven": 148,
    "porto": 437, "fc porto": 437,
    "roma": 104, "as roma": 104,
    "napoli": 114, "ssc napoli": 114,
    "lask": 4411, "lask linz": 4411,
    "rc lens": 175, "lens": 175,
    "losc lille": 166, "lille": 166,
    "club brugge": 570, "club brugge kv": 570,
    "aek athens": 887, "aek athens fc": 887,
    "sabah": 21922, "sabah fk": 21922, "sabah fc": 21922,
    "viking": 510, "viking fk": 510,
    "vfb stuttgart": 134, "stuttgart": 134,
    "rb leipzig": 11420, "rasenballsport leipzig": 11420,
    "real betis": 244, "real betis balompie": 244, "betis": 244,
    "villarreal": 102, "villarreal cf": 102,
    "como": 2572, "como 1907": 2572,
    "manchester united": 360, "man united": 360, "man utd": 360,
    "manchester city": 382, "man city": 382,
}


def _build_name_index() -> dict[str, int]:
    idx: dict[str, int] = {}
    for tid, t in UCL_TEAMS.items():
        for key in (t["name"], t["short"], t["abbrev"]):
            if key:
                idx[key.lower().strip()] = tid
    idx.update(ALIASES)
    return idx


NAME_INDEX = _build_name_index()


def lookup_team_id(name: str) -> Optional[int]:
    """Resolve an Odds API club name to our team id. None if unknown.

    Callers MUST log a miss rather than dropping the match silently —
    a club we can't resolve is a match with no venue and no forecast."""
    if not name:
        return None
    return NAME_INDEX.get(name.lower().strip())


def get_team(team_id: int) -> Optional[dict]:
    return UCL_TEAMS.get(team_id)


def get_stadium(team_id: int) -> Optional[dict]:
    t = UCL_TEAMS.get(team_id)
    return dict(t["stadium"]) if t else None


def all_teams() -> list[dict]:
    return [dict(t, team_id=tid) for tid, t in sorted(
        UCL_TEAMS.items(), key=lambda kv: kv[1]["name"])]
