"""cfb.neutral_venues — non-home venues for CFB games.

Purpose:
    CFB has three flavors of "not the home team's stadium":

    1. International kickoff games (Aer Lingus Classic in Dublin, etc.)
       — home stadium is in another country entirely.
    2. US neutral-site kickoff/rivalry games at pro venues (Mercedes-Benz
       Stadium, AT&T Stadium, Cotton Bowl, Allegiant Stadium) — these
       aren't any FBS team's home so the existing
       cfbd_client._find_stadium_by_name lookup misses them.
    3. Bowl venues, which are usually another FBS team's home (Rose Bowl
       = UCLA, Hard Rock = Miami, Camping World = UCF) — the existing
       lookup already handles these fine.

    This module covers (1) and (2). Category (3) doesn't need entries here.

Stadium shape:
    Matches cfb/venues.py FBS_TEAMS[X]["stadium"]: name, city, lat, lon,
    tz (IANA), roof, cap. International venues also carry
    nws_unsupported=True so the slate builder routes them to WeatherAPI
    (NWS only covers US territory).

    country field is informational — used by lookup fallbacks and admin
    debugging.

Maintenance:
    Add new venues as neutral-site games are announced each year.
    Update the "current-season slate" comment block below as a running
    list of known matchups so we can spot-check them in the log.
"""

from __future__ import annotations

from typing import Optional


# 2026 season neutral-site slate (informational — used to sanity-check
# that lookup finds the right venue on the game's slate row):
#   Aug 30 — UNC vs TCU @ Croke Park, Dublin (Aer Lingus Classic)
#   Aug 30 — Alabama vs FSU @ Mercedes-Benz, Atlanta (Chick-fil-A Kickoff)
#   Oct 11 — Texas vs Oklahoma @ Cotton Bowl, Dallas (Red River Rivalry)
#   Nov 28 — LSU vs Southern (Bayou Classic) @ Caesars Superdome, N.O.


