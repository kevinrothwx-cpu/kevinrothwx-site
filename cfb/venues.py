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


# ============================================================================
# G5 CONFERENCES — Sun Belt, Mountain West, American, Conference USA, MAC
# Added 2026-07-04 to complete FBS coverage (was P4 + IND only prior).
#
# Sources: each entry has a Wikipedia URL comment above it. Coordinates from
# Wikipedia stadium infoboxes (5-decimal precision), capacity from current
# 2025-season Wikipedia figures, roof type verified. ESPN team IDs cross-
# checked against site.api.espn.com team endpoints.
#
# Dome/roof entries in G5:
#   UTSA at Alamodome (fixed_dome) — indoor, no weather impact
#   UNLV at Allegiant Stadium (fixed_dome, shared with Raiders)
# ============================================================================


# ── Sun Belt (14 teams) ───────────────────────────────────────────────────
FBS_TEAMS.update({
    # https://en.wikipedia.org/wiki/Joan_C._Edwards_Stadium
    276: dict(name="Marshall Thundering Herd", short="Marshall", abbrev="MRSH",
              conf=SBC, color="#00B140",
              stadium=_stadium("Joan C. Edwards Stadium", "Huntington, WV",
                               38.42500, -82.42083, "America/New_York", cap=30475)),
    # https://en.wikipedia.org/wiki/Kidd_Brewer_Stadium
    2026: dict(name="Appalachian State Mountaineers", short="App State", abbrev="APP",
               conf=SBC, color="#FFCD00",
               stadium=_stadium("Kidd Brewer Stadium", "Boone, NC",
                                36.21167, -81.68556, "America/New_York", cap=30000)),
    # https://en.wikipedia.org/wiki/Bridgeforth_Stadium
    256: dict(name="James Madison Dukes", short="James Madison", abbrev="JMU",
             conf=SBC, color="#450084",
             stadium=_stadium("Bridgeforth Stadium", "Harrisonburg, VA",
                              38.43528, -78.87306, "America/New_York", cap=24877)),
    # https://en.wikipedia.org/wiki/Brooks_Stadium
    324: dict(name="Coastal Carolina Chanticleers", short="Coastal Carolina", abbrev="CCU",
             conf=SBC, color="#006F71",
             stadium=_stadium("Brooks Stadium", "Conway, SC",
                              33.79290, -79.01750, "America/New_York", cap=21000)),
    # https://en.wikipedia.org/wiki/Paulson_Stadium
    290: dict(name="Georgia Southern Eagles", short="Georgia Southern", abbrev="GASO",
             conf=SBC, color="#041E42",
             stadium=_stadium("Allen E. Paulson Stadium", "Statesboro, GA",
                              32.41216, -81.78314, "America/New_York", cap=25000)),
    # https://en.wikipedia.org/wiki/Center_Parc_Stadium
    2247: dict(name="Georgia State Panthers", short="Georgia State", abbrev="GAST",
               conf=SBC, color="#0039A6",
               stadium=_stadium("Center Parc Stadium", "Atlanta, GA",
                                33.73528, -84.38944, "America/New_York", cap=24333)),
    # https://en.wikipedia.org/wiki/Cajun_Field
    309: dict(name="Louisiana Ragin' Cajuns", short="Louisiana", abbrev="ULL",
             conf=SBC, color="#CE181E",
             stadium=_stadium("Cajun Field", "Lafayette, LA",
                              30.21583, -92.04194, "America/Chicago", cap=30000)),
    # https://en.wikipedia.org/wiki/Malone_Stadium
    2433: dict(name="Louisiana-Monroe Warhawks", short="ULM", abbrev="ULM",
               conf=SBC, color="#840029",
               stadium=_stadium("JPS Field at Malone Stadium", "Monroe, LA",
                                32.53083, -92.06583, "America/Chicago", cap=27617)),
    # https://en.wikipedia.org/wiki/S.B._Ballard_Stadium
    295: dict(name="Old Dominion Monarchs", short="Old Dominion", abbrev="ODU",
             conf=SBC, color="#003768",
             stadium=_stadium("S.B. Ballard Stadium", "Norfolk, VA",
                              36.88890, -76.30488, "America/New_York", cap=21944)),
    # https://en.wikipedia.org/wiki/Hancock_Whitney_Stadium
    6: dict(name="South Alabama Jaguars", short="South Alabama", abbrev="USA",
            conf=SBC, color="#00205B",
            stadium=_stadium("Hancock Whitney Stadium", "Mobile, AL",
                             30.69690, -88.19201, "America/Chicago", cap=25450)),
    # https://en.wikipedia.org/wiki/M._M._Roberts_Stadium
    2572: dict(name="Southern Miss Golden Eagles", short="Southern Miss", abbrev="USM",
               conf=SBC, color="#FFC72C",
               stadium=_stadium("M.M. Roberts Stadium", "Hattiesburg, MS",
                                31.32889, -89.33139, "America/Chicago", cap=36000)),
    # https://en.wikipedia.org/wiki/UFCU_Stadium
    326: dict(name="Texas State Bobcats", short="Texas State", abbrev="TXST",
             conf=SBC, color="#501214",
             stadium=_stadium("UFCU Stadium", "San Marcos, TX",
                              29.89111, -97.92556, "America/Chicago", cap=28388)),
    # https://en.wikipedia.org/wiki/Veterans_Memorial_Stadium_(Troy_University)
    2653: dict(name="Troy Trojans", short="Troy", abbrev="TROY",
               conf=SBC, color="#862633",
               stadium=_stadium("Veterans Memorial Stadium", "Troy, AL",
                                31.79944, -85.95194, "America/Chicago", cap=30470)),
    # https://en.wikipedia.org/wiki/Centennial_Bank_Stadium
    2032: dict(name="Arkansas State Red Wolves", short="Arkansas State", abbrev="ARST",
               conf=SBC, color="#CC092F",
               stadium=_stadium("Centennial Bank Stadium", "Jonesboro, AR",
                                35.84889, -90.66722, "America/Chicago", cap=30406)),
})


