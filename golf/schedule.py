"""
golf.schedule — ESPN's unofficial PGA Tour scoreboard + 2026 hand-curated
fallback.

ESPN's PGA scoreboard endpoint is unreliable: it often returns only the
most-recently-completed tournament (which our slate filter then drops),
leaving /golf empty. We merge ESPN's response with the hand-curated 2026
schedule in schedule_fallback.py so the page always shows the upcoming
tournament even when ESPN's data is stale.

Endpoint:
    https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard

Returns one or more active/upcoming tournaments with:
    - name, short name
    - course, location
    - start/end dates
    - status (scheduled, in-progress, final)

Free, no key, used by ESPN's apps. Same pattern as MLB Stats / soccer.
"""

from __future__ import annotations

import requests
import re
from datetime import datetime, timezone
from typing import Optional

from .schedule_fallback import get_fallback_events


ESPN_PGA_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard"
REQUEST_HEADERS = {
    "User-Agent": "kevinrothwx-site/1.0 (kevinrothwx@gmail.com)",
    "Accept":     "application/json",
}


def get_pga_scoreboard() -> list[dict]:
    """Fetch ESPN's PGA scoreboard, merged with the hand-curated 2026 fallback.

    ESPN sometimes returns only the most-recently-completed tournament. By
    always merging with the fallback (ESPN wins on name conflicts so its real
    event_id is preferred), the slate stays populated with current/upcoming
    tournaments regardless of ESPN's reliability."""
    espn_events: list[dict] = []
    try:
        resp = requests.get(
            ESPN_PGA_SCOREBOARD_URL,
            headers=REQUEST_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        espn_events = resp.json().get("events", []) or []
    except Exception as e:
        print(f"[golf.schedule] ESPN error: {e}", flush=True)

    # Merge in fallback events that ESPN didn't already surface, deduped by
    # tournament name (case-insensitive). ESPN wins on duplicates so a live
    # tournament keeps its canonical ESPN event_id.
    fallback = get_fallback_events(datetime.now(timezone.utc))
    espn_names_lower = {
        (e.get("name", "") or "").strip().lower()
        for e in espn_events
    }
    merged = list(espn_events)
    added = 0
    for fe in fallback:
        fe_name_lower = (fe.get("name", "") or "").strip().lower()
        if fe_name_lower and fe_name_lower not in espn_names_lower:
            merged.append(fe)
            added += 1
    print(
        f"[golf.schedule] ESPN={len(espn_events)} events, "
        f"fallback added {added} of {len(fallback)}, merged={len(merged)}",
        flush=True,
    )
    return merged


def parse_pga_event(event: dict) -> Optional[dict]:
    """
    Normalize an ESPN PGA event. Returns None if cancelled or missing fields.
    """
    try:
        status_name = (event.get("status") or {}).get("type", {}).get("name", "")
        if "CANCELED" in status_name.upper() or "CANCELLED" in status_name.upper():
            return None

        name      = event.get("name") or event.get("shortName") or "PGA Tournament"
        short_name = event.get("shortName") or name
        start_iso = event.get("date") or ""
        end_date  = event.get("endDate") or ""

        # Course / venue — ESPN nests this in competitions[0].venue
        comps = event.get("competitions") or []
        venue_obj = (comps[0].get("venue") if comps else {}) or {}
        course = venue_obj.get("fullName") or ""
        if not course:
            # ESPN sometimes omits venue.fullName for pre-tournament events.
            # Fall back to tournament name → course mapping.
            course = lookup_course_by_tournament(name) or lookup_course_by_tournament(short_name)
        address = venue_obj.get("address") or {}
        city = (address.get("city") or "").strip()
        state = (address.get("state") or "").strip()
        location = ", ".join([p for p in [city, state] if p])

        if not start_iso:
            return None

        return {
            "event_id":   str(event.get("id", "")),
            "name":       name,
            "short_name": short_name,
            "course":     course,
            "location":   location,
            "start_iso":  start_iso,
            "end_iso":    end_date,
            "status":     status_name,
            "url":        (event.get("links") or [{}])[0].get("href", ""),
        }
    except Exception as e:
        print(f"[golf.schedule] parse error: {e}", flush=True)
        return None


# When ESPN doesn't populate venue.fullName (common pre-tournament), look up
# the course by tournament name. Keys are matched case-insensitively against
# event['name'] or event['shortName']. Add new tournaments as they come up.
TOURNAMENT_NAME_TO_COURSE = {
    # Majors 2026
    "the masters":               "Augusta National Golf Club",
    "masters tournament":        "Augusta National Golf Club",
    "pga championship":          "Aronimink Golf Club",
    "u.s. open":                 "Shinnecock Hills Golf Club",
    "us open":                   "Shinnecock Hills Golf Club",
    "the open championship":     "Royal Birkdale Golf Club",
    "the open":                  "Royal Birkdale Golf Club",
    "open championship":         "Royal Birkdale Golf Club",

    # Regular PGA Tour stops (alphabetical by tournament name)
    "rbc canadian open":         "TPC Toronto at Osprey Valley",
    "canadian open":             "TPC Toronto at Osprey Valley",
    "the memorial tournament":   "Muirfield Village Golf Club",
    "memorial tournament":       "Muirfield Village Golf Club",
    "the memorial tournament presented by workday": "Muirfield Village Golf Club",
    "the players championship":  "TPC Sawgrass",
    "the players":               "TPC Sawgrass",
    "players championship":      "TPC Sawgrass",
    "arnold palmer invitational": "Bay Hill Club and Lodge",
    "arnold palmer invitational presented by mastercard": "Bay Hill Club and Lodge",
    "wm phoenix open":           "TPC Scottsdale",
    "phoenix open":              "TPC Scottsdale",
    "the genesis invitational":  "Riviera Country Club",
    "genesis invitational":      "Riviera Country Club",
    "farmers insurance open":    "Torrey Pines Golf Course",
    "the sentry":                "Plantation Course at Kapalua",
    "sony open in hawaii":       "Waialae Country Club",
    "sony open":                 "Waialae Country Club",
    "att pebble beach pro-am":   "Pebble Beach Golf Links",
    "at&t pebble beach pro-am":  "Pebble Beach Golf Links",
    "cognizant classic":         "PGA National Resort",
    "valspar championship":      "Innisbrook Resort (Copperhead Course)",
    "texas children's houston open": "Memorial Park Golf Course",
    "houston open":              "Memorial Park Golf Course",
    "the cj cup byron nelson":   "TPC Craig Ranch",
    "cj cup byron nelson":       "TPC Craig Ranch",
    "wells fargo championship":  "Quail Hollow Club",
    "truist championship":       "Quail Hollow Club",
    "charles schwab challenge":  "Colonial Country Club",
    "the travelers championship": "TPC River Highlands",
    "travelers championship":    "TPC River Highlands",
    "rocket mortgage classic":   "Detroit Golf Club",
    "rocket classic":            "Detroit Golf Club",
    "john deere classic":        "TPC Deere Run",
    "genesis scottish open":     "The Renaissance Club",
    "scottish open":             "The Renaissance Club",
    "the 3m open":               "TPC Twin Cities",
    "3m open":                   "TPC Twin Cities",
    "wyndham championship":      "Sedgefield Country Club",
    "fedex st. jude championship": "TPC Southwind",
    "fedex st jude championship":  "TPC Southwind",
    "bmw championship":          "Bellerive Country Club",
    "tour championship":         "East Lake Golf Club",
    "procore championship":      "Silverado Resort",

    # Fall / silly season
    "rsm classic":               "Sea Island Resort (Seaside Course)",
    "the rsm classic":           "Sea Island Resort (Seaside Course)",
    "sanderson farms championship": "Country Club of Jackson",
    "world wide technology championship": "El Cardonal at Diamante",
}


def lookup_course_by_tournament(name: str) -> str:
    """Fallback: when ESPN omits venue.fullName, look up by tournament name."""
    if not name:
        return ""
    return TOURNAMENT_NAME_TO_COURSE.get(name.lower().strip(), "")


def tournament_slug(name: str) -> str:
    """Slug for URL: 'us-open', 'memorial-tournament' style."""
    n = name.lower()
    n = re.sub(r"[^a-z0-9 ]+", "", n)
    n = re.sub(r"\s+", "-", n).strip("-")
    return n or "tournament"
