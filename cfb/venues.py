"""cfb.venues — FBS team and stadium directory.

Keyed by ESPN team ID (what ESPN's scoreboard endpoint returns in events).
Each team's stadium is its home venue; neutral-site games are handled at
the slate level (the schedule fetcher overrides venue when ESPN flags a
game as neutral, e.g. Texas vs OU at the Cotton Bowl).

Stadium fields:
  name:    Official stadium name
  city:    "City, ST" string (US only; FBS is all-US)
  lat/lon: For NWS forecast endpoint lookup
  tz:      IANA timezone for venue-local game time math
  roof:    "open" | "retractable" | "fixed_dome" | "fixed_canopy"
  cap:     Stadium capacity (informational; surfaced on detail pages)

Team fields:
  name:    Full team name
  short:   Short name for display headers
  abbrev:  3-4 char abbreviation (matches v14 mockup style)
  conf:    Conference code (SEC, B1G, ACC, B12, AAC, MWC, SBC, CUSA, MAC, IND)
  color:   Primary brand color hex (for any branded accents)

Coverage status:
  Power 4 (SEC, B1G, ACC, B12) + Independents + marquee G5: populated below.
  Remaining G5 (AAC, MWC, SBC, CUSA, MAC) to be added in subsequent sessions
  to reach the full 134-team FBS coverage.
"""

from __future__ import annotations


# ── Conference codes ──────────────────────────────────────────────────────
SEC  = "SEC"
B1G  = "B1G"
ACC  = "ACC"
B12  = "B12"
AAC  = "AAC"   # American Athletic
MWC  = "MWC"   # Mountain West
SBC  = "SBC"   # Sun Belt
CUSA = "CUSA"  # Conference USA
MAC  = "MAC"
IND  = "IND"   # Independents


# ── Roof types ────────────────────────────────────────────────────────────
ROOF_OPEN        = "open"          # No roof — weather fully exposed (most CFB)
ROOF_RETRACTABLE = "retractable"   # Can open/close (NRG Stadium, ATT Stadium for some bowls)
ROOF_FIXED_DOME  = "fixed_dome"    # Always indoors (Carrier Dome, Tropicana, Caesars Superdome)
ROOF_CANOPY      = "fixed_canopy"  # Partial cover, weather-affected (rare)


def _stadium(name, city, lat, lon, tz, roof=ROOF_OPEN, cap=None):
    """Helper to build a stadium dict cleanly."""
    return {
        "name": name, "city": city,
        "lat": lat, "lon": lon,
        "tz": tz, "roof": roof,
        "cap": cap,
    }


# ============================================================================
# FBS TEAMS — keyed by ESPN team ID
# ============================================================================
#
# Maintenance: add a team by appending a new entry below. ESPN team IDs
# can be found at site.api.espn.com/apis/site/v2/sports/football/college-
# football/teams. If an ID is wrong, the team logo on detail pages will
# break but everything else works (location comes from this file, not ESPN).

FBS_TEAMS: dict[int, dict] = {}