# ── Mountain West (12 teams) ──────────────────────────────────────────────
FBS_TEAMS.update({
    # https://en.wikipedia.org/wiki/Falcon_Stadium — elevation 6,621 ft
    2005: dict(name="Air Force Falcons", short="Air Force", abbrev="AF",
               conf=MWC, color="#003087",
               stadium=_stadium("Falcon Stadium", "Colorado Springs, CO",
                                38.99667, -104.84359, "America/Denver", cap=46692)),
    # https://en.wikipedia.org/wiki/Albertsons_Stadium — famous blue turf
    68: dict(name="Boise State Broncos", short="Boise State", abbrev="BSU",
            conf=MWC, color="#D64309",
            stadium=_stadium("Albertsons Stadium", "Boise, ID",
                             43.60306, -116.19611, "America/Boise", cap=36387)),
    # https://en.wikipedia.org/wiki/Canvas_Stadium
    36: dict(name="Colorado State Rams", short="Colorado State", abbrev="CSU",
            conf=MWC, color="#1E4D2B",
            stadium=_stadium("Canvas Stadium", "Fort Collins, CO",
                             40.57000, -105.08850, "America/Denver", cap=36500)),
    # https://en.wikipedia.org/wiki/Valley_Children%27s_Stadium
    278: dict(name="Fresno State Bulldogs", short="Fresno State", abbrev="FRES",
             conf=MWC, color="#B1102B",
             stadium=_stadium("Valley Children's Stadium", "Fresno, CA",
                              36.81440, -119.75800, "America/Los_Angeles", cap=40727)),
    # https://en.wikipedia.org/wiki/Clarence_T._C._Ching_Athletics_Complex — moved from Aloha Stadium 2021
    62: dict(name="Hawai'i Rainbow Warriors", short="Hawai'i", abbrev="HAW",
            conf=MWC, color="#024731",
            stadium=_stadium("Clarence T.C. Ching Athletics Complex", "Honolulu, HI",
                             21.29400, -157.81800, "Pacific/Honolulu", cap=15194)),
    # https://en.wikipedia.org/wiki/Mackay_Stadium
    2440: dict(name="Nevada Wolf Pack", short="Nevada", abbrev="NEV",
               conf=MWC, color="#003366",
               stadium=_stadium("Mackay Stadium", "Reno, NV",
                                39.54681, -119.81750, "America/Los_Angeles", cap=27000)),
    # https://en.wikipedia.org/wiki/University_Stadium_(Albuquerque)
    167: dict(name="New Mexico Lobos", short="New Mexico", abbrev="UNM",
             conf=MWC, color="#BA0C2F",
             stadium=_stadium("University Stadium", "Albuquerque, NM",
                              35.06689, -106.62831, "America/Denver", cap=39224)),
    # https://en.wikipedia.org/wiki/Snapdragon_Stadium — new SDSU home 2022+
    21: dict(name="San Diego State Aztecs", short="San Diego State", abbrev="SDSU",
            conf=MWC, color="#A6192E",
            stadium=_stadium("Snapdragon Stadium", "San Diego, CA",
                             32.78444, -117.12283, "America/Los_Angeles", cap=35000)),
    # https://en.wikipedia.org/wiki/CEFCU_Stadium
    23: dict(name="San José State Spartans", short="San Jose State", abbrev="SJSU",
            conf=MWC, color="#0055A2",
            stadium=_stadium("CEFCU Stadium", "San Jose, CA",
                             37.31972, -121.86833, "America/Los_Angeles", cap=30456)),
    # https://en.wikipedia.org/wiki/Allegiant_Stadium — FIXED DOME shared with Raiders
    2439: dict(name="UNLV Rebels", short="UNLV", abbrev="UNLV",
               conf=MWC, color="#CF0A2C",
               stadium=_stadium("Allegiant Stadium", "Paradise, NV",
                                36.09079, -115.18395, "America/Los_Angeles",
                                roof=ROOF_FIXED_DOME, cap=65000)),
    # https://en.wikipedia.org/wiki/Maverik_Stadium
    328: dict(name="Utah State Aggies", short="Utah State", abbrev="USU",
             conf=MWC, color="#00263A",
             stadium=_stadium("Maverik Stadium", "Logan, UT",
                              41.75169, -111.81169, "America/Denver", cap=25513)),
    # https://en.wikipedia.org/wiki/War_Memorial_Stadium_(Laramie,_Wyoming) — 7,220 ft, highest FBS
    2751: dict(name="Wyoming Cowboys", short="Wyoming", abbrev="WYO",
               conf=MWC, color="#FFC425",
               stadium=_stadium("War Memorial Stadium", "Laramie, WY",
                                41.30700, -105.56770, "America/Denver", cap=29181)),
})


