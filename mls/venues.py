"""mls.venues — the 30 MLS team venues.

Keyed by ESPN team ID (verified against ESPN's soccer/usa.1 teams endpoint
and scoreboard for the 2026 season on 2026-07-18). Each entry includes
stadium name, city, lat/lon (decimal degrees), timezone, roof_type,
capacity, nws_unsupported flag, and pitch orientation.

Coordinates are stadium center, accurate to ~0.001 degree (~100m).
Timezones use IANA names so ZoneInfo accepts them directly.

orientation_deg is the compass bearing (0-359°) of one goal — measured
looking down from above. It doesn't matter which of the two goals is
chosen; the pitch axis is symmetric. Used by the wind-arrow overlay in
the pitch diagram to display wind direction relative to the field
(mirror of the MLB home-plate-relative wind treatment). Values obtained
by Kevin via Google Maps satellite view on 2026-07-19.

roof_type values:
    "open"          — exposed (default for most MLS sites)
    "retractable"   — open or closed depending on weather
    "fixed_dome"    — permanent indoor (no MLS site currently)
"""

from __future__ import annotations


def _stadium(name: str, city: str, lat: float, lon: float,
             tz: str, *, cap: int | None = None,
             roof: str = "open", orientation: int = 0) -> dict:
    return {
        "name": name, "city": city, "lat": lat, "lon": lon,
        "timezone": tz, "roof_type": roof, "capacity": cap,
        "orientation_deg": orientation,
    }