# ── SEC (16 teams) ────────────────────────────────────────────────────────
FBS_TEAMS.update({
    333: dict(name="Alabama Crimson Tide", short="Alabama", abbrev="BAMA",
              conf=SEC, color="#9E1B32",
              stadium=_stadium("Bryant-Denny Stadium", "Tuscaloosa, AL",
                               33.2083, -87.5503, "America/Chicago", cap=100077)),
    2:   dict(name="Auburn Tigers", short="Auburn", abbrev="AUB",
              conf=SEC, color="#0C2340",
              stadium=_stadium("Jordan-Hare Stadium", "Auburn, AL",
                               32.6020, -85.4912, "America/Chicago", cap=88043)),
    8:   dict(name="Arkansas Razorbacks", short="Arkansas", abbrev="ARK",
              conf=SEC, color="#9D2235",
              stadium=_stadium("Donald W. Reynolds Razorback Stadium", "Fayetteville, AR",
                               36.0682, -94.1789, "America/Chicago", cap=76212)),
    57:  dict(name="Florida Gators", short="Florida", abbrev="FLA",
              conf=SEC, color="#0021A5",
              stadium=_stadium("Ben Hill Griffin Stadium", "Gainesville, FL",
                               29.6498, -82.3486, "America/New_York", cap=88548)),
    61:  dict(name="Georgia Bulldogs", short="Georgia", abbrev="UGA",
              conf=SEC, color="#BA0C2F",
              stadium=_stadium("Sanford Stadium", "Athens, GA",
                               33.9495, -83.3733, "America/New_York", cap=92746)),
    96:  dict(name="Kentucky Wildcats", short="Kentucky", abbrev="UK",
              conf=SEC, color="#0033A0",
              stadium=_stadium("Kroger Field", "Lexington, KY",
                               38.0220, -84.5050, "America/New_York", cap=61000)),
    99:  dict(name="LSU Tigers", short="LSU", abbrev="LSU",
              conf=SEC, color="#461D7C",
              stadium=_stadium("Tiger Stadium", "Baton Rouge, LA",
                               30.4118, -91.1838, "America/Chicago", cap=102321)),
    142: dict(name="Missouri Tigers", short="Missouri", abbrev="MIZZ",
              conf=SEC, color="#F1B82D",
              stadium=_stadium("Faurot Field", "Columbia, MO",
                               38.9404, -92.3338, "America/Chicago", cap=62621)),
    145: dict(name="Ole Miss Rebels", short="Ole Miss", abbrev="MISS",
              conf=SEC, color="#14213D",
              stadium=_stadium("Vaught-Hemingway Stadium", "Oxford, MS",
                               34.3618, -89.5366, "America/Chicago", cap=64038)),
    201: dict(name="Oklahoma Sooners", short="Oklahoma", abbrev="OU",
              conf=SEC, color="#841617",
              stadium=_stadium("Gaylord Family Oklahoma Memorial Stadium", "Norman, OK",
                               35.2058, -97.4421, "America/Chicago", cap=80126)),
    245: dict(name="Texas A&M Aggies", short="Texas A&M", abbrev="TAMU",
              conf=SEC, color="#500000",
              stadium=_stadium("Kyle Field", "College Station, TX",
                               30.6100, -96.3400, "America/Chicago", cap=102733)),
    251: dict(name="Texas Longhorns", short="Texas", abbrev="TEX",
              conf=SEC, color="#BF5700",
              stadium=_stadium("Darrell K Royal-Texas Memorial Stadium", "Austin, TX",
                               30.2836, -97.7325, "America/Chicago", cap=100119)),
    344: dict(name="Mississippi State Bulldogs", short="Mississippi State", abbrev="MSST",
              conf=SEC, color="#660000",
              stadium=_stadium("Davis Wade Stadium", "Starkville, MS",
                               33.4566, -88.7935, "America/Chicago", cap=61337)),
    2579: dict(name="South Carolina Gamecocks", short="South Carolina", abbrev="SC",
              conf=SEC, color="#73000A",
              stadium=_stadium("Williams-Brice Stadium", "Columbia, SC",
                               33.9728, -81.0193, "America/New_York", cap=77559)),
    2633: dict(name="Tennessee Volunteers", short="Tennessee", abbrev="TENN",
              conf=SEC, color="#FF8200",
              stadium=_stadium("Neyland Stadium", "Knoxville, TN",
                               35.9550, -83.9250, "America/New_York", cap=101915)),
    238: dict(name="Vanderbilt Commodores", short="Vanderbilt", abbrev="VAN",
              conf=SEC, color="#000000",
              stadium=_stadium("FirstBank Stadium", "Nashville, TN",
                               36.1432, -86.8074, "America/Chicago", cap=40550)),
})


def get_team(team_id: int) -> dict | None:
    """Lookup a team's full info dict by ESPN team ID."""
    return FBS_TEAMS.get(team_id)


def get_stadium(team_id: int) -> dict | None:
    """Shortcut to a team's home stadium dict."""
    t = FBS_TEAMS.get(team_id)
    return t["stadium"] if t else None


def teams_by_conf(conf: str) -> list[dict]:
    """All teams in a given conference (SEC, B1G, ACC, etc.)."""
    return [t for t in FBS_TEAMS.values() if t["conf"] == conf]