# ── American Conference / AAC (14 teams) ──────────────────────────────────
# Army was previously in FBS_TEAMS under IND — its conf is patched to AAC
# below (Army joined AAC in 2024). Only 13 new AAC entries added here.
FBS_TEAMS.update({
    # https://en.wikipedia.org/wiki/Jerry_Richardson_Stadium
    2429: dict(name="Charlotte 49ers", short="Charlotte", abbrev="CHAR",
               conf=AAC, color="#046A38",
               stadium=_stadium("Jerry Richardson Stadium", "Charlotte, NC",
                                35.31056, -80.74028, "America/New_York", cap=15314)),
    # https://en.wikipedia.org/wiki/Dowdy%E2%80%93Ficklen_Stadium
    151: dict(name="East Carolina Pirates", short="ECU", abbrev="ECU",
             conf=AAC, color="#592A8A",
             stadium=_stadium("Dowdy-Ficklen Stadium", "Greenville, NC",
                              35.59117, -77.35917, "America/New_York", cap=50000)),
    # https://en.wikipedia.org/wiki/Flagler_Credit_Union_Stadium — renamed Dec 2024
    2226: dict(name="Florida Atlantic Owls", short="FAU", abbrev="FAU",
               conf=AAC, color="#003366",
               stadium=_stadium("Flagler Credit Union Stadium", "Boca Raton, FL",
                                26.37528, -80.10028, "America/New_York", cap=30000)),
    # https://en.wikipedia.org/wiki/Simmons_Bank_Liberty_Stadium
    235: dict(name="Memphis Tigers", short="Memphis", abbrev="MEM",
             conf=AAC, color="#003087",
             stadium=_stadium("Simmons Bank Liberty Stadium", "Memphis, TN",
                              35.12111, -89.97750, "America/Chicago", cap=50000)),
    # https://en.wikipedia.org/wiki/Navy%E2%80%93Marine_Corps_Memorial_Stadium
    2426: dict(name="Navy Midshipmen", short="Navy", abbrev="NAVY",
               conf=AAC, color="#00205B",
               stadium=_stadium("Navy-Marine Corps Memorial Stadium", "Annapolis, MD",
                                38.98500, -76.50694, "America/New_York", cap=34000)),
    # https://en.wikipedia.org/wiki/DATCU_Stadium — renamed 2022
    249: dict(name="North Texas Mean Green", short="North Texas", abbrev="UNT",
             conf=AAC, color="#00853E",
             stadium=_stadium("DATCU Stadium", "Denton, TX",
                              33.20361, -97.15944, "America/Chicago", cap=30100)),
    # https://en.wikipedia.org/wiki/Rice_Stadium_(Rice_University)
    242: dict(name="Rice Owls", short="Rice", abbrev="RICE",
             conf=AAC, color="#00205B",
             stadium=_stadium("Rice Stadium", "Houston, TX",
                              29.71639, -95.40917, "America/Chicago", cap=47000)),
    # https://en.wikipedia.org/wiki/Raymond_James_Stadium — USF shares w/ Bucs, on-campus stadium opens 2027
    58: dict(name="South Florida Bulls", short="USF", abbrev="USF",
            conf=AAC, color="#006747",
            stadium=_stadium("Raymond James Stadium", "Tampa, FL",
                             27.97583, -82.50333, "America/New_York", cap=69218)),
    # https://en.wikipedia.org/wiki/Lincoln_Financial_Field — Temple shares w/ Eagles
    218: dict(name="Temple Owls", short="Temple", abbrev="TEM",
             conf=AAC, color="#9D2235",
             stadium=_stadium("Lincoln Financial Field", "Philadelphia, PA",
                              39.90083, -75.16778, "America/New_York", cap=67594)),
    # https://en.wikipedia.org/wiki/Yulman_Stadium
    2655: dict(name="Tulane Green Wave", short="Tulane", abbrev="TUL",
               conf=AAC, color="#006747",
               stadium=_stadium("Yulman Stadium", "New Orleans, LA",
                                29.94482, -90.11682, "America/Chicago", cap=30000)),
    # https://en.wikipedia.org/wiki/Skelly_Field_at_H._A._Chapman_Stadium
    202: dict(name="Tulsa Golden Hurricane", short="Tulsa", abbrev="TLSA",
             conf=AAC, color="#002D72",
             stadium=_stadium("Skelly Field at H.A. Chapman Stadium", "Tulsa, OK",
                              36.14861, -95.94389, "America/Chicago", cap=30000)),
    # https://en.wikipedia.org/wiki/Protective_Stadium — new UAB home 2021+
    5: dict(name="UAB Blazers", short="UAB", abbrev="UAB",
            conf=AAC, color="#1C5420",
            stadium=_stadium("Protective Stadium", "Birmingham, AL",
                             33.52778, -86.80917, "America/Chicago", cap=47100)),
    # https://en.wikipedia.org/wiki/Alamodome — FIXED DOME
    2636: dict(name="UTSA Roadrunners", short="UTSA", abbrev="UTSA",
               conf=AAC, color="#0C2340",
               stadium=_stadium("Alamodome", "San Antonio, TX",
                                29.41694, -98.47889, "America/Chicago",
                                roof=ROOF_FIXED_DOME, cap=64000)),
})


