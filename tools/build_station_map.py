"""build_station_map.py — map every venue to its nearest observing stations.

PURPOSE
    OVERcast Live needs CURRENT OBSERVED conditions during a game ("is it
    actually raining right now"), not a forecast. This script produces the
    stadium -> observation-station lookup that makes that possible, by
    querying Synoptic Data's metadata service for the closest active
    stations around each venue's lat/lon.

WHY SYNOPTIC AND NOT NWS
    MSW already depends on api.weather.gov, api.weatherapi.com, and
    open-meteo.com. Render's outbound IPs are shared across every service
    in a region (and across other Render customers), so a second service
    hammering any of those three can get MSW's own requests throttled.
    Synoptic is a vendor MSW touches nowhere, which decouples OVERcast
    Live's request budget from MSW's entirely.

WHY THIS IS A GENERATOR AND NOT A CHECKED-IN TABLE
    Station assignments are derived, not remembered. Guessing ~190 ICAO
    identifiers from memory would produce a table that looks authoritative
    and is quietly wrong in places — and a wrong station is worse than no
    station, because it reports confident weather from the wrong place.
    Everything here comes back from the API with a measured DISTANCE.

USAGE
    export SYNOPTIC_TOKEN=your_token_here
    python3 tools/build_station_map.py

    Writes  data/venue_station_map.json   (the map)
            data/venue_station_map_report.txt  (things worth eyeballing)

    Responses are cached in data/.synoptic_cache/ so re-runs cost no
    additional API quota. Delete that directory to force a refresh.

COST
    One request per venue, ~190 total, one time. Synoptic's free tier is
    5,000 requests/month, so a full rebuild is ~4% of a month's budget.
    Runtime is a few minutes because open-access concurrency is 1 and we
    deliberately sleep between calls.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Optional

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

API_URL = "https://api.synopticdata.com/v2/stations/metadata"
TOKEN = os.environ.get("SYNOPTIC_TOKEN", "").strip()

MERGE_RADIUS_MI = 2.0      # same name + within this = the same venue
SEARCH_RADIUS_MI = 30      # generous; we rank by distance afterwards
CANDIDATES_PER_VENUE = 8
SLEEP_BETWEEN_CALLS = 0.4  # open-access concurrency is 1; be polite
FAR_STATION_WARN_MI = 15.0 # flag anything further than this for review

# Live needs temperature + wind at minimum. varsoperator=and means a
# station must report BOTH to be returned at all.
REQUIRED_VARS = "air_temp,wind_speed"

# Networks whose stations are airport ASOS/AWOS — hourly METAR, highly
# reliable, and they report present-weather (rain/snow) rather than just
# a precip accumulation tick. Preferred as primary for that reason.
# NWS/FAA = 1, and RAWS/other mesonets fill in around them.
METAR_NETWORK_IDS = {"1"}

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", ".synoptic_cache")
OUT_MAP = os.path.join(os.path.dirname(__file__), "..", "data", "venue_station_map.json")
OUT_REPORT = os.path.join(os.path.dirname(__file__), "..", "data",
                          "venue_station_map_report.txt")


# ── Venue collection ──────────────────────────────────────────────────────

def _miles_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in miles."""
    from math import radians, sin, cos, asin, sqrt
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    a = (sin((lat2 - lat1) / 2) ** 2
         + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2)
    return 2 * asin(sqrt(a)) * 3958.8