def team_count() -> int:
    """How many teams currently populated. Should reach 134 at full coverage."""
    return len(FBS_TEAMS)


# ── Big Ten / B1G (18 teams) ──────────────────────────────────────────────
FBS_TEAMS.update({
    26:   dict(name="UCLA Bruins", short="UCLA", abbrev="UCLA",
              conf=B1G, color="#2D68C4",
              stadium=_stadium("Rose Bowl", "Pasadena, CA",
                               34.1613, -118.1676, "America/Los_Angeles", cap=88565)),
    30:   dict(name="USC Trojans", short="USC", abbrev="USC",
              conf=B1G, color="#990000",
              stadium=_stadium("Los Angeles Memorial Coliseum", "Los Angeles, CA",
                               34.0141, -118.2879, "America/Los_Angeles", cap=77500)),
    77:   dict(name="Northwestern Wildcats", short="Northwestern", abbrev="NW",
              conf=B1G, color="#4E2A84",
              stadium=_stadium("Ryan Field", "Evanston, IL",
                               42.0648, -87.6926, "America/Chicago", cap=47130)),
    84:   dict(name="Indiana Hoosiers", short="Indiana", abbrev="IND",
              conf=B1G, color="#990000",
              stadium=_stadium("Memorial Stadium", "Bloomington, IN",
                               39.1810, -86.5258, "America/New_York", cap=52656)),
    120:  dict(name="Maryland Terrapins", short="Maryland", abbrev="MD",
              conf=B1G, color="#E03A3E",
              stadium=_stadium("SECU Stadium", "College Park, MD",
                               38.9907, -76.9474, "America/New_York", cap=51802)),
    127:  dict(name="Michigan State Spartans", short="Michigan State", abbrev="MSU",
              conf=B1G, color="#18453B",
              stadium=_stadium("Spartan Stadium", "East Lansing, MI",
                               42.7282, -84.4847, "America/New_York", cap=75005)),
    130:  dict(name="Michigan Wolverines", short="Michigan", abbrev="MICH",
              conf=B1G, color="#00274C",
              stadium=_stadium("Michigan Stadium", "Ann Arbor, MI",
                               42.2658, -83.7487, "America/New_York", cap=107601)),
    135:  dict(name="Minnesota Golden Gophers", short="Minnesota", abbrev="MINN",
              conf=B1G, color="#7A0019",
              stadium=_stadium("Huntington Bank Stadium", "Minneapolis, MN",
                               44.9764, -93.2243, "America/Chicago", cap=50805)),
    158:  dict(name="Nebraska Cornhuskers", short="Nebraska", abbrev="NEB",
              conf=B1G, color="#E41C38",
              stadium=_stadium("Memorial Stadium", "Lincoln, NE",
                               40.8208, -96.7058, "America/Chicago", cap=85458)),
    164:  dict(name="Rutgers Scarlet Knights", short="Rutgers", abbrev="RUT",
              conf=B1G, color="#CC0033",
              stadium=_stadium("SHI Stadium", "Piscataway, NJ",
                               40.5135, -74.4655, "America/New_York", cap=52454)),
    194:  dict(name="Ohio State Buckeyes", short="Ohio State", abbrev="OSU",
              conf=B1G, color="#BB0000",
              stadium=_stadium("Ohio Stadium", "Columbus, OH",
                               40.0017, -83.0197, "America/New_York", cap=102780)),
    213:  dict(name="Penn State Nittany Lions", short="Penn State", abbrev="PSU",
              conf=B1G, color="#041E42",
              stadium=_stadium("Beaver Stadium", "State College, PA",
                               40.8122, -77.8562, "America/New_York", cap=106572)),
    264:  dict(name="Washington Huskies", short="Washington", abbrev="UW",
              conf=B1G, color="#4B2E83",
              stadium=_stadium("Husky Stadium", "Seattle, WA",
                               47.6502, -122.3019, "America/Los_Angeles", cap=70083)),
    275:  dict(name="Wisconsin Badgers", short="Wisconsin", abbrev="WIS",
              conf=B1G, color="#C5050C",
              stadium=_stadium("Camp Randall Stadium", "Madison, WI",
                               43.0696, -89.4124, "America/Chicago", cap=80321)),
    356:  dict(name="Illinois Fighting Illini", short="Illinois", abbrev="ILL",
              conf=B1G, color="#13294B",
              stadium=_stadium("Memorial Stadium", "Champaign, IL",
                               40.0993, -88.2356, "America/Chicago", cap=60670)),
    2294: dict(name="Iowa Hawkeyes", short="Iowa", abbrev="IOWA",
              conf=B1G, color="#FFCD00",
              stadium=_stadium("Kinnick Stadium", "Iowa City, IA",
                               41.6586, -91.5512, "America/Chicago", cap=69250)),
    2483: dict(name="Oregon Ducks", short="Oregon", abbrev="ORE",
              conf=B1G, color="#154733",
              stadium=_stadium("Autzen Stadium", "Eugene, OR",
                               44.0583, -123.0682, "America/Los_Angeles", cap=54000)),
    2509: dict(name="Purdue Boilermakers", short="Purdue", abbrev="PUR",
              conf=B1G, color="#CEB888",
              stadium=_stadium("Ross-Ade Stadium", "West Lafayette, IN",
                               40.4347, -86.9182, "America/Indiana/Indianapolis", cap=57236)),
})