NEUTRAL_VENUES: dict[str, dict] = {
    # ── International ─────────────────────────────────────────────────────
    "croke_park": {
        "name": "Croke Park", "city": "Dublin, IE",
        "lat": 53.3608, "lon": -6.2511, "tz": "Europe/Dublin",
        "roof": "open", "cap": 82300,
        "nws_unsupported": True, "country": "IE",
    },
    "aviva_stadium": {
        "name": "Aviva Stadium", "city": "Dublin, IE",
        "lat": 53.3350, "lon": -6.2286, "tz": "Europe/Dublin",
        "roof": "open", "cap": 51700,
        "nws_unsupported": True, "country": "IE",
    },
    "wembley": {
        "name": "Wembley Stadium", "city": "London, UK",
        "lat": 51.5560, "lon": -0.2795, "tz": "Europe/London",
        "roof": "retractable", "cap": 90000,
        "nws_unsupported": True, "country": "GB",
    },
    "allianz_arena": {
        "name": "Allianz Arena", "city": "Munich, DE",
        "lat": 48.2188, "lon": 11.6247, "tz": "Europe/Berlin",
        "roof": "open", "cap": 75000,
        "nws_unsupported": True, "country": "DE",
    },
    "estadio_azteca": {
        "name": "Estadio Azteca", "city": "Mexico City, MX",
        "lat": 19.3029, "lon": -99.1505, "tz": "America/Mexico_City",
        "roof": "open", "cap": 87000,
        "nws_unsupported": True, "country": "MX",
    },

    # ── US neutral sites (NOT any FBS team's home stadium) ───────────────
    # AT&T Stadium (Cowboys) — hosts Cotton Bowl, Southwest Classic, etc.
    "att_stadium": {
        "name": "AT&T Stadium", "city": "Arlington, TX",
        "lat": 32.7473, "lon": -97.0945, "tz": "America/Chicago",
        "roof": "retractable", "cap": 80000,
        "nws_unsupported": False, "country": "US",
    },
    # Cotton Bowl (Fair Park) — Red River Rivalry every year
    "cotton_bowl": {
        "field_bearing_degrees": 135,
        "name": "Cotton Bowl", "city": "Dallas, TX",
        "lat": 32.7796, "lon": -96.7607, "tz": "America/Chicago",
        "roof": "open", "cap": 92100,
        "nws_unsupported": False, "country": "US",
    },
    # Mercedes-Benz Stadium (Falcons) — Chick-fil-A Kickoff + Peach Bowl
    "mercedes_benz": {
        "name": "Mercedes-Benz Stadium", "city": "Atlanta, GA",
        "lat": 33.7553, "lon": -84.4006, "tz": "America/New_York",
        "roof": "retractable", "cap": 71000,
        "nws_unsupported": False, "country": "US",
    },
    # Caesars Superdome (Saints, Tulane) — Sugar Bowl, Bayou Classic
    "caesars_superdome": {
        "name": "Caesars Superdome", "city": "New Orleans, LA",
        "lat": 29.9511, "lon": -90.0814, "tz": "America/Chicago",
        "roof": "fixed_dome", "cap": 73000,
        "nws_unsupported": False, "country": "US",
    },
    # Allegiant Stadium (Raiders) — Vegas Kickoff Classic, LV Bowl
    "allegiant": {
        "name": "Allegiant Stadium", "city": "Las Vegas, NV",
        "lat": 36.0909, "lon": -115.1830, "tz": "America/Los_Angeles",
        "roof": "fixed_dome", "cap": 65000,
        "nws_unsupported": False, "country": "US",
    },
    # Ford Field (Lions) — Quick Lane Bowl
    "ford_field": {
        "name": "Ford Field", "city": "Detroit, MI",
        "lat": 42.3400, "lon": -83.0456, "tz": "America/Detroit",
        "roof": "fixed_dome", "cap": 65000,
        "nws_unsupported": False, "country": "US",
    },
    # Bank of America Stadium (Panthers) — Belk / Duke's Mayo Bowl
    "bank_of_america": {
        "field_bearing_degrees": 135,
        "name": "Bank of America Stadium", "city": "Charlotte, NC",
        "lat": 35.2258, "lon": -80.8528, "tz": "America/New_York",
        "roof": "open", "cap": 74867,
        "nws_unsupported": False, "country": "US",
    },
    # Yankee Stadium — Pinstripe Bowl
    "yankee_stadium": {
        "field_bearing_degrees": 45,
        "name": "Yankee Stadium", "city": "Bronx, NY",
        "lat": 40.8296, "lon": -73.9262, "tz": "America/New_York",
        "roof": "open", "cap": 54251,
        "nws_unsupported": False, "country": "US",
    },
    # Fenway Park — Fenway Bowl
    "fenway_park": {
        "name": "Fenway Park", "city": "Boston, MA",
        "lat": 42.3467, "lon": -71.0972, "tz": "America/New_York",
        "roof": "open", "cap": 37755,
        "nws_unsupported": False, "country": "US",
    },
    # Wrigley Field — occasional bowl games
    "wrigley_field": {
        "name": "Wrigley Field", "city": "Chicago, IL",
        "lat": 41.9484, "lon": -87.6553, "tz": "America/Chicago",
        "roof": "open", "cap": 41649,
        "nws_unsupported": False, "country": "US",
    },
    # Chase Field — Guaranteed Rate Bowl (Phoenix)
    "chase_field": {
        "name": "Chase Field", "city": "Phoenix, AZ",
        "lat": 33.4453, "lon": -112.0667, "tz": "America/Phoenix",
        "roof": "retractable", "cap": 48519,
        "nws_unsupported": False, "country": "US",
    },
    # SoFi Stadium (Rams/Chargers) — LA Bowl, occasional kickoff games
    "sofi_stadium": {
        "name": "SoFi Stadium", "city": "Inglewood, CA",
        "lat": 33.9535, "lon": -118.3392, "tz": "America/Los_Angeles",
        "roof": "fixed_canopy", "cap": 70240,
        "nws_unsupported": False, "country": "US",
    },
    # State Farm Stadium (Cardinals) — Fiesta Bowl + CFP semi/final
    "state_farm_stadium": {
        "name": "State Farm Stadium", "city": "Glendale, AZ",
        "lat": 33.5276, "lon": -112.2626, "tz": "America/Phoenix",
        "roof": "retractable", "cap": 63400,
        "nws_unsupported": False, "country": "US",
    },
    # Alamodome — Alamo Bowl (San Antonio)
    "alamodome": {
        "name": "Alamodome", "city": "San Antonio, TX",
        "lat": 29.4169, "lon": -98.4785, "tz": "America/Chicago",
        "roof": "fixed_dome", "cap": 64000,
        "nws_unsupported": False, "country": "US",
    },
    # Levi's Stadium (49ers) — LA Bowl / occasional bowl
    "levis_stadium": {
        "name": "Levi's Stadium", "city": "Santa Clara, CA",
        "lat": 37.4030, "lon": -121.9700, "tz": "America/Los_Angeles",
        "roof": "open", "cap": 68500,
        "nws_unsupported": False, "country": "US",
    },
}


def lookup_neutral_venue(venue_name: Optional[str],
                         city: Optional[str] = None) -> Optional[dict]:
    """Try to match a CFBD-supplied venue name + optional city to our
    NEUTRAL_VENUES table.

    Match order (most specific first):
      1. Exact name match (case-insensitive)
      2. Name substring — "AT&T" matches "AT&T Stadium"; "Croke" matches
         "Croke Park"; also catch the reverse (our name inside their name)
      3. City substring — "Dublin" matches Dublin venues; if there's
         exactly one match in that city, take it. When multiple venues
         share a city (e.g., Dublin has Croke + Aviva) return None from
         this step and let the caller fall through to the home-stadium
         default rather than picking the wrong one.

    Returns a copy of the venue dict so the caller can mutate it (e.g.,
    add is_neutral=True) without affecting our table."""
    if not venue_name and not city:
        return None

    vn = (venue_name or "").lower().strip()
    ci = (city or "").lower().strip()

    # 1. Exact name match
    if vn:
        for v in NEUTRAL_VENUES.values():
            if v["name"].lower() == vn:
                return dict(v)

    # 2. Substring match on the venue name (both directions)
    if vn:
        for slug, v in NEUTRAL_VENUES.items():
            vname_lower = v["name"].lower()
            if vname_lower in vn or vn in vname_lower or slug.replace("_", " ") in vn:
                return dict(v)

    # 3. City fallback — only take it when unique in that city
    if ci:
        matches = []
        for v in NEUTRAL_VENUES.values():
            v_city = v["city"].split(",")[0].strip().lower()
            if v_city and (v_city == ci or v_city in ci or ci in v_city):
                matches.append(v)
        if len(matches) == 1:
            return dict(matches[0])

    return None
