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
from .courses import lookup_course


ESPN_PGA_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard"
REQUEST_HEADERS = {
    # Chrome desktop UA — see nfl/schedule.py for the 2026-08-14 UA-switch context
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept":     "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
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

    # Merge ESPN with the hand-curated fallback (2026-10-01 rewrite).
    #
    # WHAT BROKE: on 10/1 ESPN started listing the Bank of Utah Championship
    # with no course, and ESPN won the dedupe, so /golf showed "course not
    # mapped" on Round 1 day. The event_id also flipped from the fallback id
    # to ESPN's, so delete_orphaned() treated Kevin's write-up as an orphan
    # and deleted it.
    #
    # NOW, when an ESPN event matches a fallback event (by name/shortName, or
    # by start date when that date has exactly one event on each side):
    #   1. Fill in the course from the fallback if ESPN's is missing or not
    #      in our course table.
    #   2. Keep the fallback's event_id, so write-ups and round freezes keyed
    #      to it survive ESPN taking over. ESPN's leaderboard link is kept.
    fallback = get_fallback_events(datetime.now(timezone.utc))

    def _names(ev):
        return {(ev.get(k, "") or "").strip().lower()
                for k in ("name", "shortName")} - {""}

    def _start_day(ev):
        return (ev.get("date") or "")[:10]

    espn_days: dict[str, int] = {}
    for e in espn_events:
        d = _start_day(e)
        if d:
            espn_days[d] = espn_days.get(d, 0) + 1
    fb_days: dict[str, int] = {}
    for fe in fallback:
        d = _start_day(fe)
        if d:
            fb_days[d] = fb_days.get(d, 0) + 1

    used: set[int] = set()
    for e in espn_events:
        match_i = None
        for i, fe in enumerate(fallback):
            if i not in used and (_names(e) & _names(fe)):
                match_i = i
                break
        if match_i is None:
            d = _start_day(e)
            if d and espn_days.get(d) == 1 and fb_days.get(d) == 1:
                for i, fe in enumerate(fallback):
                    if i not in used and _start_day(fe) == d:
                        match_i = i
                        break
        if match_i is None:
            continue
        used.add(match_i)
        fe = fallback[match_i]
        try:
            comps = e.get("competitions") or []
            venue = (comps[0].get("venue") if comps else None) or {}
            course = (venue.get("fullName") or "").strip()
            if not course or lookup_course(course) is None:
                fb_venue = dict(((fe.get("competitions") or [{}])[0]).get("venue") or {})
                if fb_venue.get("fullName"):
                    if comps:
                        comps[0]["venue"] = fb_venue
                    else:
                        e["competitions"] = [{"venue": fb_venue}]
                    print(f"[golf.schedule] {e.get('name')!r}: ESPN course "
                          f"{course or '(none)'!r} -> fallback {fb_venue['fullName']!r}",
                          flush=True)
            e["espn_id"] = e.get("id")
            e["id"] = fe.get("id")
        except Exception as ex:
            print(f"[golf.schedule] merge patch failed for {e.get('name')!r}: {ex}", flush=True)

    merged = list(espn_events) + [fe for i, fe in enumerate(fallback) if i not in used]
    print(
        f"[golf.schedule] ESPN={len(espn_events)} events, matched {len(used)} "
        f"to fallback, fallback added {len(fallback) - len(used)}, merged={len(merged)}",
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

    # PGA Tour opposite-field events (usually clash with majors)
    "corales puntacana championship": "Corales Golf Course",
    "corales puntacana":              "Corales Golf Course",

    # Fall / silly season
    "rsm classic":               "Sea Island Resort (Seaside Course)",
    "the rsm classic":           "Sea Island Resort (Seaside Course)",
    "sanderson farms championship": "Country Club of Jackson",
    "world wide technology championship": "El Cardonal at Diamante",
    # Fall 2026 (added 2026-10-01; names as ESPN and pgatour.com list them)
    "bank of utah championship":  "Black Desert Resort",
    "black desert championship":  "Black Desert Resort",
    "baycurrent classic":         "Yokohama Country Club",
    "butterfield bermuda championship": "Port Royal Golf Course",
    "vidantaworld mexico open":   "Vidanta Vallarta",
    "austin championship":        "Omni Barton Creek Resort",
    "good good championship":     "Omni Barton Creek Resort",
    "hero world challenge":       "Albany GC",
    "grant thornton invitational": "Tiburon Golf Club",
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


# EOF-CANARY 2026-07-15-golf-corales