# ── Conference USA (12 teams) ─────────────────────────────────────────────
FBS_TEAMS.update({
    # https://en.wikipedia.org/wiki/Pitbull_Stadium — renamed 2024
    2229: dict(name="FIU Panthers", short="FIU", abbrev="FIU",
               conf=CUSA, color="#081E3F",
               stadium=_stadium("Pitbull Stadium", "Miami, FL",
                                25.75250, -80.37778, "America/New_York", cap=20000)),
    # https://en.wikipedia.org/wiki/AmFirst_Stadium — renamed 2024
    55: dict(name="Jacksonville State Gamecocks", short="Jax State", abbrev="JVST",
             conf=CUSA, color="#CC0000",
             stadium=_stadium("Burgess-Snow Field at AmFirst Stadium", "Jacksonville, AL",
                              33.82028, -85.76639, "America/Chicago", cap=22500)),
    # https://en.wikipedia.org/wiki/Fifth_Third_Stadium
    338: dict(name="Kennesaw State Owls", short="Kennesaw State", abbrev="KENN",
             conf=CUSA, color="#FDBB30",
             stadium=_stadium("Fifth Third Stadium", "Kennesaw, GA",
                              34.02900, -84.56760, "America/New_York", cap=10200)),
    # https://en.wikipedia.org/wiki/Williams_Stadium
    2335: dict(name="Liberty Flames", short="Liberty", abbrev="LIB",
               conf=CUSA, color="#002D62",
               stadium=_stadium("Williams Stadium", "Lynchburg, VA",
                                37.35400, -79.17500, "America/New_York", cap=25000)),
    # https://en.wikipedia.org/wiki/Joe_Aillet_Stadium
    2348: dict(name="Louisiana Tech Bulldogs", short="Louisiana Tech", abbrev="LT",
               conf=CUSA, color="#002F8B",
               stadium=_stadium("Joe Aillet Stadium", "Ruston, LA",
                                32.53202, -92.65590, "America/Chicago", cap=28562)),
    # https://en.wikipedia.org/wiki/Johnny_%22Red%22_Floyd_Stadium
    2393: dict(name="Middle Tennessee Blue Raiders", short="Middle Tennessee", abbrev="MTSU",
               conf=CUSA, color="#0066CC",
               stadium=_stadium('Johnny "Red" Floyd Stadium', "Murfreesboro, TN",
                                35.85051, -86.36822, "America/Chicago", cap=27303)),
    # https://en.wikipedia.org/wiki/Aggie_Memorial_Stadium
    166: dict(name="New Mexico State Aggies", short="New Mexico State", abbrev="NMSU",
             conf=CUSA, color="#861F41",
             stadium=_stadium("Aggie Memorial Stadium", "Las Cruces, NM",
                              32.27972, -106.74111, "America/Denver", cap=28853)),
    # https://en.wikipedia.org/wiki/Bowers_Stadium — 2025 season played at Shell Energy Stadium (renovation)
    2534: dict(name="Sam Houston Bearkats", short="Sam Houston", abbrev="SHSU",
               conf=CUSA, color="#FE5100",
               stadium=_stadium("Elliott T. Bowers Stadium", "Huntsville, TX",
                                30.71389, -95.54167, "America/Chicago", cap=14000)),
    # https://en.wikipedia.org/wiki/Sun_Bowl_(stadium) — 3,900 ft elevation
    2638: dict(name="UTEP Miners", short="UTEP", abbrev="UTEP",
               conf=CUSA, color="#041E42",
               stadium=_stadium("Sun Bowl", "El Paso, TX",
                                31.77306, -106.50806, "America/Denver", cap=51500)),
    # https://en.wikipedia.org/wiki/Houchens_Industries%E2%80%93L._T._Smith_Stadium
    98: dict(name="Western Kentucky Hilltoppers", short="Western Kentucky", abbrev="WKU",
            conf=CUSA, color="#C60C30",
            stadium=_stadium("Houchens Industries-L.T. Smith Stadium", "Bowling Green, KY",
                             36.98472, -86.45944, "America/Chicago", cap=22113)),
    # https://en.wikipedia.org/wiki/Delaware_Stadium — Delaware joined CUSA July 2025
    48: dict(name="Delaware Blue Hens", short="Delaware", abbrev="DEL",
            conf=CUSA, color="#00539F",
            stadium=_stadium("Delaware Stadium", "Newark, DE",
                             39.66170, -75.74880, "America/New_York", cap=18500)),
    # https://en.wikipedia.org/wiki/Robert_W._Plaster_Stadium — Missouri State joined CUSA July 2025
    2623: dict(name="Missouri State Bears", short="Missouri State", abbrev="MOST",
               conf=CUSA, color="#5E0009",
               stadium=_stadium("Robert W. Plaster Stadium", "Springfield, MO",
                                37.19778, -93.27972, "America/Chicago", cap=17500)),
})