# ── ACC (17 teams) ────────────────────────────────────────────────────────
FBS_TEAMS.update({
    24:   dict(name="Stanford Cardinal", short="Stanford", abbrev="STAN",
              conf=ACC, color="#8C1515",
              stadium=_stadium("Stanford Stadium", "Stanford, CA",
                               37.4347, -122.1610, "America/Los_Angeles", cap=50424)),
    25:   dict(name="California Golden Bears", short="Cal", abbrev="CAL",
              conf=ACC, color="#003262",
              stadium=_stadium("California Memorial Stadium", "Berkeley, CA",
                               37.8716, -122.2509, "America/Los_Angeles", cap=63186)),
    52:   dict(name="Florida State Seminoles", short="Florida State", abbrev="FSU",
              conf=ACC, color="#782F40",
              stadium=_stadium("Doak Campbell Stadium", "Tallahassee, FL",
                               30.4380, -84.3047, "America/New_York", cap=79560)),
    59:   dict(name="Georgia Tech Yellow Jackets", short="Georgia Tech", abbrev="GT",
              conf=ACC, color="#B3A369",
              stadium=_stadium("Bobby Dodd Stadium", "Atlanta, GA",
                               33.7724, -84.3925, "America/New_York", cap=55000)),
    97:   dict(name="Louisville Cardinals", short="Louisville", abbrev="LOU",
              conf=ACC, color="#AD0000",
              stadium=_stadium("L&N Federal Credit Union Stadium", "Louisville, KY",
                               38.2065, -85.7572, "America/New_York", cap=60800)),
    103:  dict(name="Boston College Eagles", short="Boston College", abbrev="BC",
              conf=ACC, color="#8B0000",
              stadium=_stadium("Alumni Stadium", "Chestnut Hill, MA",
                               42.3354, -71.1665, "America/New_York", cap=44500)),
    150:  dict(name="Duke Blue Devils", short="Duke", abbrev="DUKE",
              conf=ACC, color="#003087",
              stadium=_stadium("Wallace Wade Stadium", "Durham, NC",
                               36.0007, -78.9412, "America/New_York", cap=40004)),
    152:  dict(name="NC State Wolfpack", short="NC State", abbrev="NCST",
              conf=ACC, color="#CC0000",
              stadium=_stadium("Carter-Finley Stadium", "Raleigh, NC",
                               35.8011, -78.7194, "America/New_York", cap=57583)),
    153:  dict(name="North Carolina Tar Heels", short="North Carolina", abbrev="UNC",
              conf=ACC, color="#7BAFD4",
              stadium=_stadium("Kenan Memorial Stadium", "Chapel Hill, NC",
                               35.9069, -79.0476, "America/New_York", cap=50500)),
    154:  dict(name="Wake Forest Demon Deacons", short="Wake Forest", abbrev="WF",
              conf=ACC, color="#9E7E38",
              stadium=_stadium("Allegacy Federal Credit Union Stadium", "Winston-Salem, NC",
                               36.1322, -80.2540, "America/New_York", cap=31500)),
    183:  dict(name="Syracuse Orange", short="Syracuse", abbrev="SYR",
              conf=ACC, color="#F76900",
              stadium=_stadium("JMA Wireless Dome", "Syracuse, NY",
                               43.0364, -76.1361, "America/New_York", roof=ROOF_FIXED_DOME, cap=49250)),
    221:  dict(name="Pittsburgh Panthers", short="Pittsburgh", abbrev="PITT",
              conf=ACC, color="#003594",
              stadium=_stadium("Acrisure Stadium", "Pittsburgh, PA",
                               40.4467, -80.0157, "America/New_York", cap=68400)),
    228:  dict(name="Clemson Tigers", short="Clemson", abbrev="CLEM",
              conf=ACC, color="#F66733",
              stadium=_stadium("Memorial Stadium", "Clemson, SC",
                               34.6787, -82.8430, "America/New_York", cap=81500)),
    258:  dict(name="Virginia Cavaliers", short="Virginia", abbrev="UVA",
              conf=ACC, color="#232D4B",
              stadium=_stadium("Scott Stadium", "Charlottesville, VA",
                               38.0316, -78.5128, "America/New_York", cap=61500)),
    259:  dict(name="Virginia Tech Hokies", short="Virginia Tech", abbrev="VT",
              conf=ACC, color="#630031",
              stadium=_stadium("Lane Stadium", "Blacksburg, VA",
                               37.2197, -80.4180, "America/New_York", cap=65632)),
    2390: dict(name="Miami Hurricanes", short="Miami", abbrev="MIA",
              conf=ACC, color="#F47321",
              stadium=_stadium("Hard Rock Stadium", "Miami Gardens, FL",
                               25.9580, -80.2389, "America/New_York", cap=65326)),
    2567: dict(name="SMU Mustangs", short="SMU", abbrev="SMU",
              conf=ACC, color="#0033A0",
              stadium=_stadium("Gerald J. Ford Stadium", "Dallas, TX",
                               32.8403, -96.7822, "America/Chicago", cap=32000)),
})