def collect_venues() -> list[dict]:
    """Every venue across all sports, deduped by name + proximity.

    Domes are INCLUDED but flagged needs_obs=False. Live should skip them
    (there is no weather indoors), but having the row present means a
    lookup never silently misses — it returns a venue that says "indoor".
    """
    out: dict[str, list[dict]] = {}

    def add(sport, name, city, lat, lon, roof, extra=None):
        """Merge on NAME **and** proximity — never on name alone.

        Both halves are load-bearing, and each guards a real failure we
        have already hit in this codebase:

        - Name alone is wrong: there are FOUR different "Memorial Stadium"
          entries (Lincoln NE, Champaign IL, Clemson SC, Bloomington IN).
          Merging by name collapsed them into one venue and would have
          pointed three schools at a station hundreds of miles away. This
          is the same collision that produced wrong field bearings when
          matching was done on city alone.

        - Exact coords are wrong too: the same stadium appears in several
          tables with slightly different lat/lon (Allegiant is in both
          cfb/venues.py and cfb/neutral_venues.py; Fenway is in both
          neutral_venues.py and park_metadata.py). Keying on rounded
          coords split those into duplicates — two API calls each, and two
          rows Live could disagree between.

        So: same name AND within MERGE_RADIUS_MI => same venue.

        On merge we UNION the extra fields rather than discarding them.
        Otherwise MLB's hand-entered asos_station was lost whenever a park
        had already been added by an earlier sport, silently disabling the
        cross-check that validates this script against known-good data.
        """
        if lat is None or lon is None:
            return
        lat, lon = float(lat), float(lon)
        nkey = str(name).strip().lower()

        for rec in out.setdefault(nkey, []):
            if _miles_between(rec["lat"], rec["lon"], lat, lon) <= MERGE_RADIUS_MI:
                rec["sports"].add(sport)
                if extra:
                    for k, val in extra.items():
                        if val is not None and rec.get(k) is None:
                            rec[k] = val
                return

        rec = {
            "name": name, "city": city,
            "lat": lat, "lon": lon,
            "roof": roof or "open",
            "sports": {sport},
            "needs_obs": (roof or "open") != "fixed_dome",
        }
        if extra:
            rec.update(extra)
        out[nkey].append(rec)

    from cfb.venues import FBS_TEAMS
    for t in FBS_TEAMS.values():
        s = t.get("stadium")
        if s:
            add("cfb", s.get("name"), s.get("city"), s.get("lat"), s.get("lon"),
                s.get("roof"), {"team": t.get("short")})

    from cfb.neutral_venues import NEUTRAL_VENUES
    for v in NEUTRAL_VENUES.values():
        add("cfb_neutral", v.get("name"), v.get("city"), v.get("lat"),
            v.get("lon"), v.get("roof"), {"country": v.get("country", "US")})

    from nfl.venues import NFL_TEAMS
    for t in NFL_TEAMS.values():
        s = t.get("stadium")
        if s:
            add("nfl", s.get("name"), s.get("city"), s.get("lat"), s.get("lon"),
                s.get("roof_type"), {"team": t.get("short")})

    try:
        from nfl.venues import INTERNATIONAL_VENUES
        for v in INTERNATIONAL_VENUES.values():
            add("nfl_intl", v.get("name"), v.get("city"), v.get("lat"),
                v.get("lon"), v.get("roof_type") or v.get("roof"),
                {"country": v.get("country", "??")})
    except ImportError:
        pass

    try:
        from mlb.park_metadata import PARK_METADATA
        for name, p in PARK_METADATA.items():
            add("mlb", name, p.get("city"), p.get("lat"), p.get("lon"),
                p.get("roof_type"),
                {"team": p.get("team"), "existing_asos": p.get("asos_station")})
    except ImportError:
        pass

    venues = [rec for group in out.values() for rec in group]
    for v in venues:
        v["sports"] = sorted(v["sports"])
    venues.sort(key=lambda v: (v["sports"][0], v["name"], v["city"] or ""))
    return venues


# ── Synoptic query ────────────────────────────────────────────────────────

def _cache_path(lat: float, lon: float) -> str:
    return os.path.join(CACHE_DIR, f"{lat:.3f}_{lon:.3f}.json")


