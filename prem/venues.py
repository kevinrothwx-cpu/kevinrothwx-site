"""prem.venues — Premier League 2026-27 team + stadium directory.

Keyed by ESPN team ID (soccer/eng.1 league). All stadiums are in England,
so all use Europe/London timezone. None of the current EPL grounds have
a closable roof over the pitch — Tottenham Hotspur Stadium has a
retractable pitch tray but the roof itself is fixed open above the
football surface.

All venues are outside NWS coverage and outside HRRR CONUS bounds, so
weather goes through WeatherAPI directly. HRRR is not fetched.

Sources: Wikipedia stadium pages + Premier League official + ESPN teams
endpoint (all cited inline as comments above each entry).
"""

from __future__ import annotations


ROOF_OPEN        = "open"
ROOF_RETRACTABLE = "retractable"
ROOF_FIXED_DOME  = "fixed_dome"


def _stadium(name, city, lat, lon, tz, roof=ROOF_OPEN, cap=None):
    """Helper to build a stadium dict cleanly."""
    return {
        "name": name, "city": city,
        "lat": lat, "lon": lon,
        "tz": tz, "roof": roof,
        "cap": cap,
        "nws_unsupported": True,  # UK — no NWS coverage, WeatherAPI only
        "country": "GB",
    }


# ── 2026-27 Premier League (20 teams) ────────────────────────────────────
# Promoted from Championship 2025-26: Coventry City, Ipswich Town, Hull City
# Relegated to Championship after 2025-26: Wolves, Burnley, West Ham
EPL_TEAMS: dict[int, dict] = {
    # https://en.wikipedia.org/wiki/Emirates_Stadium
    359: dict(name="Arsenal", short="Arsenal", abbrev="ARS",
              color="#E20520",
              stadium=_stadium("Emirates Stadium", "London",
                               51.55500, -0.10833, "Europe/London", cap=60704)),
    # https://en.wikipedia.org/wiki/Villa_Park
    362: dict(name="Aston Villa", short="Aston Villa", abbrev="AVL",
              color="#660E36",
              stadium=_stadium("Villa Park", "Birmingham",
                               52.50917, -1.88472, "Europe/London", cap=42918)),
    # https://en.wikipedia.org/wiki/Dean_Court
    349: dict(name="AFC Bournemouth", short="Bournemouth", abbrev="BOU",
              color="#F42727",
              stadium=_stadium("Vitality Stadium", "Bournemouth",
                               50.73528, -1.83833, "Europe/London", cap=11307)),
    # https://en.wikipedia.org/wiki/Brentford_Community_Stadium
    337: dict(name="Brentford", short="Brentford", abbrev="BRE",
              color="#E30613",
              stadium=_stadium("Gtech Community Stadium", "London",
                               51.49072, -0.28905, "Europe/London", cap=17250)),
    # https://en.wikipedia.org/wiki/Falmer_Stadium
    331: dict(name="Brighton & Hove Albion", short="Brighton", abbrev="BHA",
              color="#0057B8",
              stadium=_stadium("American Express Stadium", "Falmer",
                               50.86186, -0.08333, "Europe/London", cap=31876)),
    # https://en.wikipedia.org/wiki/Stamford_Bridge_(stadium)
    363: dict(name="Chelsea", short="Chelsea", abbrev="CHE",
              color="#034694",
              stadium=_stadium("Stamford Bridge", "London",
                               51.48167, -0.19111, "Europe/London", cap=40173)),
    # https://en.wikipedia.org/wiki/Coventry_Building_Society_Arena
    # Newly promoted for 2026-27.
    388: dict(name="Coventry City", short="Coventry", abbrev="COV",
              color="#87CCED",
              stadium=_stadium("Coventry Building Society Arena", "Coventry",
                               52.44821, -1.49694, "Europe/London", cap=32609)),
    # https://en.wikipedia.org/wiki/Selhurst_Park
    384: dict(name="Crystal Palace", short="Crystal Palace", abbrev="CRY",
              color="#1B458F",
              stadium=_stadium("Selhurst Park", "London",
                               51.39833, -0.08556, "Europe/London", cap=25486)),
    # https://en.wikipedia.org/wiki/Hill_Dickinson_Stadium
    # New home from 2025-26 (replaced Goodison Park). Bramley-Moore Dock.
    368: dict(name="Everton", short="Everton", abbrev="EVE",
              color="#003399",
              stadium=_stadium("Hill Dickinson Stadium", "Liverpool",
                               53.42510, -3.00280, "Europe/London", cap=52769)),
    # https://en.wikipedia.org/wiki/Craven_Cottage
    370: dict(name="Fulham", short="Fulham", abbrev="FUL",
              color="#CC0000",
              stadium=_stadium("Craven Cottage", "London",
                               51.47500, -0.22167, "Europe/London", cap=28800)),
    # https://en.wikipedia.org/wiki/MKM_Stadium
    # Newly promoted for 2026-27 (via Championship play-off).
    306: dict(name="Hull City", short="Hull", abbrev="HUL",
              color="#F28800",
              stadium=_stadium("MKM Stadium", "Kingston upon Hull",
                               53.74585, -0.36892, "Europe/London", cap=24620)),
    # https://en.wikipedia.org/wiki/Portman_Road
    # Newly promoted for 2026-27 (Championship winners 2025-26).
    373: dict(name="Ipswich Town", short="Ipswich", abbrev="IPS",
              color="#0000FA",
              stadium=_stadium("Portman Road", "Ipswich",
                               52.05506, 1.14483, "Europe/London", cap=30056)),
    # https://en.wikipedia.org/wiki/Elland_Road
    357: dict(name="Leeds United", short="Leeds", abbrev="LEE",
              color="#1D428A",
              stadium=_stadium("Elland Road", "Leeds",
                               53.77778, -1.57222, "Europe/London", cap=37645)),
    # https://en.wikipedia.org/wiki/Anfield
    364: dict(name="Liverpool", short="Liverpool", abbrev="LIV",
              color="#C8102E",
              stadium=_stadium("Anfield", "Liverpool",
                               53.43083, -2.96083, "Europe/London", cap=61276)),
    # https://en.wikipedia.org/wiki/City_of_Manchester_Stadium
    382: dict(name="Manchester City", short="Man City", abbrev="MCI",
              color="#6CABDD",
              stadium=_stadium("Etihad Stadium", "Manchester",
                               53.48314, -2.20094, "Europe/London", cap=52900)),
    # https://en.wikipedia.org/wiki/Old_Trafford
    360: dict(name="Manchester United", short="Man United", abbrev="MUN",
              color="#DA020E",
              stadium=_stadium("Old Trafford", "Manchester",
                               53.46349, -2.29128, "Europe/London", cap=74244)),
    # https://en.wikipedia.org/wiki/St_James%27_Park
    361: dict(name="Newcastle United", short="Newcastle", abbrev="NEW",
              color="#241F20",
              stadium=_stadium("St James' Park", "Newcastle upon Tyne",
                               54.97578, -1.61990, "Europe/London", cap=52305)),
    # https://en.wikipedia.org/wiki/City_Ground
    393: dict(name="Nottingham Forest", short="Nott'm Forest", abbrev="NFO",
              color="#C8102E",
              stadium=_stadium("City Ground", "Nottingham",
                               52.94000, -1.13278, "Europe/London", cap=30445)),
    # https://en.wikipedia.org/wiki/Stadium_of_Light
    # Newly promoted for 2026-27.
    366: dict(name="Sunderland", short="Sunderland", abbrev="SUN",
              color="#EB172B",
              stadium=_stadium("Stadium of Light", "Sunderland",
                               54.91443, -1.38817, "Europe/London", cap=49000)),
    # https://en.wikipedia.org/wiki/Tottenham_Hotspur_Stadium
    # Retractable PITCH tray for the NFL surface underneath. The roof
    # above the pitch is FIXED open — treat as open for weather purposes.
    367: dict(name="Tottenham Hotspur", short="Spurs", abbrev="TOT",
              color="#132257",
              stadium=_stadium("Tottenham Hotspur Stadium", "London",
                               51.60425, -0.06701, "Europe/London", cap=62850)),
}


def get_team(team_id: int):
    """Look up an EPL team by ESPN team ID. Returns None on miss."""
    if team_id is None:
        return None
    try:
        return EPL_TEAMS.get(int(team_id))
    except (TypeError, ValueError):
        return None


def get_stadium(team_id: int):
    """Return the stadium dict for a team, or None."""
    t = get_team(team_id)
    return t["stadium"] if t else None


# EOF-CANARY 2026-07-06-prem-build