# ── MAC / Mid-American (13 teams) ─────────────────────────────────────────
# UMass was previously in FBS_TEAMS under IND — its conf is patched to MAC
# below (UMass joined MAC in 2025). Only 12 new MAC entries added here.
FBS_TEAMS.update({
    # https://en.wikipedia.org/wiki/InfoCision_Stadium%E2%80%93Summa_Field
    2006: dict(name="Akron Zips", short="Akron", abbrev="AKR",
               conf=MAC, color="#041E42",
               stadium=_stadium("InfoCision Stadium-Summa Field", "Akron, OH",
                                41.07234, -81.50802, "America/New_York", cap=30000)),
    # https://en.wikipedia.org/wiki/Scheumann_Stadium
    2050: dict(name="Ball State Cardinals", short="Ball State", abbrev="BALL",
               conf=MAC, color="#BA0C2F",
               stadium=_stadium("Scheumann Stadium", "Muncie, IN",
                                40.21600, -85.41680, "America/Indiana/Indianapolis", cap=22500)),
    # https://en.wikipedia.org/wiki/Doyt_Perry_Stadium
    189: dict(name="Bowling Green Falcons", short="Bowling Green", abbrev="BGSU",
             conf=MAC, color="#FE5000",
             stadium=_stadium("Doyt L. Perry Stadium", "Bowling Green, OH",
                              41.37811, -83.62250, "America/New_York", cap=24000)),
    # https://en.wikipedia.org/wiki/University_at_Buffalo_Stadium
    2084: dict(name="Buffalo Bulls", short="Buffalo", abbrev="BUFF",
               conf=MAC, color="#005BBB",
               stadium=_stadium("UB Stadium", "Amherst, NY",
                                42.99920, -78.77750, "America/New_York", cap=29013)),
    # https://en.wikipedia.org/wiki/Kelly/Shorts_Stadium
    2117: dict(name="Central Michigan Chippewas", short="Central Michigan", abbrev="CMU",
               conf=MAC, color="#6A0032",
               stadium=_stadium("Kelly/Shorts Stadium", "Mount Pleasant, MI",
                                43.57750, -84.77081, "America/Detroit", cap=35127)),
    # https://en.wikipedia.org/wiki/Rynearson_Stadium
    2199: dict(name="Eastern Michigan Eagles", short="Eastern Michigan", abbrev="EMU",
               conf=MAC, color="#006633",
               stadium=_stadium("Rynearson Stadium", "Ypsilanti, MI",
                                42.25583, -83.64722, "America/Detroit", cap=30200)),
    # https://en.wikipedia.org/wiki/Dix_Stadium
    2309: dict(name="Kent State Golden Flashes", short="Kent State", abbrev="KENT",
               conf=MAC, color="#002664",
               stadium=_stadium("Dix Stadium", "Kent, OH",
                                41.13920, -81.31331, "America/New_York", cap=25319)),
    # https://en.wikipedia.org/wiki/Yager_Stadium_(Miami_University)
    193: dict(name="Miami (OH) RedHawks", short="Miami (OH)", abbrev="M-OH",
             conf=MAC, color="#B61E2E",
             stadium=_stadium("Yager Stadium", "Oxford, OH",
                              39.51833, -84.72633, "America/New_York", cap=24286)),
    # https://en.wikipedia.org/wiki/Huskie_Stadium
    2459: dict(name="Northern Illinois Huskies", short="Northern Illinois", abbrev="NIU",
               conf=MAC, color="#BA0C2F",
               stadium=_stadium("Huskie Stadium", "DeKalb, IL",
                                41.93406, -88.77798, "America/Chicago", cap=23595)),
    # https://en.wikipedia.org/wiki/Peden_Stadium
    195: dict(name="Ohio Bobcats", short="Ohio", abbrev="OHIO",
             conf=MAC, color="#00694E",
             stadium=_stadium("Frank Solich Field at Peden Stadium", "Athens, OH",
                              39.32111, -82.10281, "America/New_York", cap=24000)),
    # https://en.wikipedia.org/wiki/Glass_Bowl
    2649: dict(name="Toledo Rockets", short="Toledo", abbrev="TOL",
               conf=MAC, color="#15397F",
               stadium=_stadium("Glass Bowl", "Toledo, OH",
                                41.65739, -83.61402, "America/New_York", cap=26248)),
    # https://en.wikipedia.org/wiki/Waldo_Stadium
    2711: dict(name="Western Michigan Broncos", short="Western Michigan", abbrev="WMU",
               conf=MAC, color="#6C4023",
               stadium=_stadium("Waldo Stadium", "Kalamazoo, MI",
                                42.28600, -85.60075, "America/Detroit", cap=30200)),
})


# ── Patch conference for teams that moved from IND to G5 ──────────────────
# Army joined AAC in 2024 (was IND in the initial P4+IND coverage).
# UMass joined MAC in 2025 (same).
# UConn stays IND.
if 349 in FBS_TEAMS:
    FBS_TEAMS[349]["conf"] = AAC
if 113 in FBS_TEAMS:
    FBS_TEAMS[113]["conf"] = MAC