# ── Big 12 (16 teams) ─────────────────────────────────────────────────────
FBS_TEAMS.update({
    9:    dict(name="Arizona State Sun Devils", short="Arizona State", abbrev="ASU",
              conf=B12, color="#8C1D40",
              stadium=_stadium("Mountain America Stadium", "Tempe, AZ",
                               33.4264, -111.9325, "America/Phoenix", cap=53599)),
    12:   dict(name="Arizona Wildcats", short="Arizona", abbrev="UA",
              conf=B12, color="#AB0520",
              stadium=_stadium("Arizona Stadium", "Tucson, AZ",
                               32.2298, -110.9491, "America/Phoenix", cap=50782)),
    38:   dict(name="Colorado Buffaloes", short="Colorado", abbrev="COLO",
              conf=B12, color="#CFB87C",
              stadium=_stadium("Folsom Field", "Boulder, CO",
                               40.0075, -105.2670, "America/Denver", cap=50183)),
    66:   dict(name="Iowa State Cyclones", short="Iowa State", abbrev="ISU",
              conf=B12, color="#C8102E",
              stadium=_stadium("Jack Trice Stadium", "Ames, IA",
                               42.0145, -93.6357, "America/Chicago", cap=61500)),
    197:  dict(name="Oklahoma State Cowboys", short="Oklahoma State", abbrev="OKST",
              conf=B12, color="#FF7300",
              stadium=_stadium("Boone Pickens Stadium", "Stillwater, OK",
                               36.1255, -97.0664, "America/Chicago", cap=55509)),
    239:  dict(name="Baylor Bears", short="Baylor", abbrev="BAY",
              conf=B12, color="#003015",
              stadium=_stadium("McLane Stadium", "Waco, TX",
                               31.5582, -97.1156, "America/Chicago", cap=45140)),
    248:  dict(name="Houston Cougars", short="Houston", abbrev="HOU",
              conf=B12, color="#C8102E",
              stadium=_stadium("TDECU Stadium", "Houston, TX",
                               29.7222, -95.3491, "America/Chicago", cap=40000)),
    252:  dict(name="BYU Cougars", short="BYU", abbrev="BYU",
              conf=B12, color="#002E5D",
              stadium=_stadium("LaVell Edwards Stadium", "Provo, UT",
                               40.2575, -111.6542, "America/Denver", cap=63470)),
    254:  dict(name="Utah Utes", short="Utah", abbrev="UTAH",
              conf=B12, color="#CC0000",
              stadium=_stadium("Rice-Eccles Stadium", "Salt Lake City, UT",
                               40.7608, -111.8484, "America/Denver", cap=51444)),
    277:  dict(name="West Virginia Mountaineers", short="West Virginia", abbrev="WVU",
              conf=B12, color="#002855",
              stadium=_stadium("Milan Puskar Stadium", "Morgantown, WV",
                               39.6483, -79.9540, "America/New_York", cap=60000)),
    2116: dict(name="UCF Knights", short="UCF", abbrev="UCF",
              conf=B12, color="#000000",
              stadium=_stadium("FBC Mortgage Stadium", "Orlando, FL",
                               28.6079, -81.1929, "America/New_York", cap=44206)),
    2132: dict(name="Cincinnati Bearcats", short="Cincinnati", abbrev="CIN",
              conf=B12, color="#E00122",
              stadium=_stadium("Nippert Stadium", "Cincinnati, OH",
                               39.1316, -84.5168, "America/New_York", cap=40000)),
    2305: dict(name="Kansas Jayhawks", short="Kansas", abbrev="KU",
              conf=B12, color="#0051BA",
              stadium=_stadium("David Booth Kansas Memorial Stadium", "Lawrence, KS",
                               38.9633, -95.2456, "America/Chicago", cap=47233)),
    2306: dict(name="Kansas State Wildcats", short="Kansas State", abbrev="KSU",
              conf=B12, color="#512888",
              stadium=_stadium("Bill Snyder Family Stadium", "Manhattan, KS",
                               39.2018, -96.5942, "America/Chicago", cap=50000)),
    2628: dict(name="TCU Horned Frogs", short="TCU", abbrev="TCU",
              conf=B12, color="#4D1979",
              stadium=_stadium("Amon G. Carter Stadium", "Fort Worth, TX",
                               32.7100, -97.3686, "America/Chicago", cap=45000)),
    2641: dict(name="Texas Tech Red Raiders", short="Texas Tech", abbrev="TTU",
              conf=B12, color="#CC0000",
              stadium=_stadium("Jones AT&T Stadium", "Lubbock, TX",
                               33.5912, -101.8729, "America/Chicago", cap=60454)),
})


# ── Independents + Notre Dame (4 teams) ───────────────────────────────────
FBS_TEAMS.update({
    41:   dict(name="UConn Huskies", short="UConn", abbrev="CONN",
              conf=IND, color="#000E2F",
              stadium=_stadium("Pratt & Whitney Stadium at Rentschler Field", "East Hartford, CT",
                               41.7591, -72.6092, "America/New_York", cap=40000)),
    87:   dict(name="Notre Dame Fighting Irish", short="Notre Dame", abbrev="ND",
              conf=IND, color="#0C2340",
              stadium=_stadium("Notre Dame Stadium", "Notre Dame, IN",
                               41.6985, -86.2336, "America/New_York", cap=77622)),
    113:  dict(name="UMass Minutemen", short="UMass", abbrev="MASS",
              conf=IND, color="#881C1C",
              stadium=_stadium("McGuirk Alumni Stadium", "Amherst, MA",
                               42.3940, -72.5290, "America/New_York", cap=17000)),
    349:  dict(name="Army Black Knights", short="Army", abbrev="ARMY",
              conf=IND, color="#000000",
              stadium=_stadium("Michie Stadium", "West Point, NY",
                               41.3760, -73.9582, "America/New_York", cap=38000)),
})
