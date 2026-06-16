"""
nascar.schedule_fallback — hand-curated 2026 NASCAR Cup Series schedule.

WHY this exists:
    ESPN's NASCAR Cup endpoint at /sports/racing/nascar-cup-series/scoreboard
    returns 400. The community ESPN-API gist no longer lists a NASCAR
    endpoint. Until ESPN restores access (or we find the right path), we
    fall back to this embedded schedule so the /nascar page is never blank
    during the active season.

    Source: 2026 NASCAR Cup Series schedule, verified against NASCAR.com
    and Wikipedia (June 2026). Pre-DST races (Daytona 500 Feb 15) are EST
    (UTC-5); everything from March 8 through November 1 is EDT (UTC-4).

USAGE:
    `get_fallback_events(today_utc)` returns the next several upcoming
    races as a list of dicts that match ESPN's event schema, so
    parse_nascar_event handles them with no special-casing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


EASTERN_TZ = ZoneInfo("America/New_York")


# 2026 Cup Series schedule. Each entry:
#   (race_num, full_name, short_name, track_name, eastern_datetime)
# eastern_datetime is in ET local time, naive — we attach the timezone
# below before converting to UTC.
#
# Tracks must match an entry in nascar/tracks.py for the venue lookup
# to find weather. Tracks marked with # TODO below are new for 2026 and
# need to be added to tracks.py before they render correctly.
_RACES: list[tuple[int, str, str, str, datetime]] = [
    # Regular season
    (1,  "Daytona 500",                        "Daytona 500",        "Daytona International Speedway",   datetime(2026, 2, 15, 14, 30)),
    (2,  "Autotrader 400",                     "Atlanta",            "Atlanta Motor Speedway",           datetime(2026, 2, 22, 15, 0)),
    (3,  "Cook Out 400",                       "Phoenix",            "Phoenix Raceway",                  datetime(2026, 3, 8, 15, 30)),
    (4,  "Straight Talk Wireless 500",         "Phoenix",            "Phoenix Raceway",                  datetime(2026, 3, 8, 15, 30)),
    (5,  "Pennzoil 400",                       "Las Vegas",          "Las Vegas Motor Speedway",         datetime(2026, 3, 15, 16, 0)),
    (6,  "Goodyear 400",                       "Darlington",         "Darlington Raceway",               datetime(2026, 3, 22, 15, 0)),
    (7,  "Cook Out 400",                       "Martinsville",       "Martinsville Speedway",            datetime(2026, 3, 29, 15, 30)),
    (8,  "Food City 500",                      "Bristol",            "Bristol Motor Speedway",           datetime(2026, 4, 12, 15, 0)),
    (9,  "AdventHealth 400",                   "Kansas",             "Kansas Speedway",                  datetime(2026, 4, 19, 14, 0)),
    (10, "Würth 400",                          "Texas",              "Texas Motor Speedway",             datetime(2026, 5, 3, 15, 30)),
    (11, "Go Bowling at The Glen",             "Watkins Glen",       "Watkins Glen International",       datetime(2026, 5, 10, 15, 0)),
    (12, "Coca-Cola 600",                      "Charlotte 600",      "Charlotte Motor Speedway",         datetime(2026, 5, 24, 18, 0)),
    (13, "Cracker Barrel 400",                 "Nashville",          "Nashville Superspeedway",          datetime(2026, 5, 31, 15, 0)),
    (14, "FireKeepers Casino 400",             "Michigan",           "Michigan International Speedway",  datetime(2026, 6, 7, 15, 0)),
    (15, "The Great American Getaway 400",     "Pocono",             "Pocono Raceway",                   datetime(2026, 6, 14, 15, 0)),
    (16, "Anduril 250",                        "Coronado",           "Coronado Street Course",           datetime(2026, 6, 21, 16, 0)),  # new track
    (17, "Toyota/Save Mart 350",               "Sonoma",             "Sonoma Raceway",                   datetime(2026, 6, 28, 15, 30)),
    (18, "Grant Park 165",                     "Chicagoland",        "Chicagoland Speedway",             datetime(2026, 7, 5, 18, 0)),
    (19, "Quaker State 400",                   "Atlanta Summer",     "Atlanta Motor Speedway",           datetime(2026, 7, 12, 19, 0)),
    (20, "Window World 450",                   "North Wilkesboro",   "North Wilkesboro Speedway",        datetime(2026, 7, 19, 18, 0)),  # new track
    (21, "Brickyard 400",                      "Indianapolis",       "Indianapolis Motor Speedway",      datetime(2026, 7, 26, 14, 0)),
    (22, "Iowa Corn 350",                      "Iowa",               "Iowa Speedway",                    datetime(2026, 8, 9, 15, 30)),
    (23, "Cook Out 400",                       "Richmond",           "Richmond Raceway",                 datetime(2026, 8, 15, 19, 0)),
    (24, "Mobil 1 301",                        "New Hampshire",      "New Hampshire Motor Speedway",     datetime(2026, 8, 23, 15, 0)),
    (25, "Coke Zero Sugar 400",                "Daytona Summer",     "Daytona International Speedway",   datetime(2026, 8, 29, 19, 30)),
    # Playoffs
    (26, "Cook Out Southern 500",              "Darlington Playoff", "Darlington Raceway",               datetime(2026, 9, 6, 17, 0)),
    (27, "Enjoy Illinois 300",                 "WWTR",               "World Wide Technology Raceway",    datetime(2026, 9, 13, 15, 0)),
    (28, "Bass Pro Shops Night Race",          "Bristol Night",      "Bristol Motor Speedway",           datetime(2026, 9, 19, 19, 30)),
    (29, "Hollywood Casino 400",               "Kansas Playoff",     "Kansas Speedway",                  datetime(2026, 9, 27, 15, 0)),
    (30, "South Point 400",                    "Las Vegas Playoff",  "Las Vegas Motor Speedway",         datetime(2026, 10, 4, 17, 30)),
    (31, "Bank of America 400",                "Charlotte Roval",    "Charlotte Motor Speedway",         datetime(2026, 10, 11, 15, 0)),
    (32, "Freeway Insurance 500",              "Phoenix Playoff",    "Phoenix Raceway",                  datetime(2026, 10, 18, 15, 0)),
    (33, "YellaWood 500",                      "Talladega",          "Talladega Superspeedway",          datetime(2026, 10, 25, 14, 0)),
    (34, "Xfinity 500",                        "Martinsville Final", "Martinsville Speedway",            datetime(2026, 11, 1, 14, 0)),
    (35, "Straight Talk Wireless 400",         "Homestead Finale",   "Homestead-Miami Speedway",         datetime(2026, 11, 8, 15, 0)),
]


def _race_to_espn_dict(race: tuple) -> dict:
    """Convert a schedule row to a dict shaped like ESPN's event JSON."""
    race_num, full_name, short_name, track, et_naive = race
    et_aware = et_naive.replace(tzinfo=EASTERN_TZ)
    utc_iso = et_aware.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "id":        f"nascar-2026-{race_num:02d}",
        "name":      full_name,
        "shortName": short_name,
        "date":      utc_iso,
        "status":    {"type": {"name": "STATUS_SCHEDULED"}},
        "competitions": [{
            "venue": {"fullName": track},
        }],
        "links":     [{"href": "https://www.nascar.com/nascar-cup-series/2026/schedule/"}],
    }


def get_fallback_events(now_utc: datetime | None = None, lookahead_days: int = 8) -> list[dict]:
    """
    Return upcoming races within the next `lookahead_days` window, formatted
    like ESPN's event dicts so parse_nascar_event handles them transparently.

    Empty list if the season hasn't started yet OR every remaining race is
    past `lookahead_days` away. Mirrors how ESPN's scoreboard naturally
    surfaces only "current" events.

    Lookahead of 8 days means: only this weekend's race shows mid-week, and
    the page rolls to next weekend's race on Monday once the prior one ends.
    Avoids showing races whose date is beyond the NWS 7-day forecast window.
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    cutoff = now_utc + timedelta(days=lookahead_days)

    out = []
    for race in _RACES:
        et_naive = race[4]
        et_aware = et_naive.replace(tzinfo=EASTERN_TZ)
        race_utc = et_aware.astimezone(timezone.utc)
        # Include races that haven't ended yet (assume ~3.5 h race duration)
        if race_utc + timedelta(hours=4) < now_utc:
            continue
        if race_utc > cutoff:
            continue
        out.append(_race_to_espn_dict(race))
    return out