def fetch_candidates(lat: float, lon: float) -> Optional[dict]:
    """Nearest active stations reporting temp AND wind. Cached on disk."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cp = _cache_path(lat, lon)
    if os.path.exists(cp):
        with open(cp, encoding="utf-8") as f:
            return json.load(f)

    params = {
        "token": TOKEN,
        "radius": f"{lat},{lon},{SEARCH_RADIUS_MI}",
        "limit": CANDIDATES_PER_VENUE,
        "status": "active",
        "vars": REQUIRED_VARS,
        "varsoperator": "and",
        "sensorvars": 1,
        "output": "json",
    }
    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    code = str((data.get("SUMMARY") or {}).get("RESPONSE_CODE", ""))
    if code == "200":
        raise RuntimeError("Synoptic auth failure — check SYNOPTIC_TOKEN")
    if code not in ("1", "2"):
        raise RuntimeError(f"Synoptic error {code}: "
                           f"{(data.get('SUMMARY') or {}).get('RESPONSE_MESSAGE')}")

    with open(cp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    time.sleep(SLEEP_BETWEEN_CALLS)
    return data


def rank_stations(data: dict) -> list[dict]:
    """Order candidates: METAR/ASOS first (they report present weather, not
    just accumulation), then by distance. Returns simplified dicts."""
    stations = (data or {}).get("STATION") or []
    out = []
    for s in stations:
        sensor_vars = s.get("SENSOR_VARIABLES") or {}
        has_precip = any(k.startswith("precip") for k in sensor_vars)
        has_weather = "weather_condition" in sensor_vars or "weather_summary" in sensor_vars
        try:
            dist = float(s.get("DISTANCE"))
        except (TypeError, ValueError):
            dist = 999.0
        out.append({
            "stid": s.get("STID"),
            "name": s.get("NAME"),
            "distance_mi": round(dist, 2),
            "network_id": str(s.get("MNET_ID") or ""),
            "is_metar": str(s.get("MNET_ID") or "") in METAR_NETWORK_IDS,
            "elevation_ft": s.get("ELEVATION"),
            "lat": s.get("LATITUDE"), "lon": s.get("LONGITUDE"),
            "timezone": s.get("TIMEZONE"),
            "reports_precip": has_precip,
            "reports_present_weather": has_weather,
        })
    # METAR first, then present-weather capability, then distance.
    out.sort(key=lambda x: (not x["is_metar"],
                            not x["reports_present_weather"],
                            x["distance_mi"]))
    return out


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> int:
    if not TOKEN:
        print("ERROR: set SYNOPTIC_TOKEN first.\n"
              "  export SYNOPTIC_TOKEN=your_token_here\n"
              "Get one at https://synopticdata.com/pricing/free-trial/")
        return 1

    venues = collect_venues()
    obs_needed = [v for v in venues if v["needs_obs"]]
    print(f"{len(venues)} venues total, {len(obs_needed)} need observations "
          f"({len(venues) - len(obs_needed)} domes skipped)\n")

    result, report, failures = {}, [], 0

    for i, v in enumerate(venues, 1):
        key = f"{v['name']}|{v['city']}"
        if not v["needs_obs"]:
            result[key] = {**{k: v[k] for k in
                              ("name", "city", "lat", "lon", "roof", "sports")},
                           "needs_obs": False, "primary": None, "fallbacks": []}
            continue

        try:
            ranked = rank_stations(fetch_candidates(v["lat"], v["lon"]))
        except Exception as e:
            print(f"  [{i}/{len(venues)}] FAIL {v['name']}: {type(e).__name__}: {e}")
            report.append(f"FETCH FAILED  {key}: {type(e).__name__}: {e}")
            failures += 1
            continue

        if not ranked:
            print(f"  [{i}/{len(venues)}] NONE {v['name']} — no station in "
                  f"{SEARCH_RADIUS_MI}mi reporting {REQUIRED_VARS}")
            report.append(f"NO STATION    {key} (searched {SEARCH_RADIUS_MI}mi)")
            result[key] = {**{k: v[k] for k in
                              ("name", "city", "lat", "lon", "roof", "sports")},
                           "needs_obs": True, "primary": None, "fallbacks": []}
            continue

        primary, fallbacks = ranked[0], ranked[1:3]
        result[key] = {
            **{k: v[k] for k in ("name", "city", "lat", "lon", "roof", "sports")},
            "needs_obs": True,
            "primary": primary,
            "fallbacks": fallbacks,
        }

        flag = ""
        if primary["distance_mi"] > FAR_STATION_WARN_MI:
            flag = f"  <-- {primary['distance_mi']}mi away, REVIEW"
            report.append(f"FAR STATION   {key}: {primary['stid']} "
                          f"{primary['distance_mi']}mi")
        if not primary["reports_present_weather"]:
            report.append(f"NO PRESENT-WX {key}: {primary['stid']} reports precip "
                          f"accumulation but not rain/snow type")
        print(f"  [{i}/{len(venues)}] {v['name'][:38]:38s} -> "
              f"{primary['stid']:8s} {primary['distance_mi']:5.1f}mi{flag}")

        # Cross-check MLB's existing hand-entered ASOS assignments.
        if v.get("existing_asos"):
            got = (primary["stid"] or "").upper()
            want = v["existing_asos"].upper()
            if got != want and got != want.lstrip("K"):
                report.append(f"MLB MISMATCH  {key}: file says {want}, "
                              f"nearest is {got} ({primary['distance_mi']}mi)")

    os.makedirs(os.path.dirname(OUT_MAP), exist_ok=True)
    with open(OUT_MAP, "w", encoding="utf-8") as f:
        json.dump({
            "generated_by": "tools/build_station_map.py",
            "source": "Synoptic Data /v2/stations/metadata",
            "search_radius_mi": SEARCH_RADIUS_MI,
            "required_vars": REQUIRED_VARS,
            "venue_count": len(result),
            "venues": result,
        }, f, indent=2)

    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write(f"Venues: {len(venues)}  needing obs: {len(obs_needed)}  "
                f"fetch failures: {failures}\n")
        f.write(f"Items below want a human eye. An empty list is a clean run.\n\n")
        f.write("\n".join(report) if report else "(nothing flagged)")

    print(f"\nWrote {OUT_MAP}")
    print(f"Wrote {OUT_REPORT}  ({len(report)} item(s) flagged)")
    if failures:
        print(f"WARNING: {failures} venue(s) failed to fetch — re-run to retry "
              f"(cache means successful ones cost nothing).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