MLS_TEAMS: dict[int, dict] = {
    # ── Eastern Conference ────────────────────────────────────────────
    18418: dict(name="Atlanta United FC", short="Atlanta", abbrev="ATL",
                conf="East", color="#80000A", nws_unsupported=False,
                stadium=_stadium("Mercedes-Benz Stadium", "Atlanta, GA",
                                 33.7553, -84.4006, "America/New_York",
                                 cap=42500, roof="retractable", orientation=90)),
    21300: dict(name="Charlotte FC", short="Charlotte", abbrev="CLT",
                conf="East", color="#1A85C8", nws_unsupported=False,
                stadium=_stadium("Bank of America Stadium", "Charlotte, NC",
                                 35.2258, -80.8528, "America/New_York",
                                 cap=38000, orientation=135)),
    182: dict(name="Chicago Fire FC", short="Chicago", abbrev="CHI",
              conf="East", color="#AF1E2D", nws_unsupported=False,
              stadium=_stadium("Soldier Field", "Chicago, IL",
                               41.8623, -87.6167, "America/Chicago",
                               cap=61500, orientation=0)),
    18267: dict(name="FC Cincinnati", short="Cincinnati", abbrev="CIN",
                conf="East", color="#FF6B35", nws_unsupported=False,
                stadium=_stadium("TQL Stadium", "Cincinnati, OH",
                                 39.1117, -84.5225, "America/New_York",
                                 cap=26000, orientation=0)),
    183: dict(name="Columbus Crew", short="Columbus", abbrev="CLB",
              conf="East", color="#FEDD00", nws_unsupported=False,
              stadium=_stadium("Lower.com Field", "Columbus, OH",
                               39.9683, -83.0175, "America/New_York",
                               cap=20011, orientation=0)),
    193: dict(name="D.C. United", short="D.C.", abbrev="DC",
             conf="East", color="#000000", nws_unsupported=False,
             stadium=_stadium("Audi Field", "Washington, DC",
                              38.8683, -77.0125, "America/New_York",
                              cap=20000, orientation=0)),
    20232: dict(name="Inter Miami CF", short="Miami", abbrev="MIA",
                conf="East", color="#F7B5CD", nws_unsupported=False,
                stadium=_stadium("Chase Stadium", "Fort Lauderdale, FL",
                                 26.1933, -80.1611, "America/New_York",
                                 cap=21550, orientation=0)),
    9720: dict(name="CF Montreal", short="Montreal", abbrev="MTL",
               conf="East", color="#0033A0", nws_unsupported=True,
               stadium=_stadium("Stade Saputo", "Montreal, QC",
                                45.5631, -73.5519, "America/Montreal",
                                cap=19619, orientation=157)),
    18986: dict(name="Nashville SC", short="Nashville", abbrev="NSH",
                conf="East", color="#FFB81C", nws_unsupported=False,
                stadium=_stadium("Geodis Park", "Nashville, TN",
                                 36.1303, -86.7656, "America/Chicago",
                                 cap=30000, orientation=157)),
    189: dict(name="New England Revolution", short="New England", abbrev="NE",
              conf="East", color="#DA291C", nws_unsupported=False,
              stadium=_stadium("Gillette Stadium", "Foxborough, MA",
                               42.0909, -71.2643, "America/New_York",
                               cap=20000, orientation=157)),
    17606: dict(name="New York City FC", short="NYCFC", abbrev="NYC",
                conf="East", color="#6CACE4", nws_unsupported=False,
                stadium=_stadium("Yankee Stadium", "Bronx, NY",
                                 40.8296, -73.9262, "America/New_York",
                                 cap=28743, orientation=45)),
    190: dict(name="New York Red Bulls", short="NY Red Bulls", abbrev="RBNY",
              conf="East", color="#ED1C24", nws_unsupported=False,
              stadium=_stadium("Red Bull Arena", "Harrison, NJ",
                               40.7374, -74.1502, "America/New_York",
                               cap=25000, orientation=0)),
    12011: dict(name="Orlando City SC", short="Orlando", abbrev="ORL",
                conf="East", color="#612B91", nws_unsupported=False,
                stadium=_stadium("Inter&Co Stadium", "Orlando, FL",
                                 28.5411, -81.3892, "America/New_York",
                                 cap=25500, orientation=0)),
    10739: dict(name="Philadelphia Union", short="Philadelphia", abbrev="PHI",
                conf="East", color="#002F65", nws_unsupported=False,
                stadium=_stadium("Subaru Park", "Chester, PA",
                                 39.8333, -75.3786, "America/New_York",
                                 cap=18500, orientation=0)),
    7318: dict(name="Toronto FC", short="Toronto", abbrev="TOR",
              conf="East", color="#B81137", nws_unsupported=True,
              stadium=_stadium("BMO Field", "Toronto, ON",
                               43.6332, -79.4185, "America/Toronto",
                               cap=30991, orientation=157)),
    # ── Western Conference ────────────────────────────────────────────
    20906: dict(name="Austin FC", short="Austin", abbrev="ATX",
                conf="West", color="#00B140", nws_unsupported=False,
                stadium=_stadium("Q2 Stadium", "Austin, TX",
                                 30.3877, -97.7194, "America/Chicago",
                                 cap=20738, orientation=157)),
    184: dict(name="Colorado Rapids", short="Colorado", abbrev="COL",
             conf="West", color="#960A2C", nws_unsupported=False,
             stadium=_stadium("Dick's Sporting Goods Park", "Commerce City, CO",
                              39.8056, -104.8917, "America/Denver",
                              cap=18061, orientation=0)),
    185: dict(name="FC Dallas", short="Dallas", abbrev="DAL",
             conf="West", color="#BF0A30", nws_unsupported=False,
             stadium=_stadium("Toyota Stadium", "Frisco, TX",
                              33.1553, -96.8350, "America/Chicago",
                              cap=20500, orientation=0)),
    6077: dict(name="Houston Dynamo FC", short="Houston", abbrev="HOU",
              conf="West", color="#F36F21", nws_unsupported=False,
              stadium=_stadium("Shell Energy Stadium", "Houston, TX",
                               29.7522, -95.3525, "America/Chicago",
                               cap=22039, orientation=45)),
    187: dict(name="LA Galaxy", short="LA Galaxy", abbrev="LA",
             conf="West", color="#00245D", nws_unsupported=False,
             stadium=_stadium("Dignity Health Sports Park", "Carson, CA",
                              33.8644, -118.2611, "America/Los_Angeles",
                              cap=27000, orientation=0)),
    18966: dict(name="Los Angeles FC", short="LAFC", abbrev="LAFC",
                conf="West", color="#C39E6D", nws_unsupported=False,
                stadium=_stadium("BMO Stadium", "Los Angeles, CA",
                                 34.0128, -118.2854, "America/Los_Angeles",
                                 cap=22000, orientation=0)),
    17362: dict(name="Minnesota United FC", short="Minnesota", abbrev="MIN",
                conf="West", color="#8CD2F4", nws_unsupported=False,
                stadium=_stadium("Allianz Field", "Saint Paul, MN",
                                 44.9531, -93.1653, "America/Chicago",
                                 cap=19619, orientation=0)),
    9723: dict(name="Portland Timbers", short="Portland", abbrev="POR",
               conf="West", color="#004812", nws_unsupported=False,
               stadium=_stadium("Providence Park", "Portland, OR",
                                45.5214, -122.6917, "America/Los_Angeles",
                                cap=25218, orientation=22)),
    4771: dict(name="Real Salt Lake", short="Salt Lake", abbrev="RSL",
               conf="West", color="#A50531", nws_unsupported=False,
               stadium=_stadium("America First Field", "Sandy, UT",
                                40.5832, -111.8932, "America/Denver",
                                cap=20213, orientation=0)),
    22529: dict(name="San Diego FC", short="San Diego", abbrev="SD",
                conf="West", color="#000000", nws_unsupported=False,
                stadium=_stadium("Snapdragon Stadium", "San Diego, CA",
                                 32.7831, -117.1196, "America/Los_Angeles",
                                 cap=32000, orientation=0)),
    191: dict(name="San Jose Earthquakes", short="San Jose", abbrev="SJ",
             conf="West", color="#0067B1", nws_unsupported=False,
             stadium=_stadium("PayPal Park", "San Jose, CA",
                              37.3508, -121.9253, "America/Los_Angeles",
                              cap=18000, orientation=45)),
    9726: dict(name="Seattle Sounders FC", short="Seattle", abbrev="SEA",
               conf="West", color="#236192", nws_unsupported=False,
               stadium=_stadium("Lumen Field", "Seattle, WA",
                                47.5952, -122.3316, "America/Los_Angeles",
                                cap=37722, orientation=0)),
    186: dict(name="Sporting Kansas City", short="Sporting KC", abbrev="SKC",
             conf="West", color="#93B1D7", nws_unsupported=False,
             stadium=_stadium("Children's Mercy Park", "Kansas City, KS",
                              39.1219, -94.8231, "America/Chicago",
                              cap=18467, orientation=45)),
    21812: dict(name="St. Louis City SC", short="St. Louis", abbrev="STL",
                conf="West", color="#AC162C", nws_unsupported=False,
                stadium=_stadium("Energizer Park", "St. Louis, MO",
                                 38.6313, -90.2128, "America/Chicago",
                                 cap=22500, orientation=22)),
    9727: dict(name="Vancouver Whitecaps FC", short="Vancouver", abbrev="VAN",
               conf="West", color="#00245D", nws_unsupported=True,
               stadium=_stadium("BC Place", "Vancouver, BC",
                                49.2768, -123.1119, "America/Vancouver",
                                cap=22120, roof="retractable", orientation=45)),
}


def get_team(team_id) -> dict | None:
    """Look up a team by ESPN team ID. Returns None if unknown."""
    try:
        return MLS_TEAMS.get(int(team_id))
    except (TypeError, ValueError):
        return None


def get_stadium(team_id) -> dict | None:
    """Convenience: stadium info for a team ID."""
    t = get_team(team_id)
    return t["stadium"] if t else None


def teams_by_conf(conf: str) -> list[dict]:
    """All teams in 'East' or 'West'."""
    return [t for t in MLS_TEAMS.values() if t["conf"] == conf]


# EOF-CANARY 2026-07-19-mls-orientation-added
