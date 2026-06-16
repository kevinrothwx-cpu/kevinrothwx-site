"""
golf.schedule_fallback — hand-curated 2026 PGA Tour schedule.

WHY this exists:
    ESPN's PGA scoreboard endpoint at /sports/golf/pga/scoreboard often
    returns only the most-recently-completed tournament (sometimes weeks
    out of date), not the current/upcoming event. That leaves /golf empty
    once the filter drops the completed event. Same problem we solved for
    NASCAR with its own fallback.

    Source: https://www.pgatour.com/schedule (2026 season), captured
    2026-06-16. For weeks with two events on the same dates, we keep
    only the higher-purse one (the Signature / regular event over the
    opposite-field event), per Kevin's spec. Excluded:
      - JUL 9-12: ISCO Championship (kept Genesis Scottish Open)
      - JUL 16-19: Corales Puntacana (kept The Open Championship)

USAGE:
    `get_fallback_events(today_utc)` returns upcoming tournaments as
    ESPN-shaped event dicts so parse_pga_event handles them unchanged.

UPDATE CADENCE:
    Schedule needs an annual refresh for 2027. Re-pull from
    pgatour.com/schedule when the new season is published.
"""

from __future__ import annotations

from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo


EASTERN_TZ = ZoneInfo("America/New_York")


# 2026 PGA Tour schedule. Each row:
#   (event_id_suffix, full_name, short_name, course, location, start_date, end_date)
# Past tournaments (already played) are omitted — they wouldn't survive the
# date filter anyway. Kept events run from this week (mid-June) onward.
_TOURNAMENTS: list[tuple[str, str, str, str, str, date, date]] = [
    ("us-open",                "U.S. Open",                        "U.S. Open",                  "Shinnecock Hills Golf Club",          "Southampton, NY",             date(2026, 6, 18),  date(2026, 6, 21)),
    ("travelers",              "Travelers Championship",           "Travelers",                  "TPC River Highlands",                 "Cromwell, CT",                date(2026, 6, 25),  date(2026, 6, 28)),
    ("john-deere",             "John Deere Classic",               "John Deere",                 "TPC Deere Run",                       "Silvis, IL",                  date(2026, 7, 2),   date(2026, 7, 5)),
    ("scottish-open",          "Genesis Scottish Open",            "Scottish Open",              "The Renaissance Club",                "North Berwick, Scotland",     date(2026, 7, 9),   date(2026, 7, 12)),
    ("the-open",               "The Open Championship",            "The Open",                   "Royal Birkdale Golf Club",            "Southport, England",          date(2026, 7, 16),  date(2026, 7, 19)),
    ("3m-open",                "3M Open",                          "3M Open",                    "TPC Twin Cities",                     "Blaine, MN",                  date(2026, 7, 23),  date(2026, 7, 26)),
    ("rocket-classic",         "Rocket Classic",                   "Rocket Classic",             "Detroit Golf Club",                   "Detroit, MI",                 date(2026, 7, 30),  date(2026, 8, 2)),
    ("wyndham",                "Wyndham Championship",             "Wyndham",                    "Sedgefield Country Club",             "Greensboro, NC",              date(2026, 8, 6),   date(2026, 8, 9)),
    ("fedex-st-jude",          "FedEx St. Jude Championship",      "FedEx St. Jude",             "TPC Southwind",                       "Memphis, TN",                 date(2026, 8, 13),  date(2026, 8, 16)),
    ("bmw-championship",       "BMW Championship",                 "BMW",                        "Bellerive Country Club",              "St. Louis, MO",               date(2026, 8, 20),  date(2026, 8, 23)),
    ("tour-championship",      "TOUR Championship",                "TOUR Championship",          "East Lake Golf Club",                 "Atlanta, GA",                 date(2026, 8, 27),  date(2026, 8, 30)),
    ("biltmore",               "Biltmore Championship Asheville",  "Biltmore",                   "The Cliffs at Walnut Cove",           "Asheville, NC",               date(2026, 9, 17),  date(2026, 9, 20)),
    ("presidents-cup",         "Presidents Cup",                   "Presidents Cup",             "Medinah CC (No. 3)",                  "Medinah, IL",                 date(2026, 9, 24),  date(2026, 9, 27)),
    ("bank-of-utah",           "Bank of Utah Championship",        "Bank of Utah",               "Black Desert Resort",                 "Ivins, UT",                   date(2026, 10, 1),  date(2026, 10, 4)),
    ("baycurrent",             "Baycurrent Classic",               "Baycurrent",                 "Yokohama Country Club",               "Yokohama, Japan",             date(2026, 10, 8),  date(2026, 10, 11)),
    ("bermuda",                "Butterfield Bermuda Championship", "Bermuda",                    "Port Royal Golf Course",              "Southampton, Bermuda",        date(2026, 10, 22), date(2026, 10, 25)),
    ("mexico-open",            "VidantaWorld Mexico Open",         "Mexico Open",                "Vidanta Vallarta",                    "Vallarta, Mexico",            date(2026, 10, 29), date(2026, 11, 1)),
    ("wwt-championship",       "World Wide Technology Championship","WWT Championship",          "El Cardonal at Diamante",             "Los Cabos, Mexico",           date(2026, 11, 5),  date(2026, 11, 8)),
    ("good-good",              "Good Good Championship",           "Good Good",                  "Omni Barton Creek Resort",            "Austin, TX",                  date(2026, 11, 12), date(2026, 11, 15)),
    ("rsm-classic",            "The RSM Classic",                  "RSM Classic",                "Sea Island Golf Club (Seaside Course)", "St. Simons Island, GA",     date(2026, 11, 19), date(2026, 11, 22)),
    ("hero-world",             "Hero World Challenge",             "Hero",                       "Albany GC",                           "Albany, Bahamas",             date(2026, 12, 3),  date(2026, 12, 6)),
    ("grant-thornton",         "Grant Thornton Invitational",      "Grant Thornton",             "Tiburon Golf Club",                   "Naples, FL",                  date(2026, 12, 11), date(2026, 12, 13)),
]


def _tournament_to_espn_dict(t: tuple) -> dict:
    """Convert a schedule row to a dict shaped like ESPN's PGA event JSON."""
    suffix, full_name, short_name, course, location, start_d, end_d = t
    # ESPN uses midnight ET (04:00 UTC during EDT) for date/endDate fields.
    start_et = datetime(start_d.year, start_d.month, start_d.day, 0, 0, tzinfo=EASTERN_TZ)
    end_et   = datetime(end_d.year,   end_d.month,   end_d.day,   0, 0, tzinfo=EASTERN_TZ)
    start_iso = start_et.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    end_iso   = end_et.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

    # Split location into city + state/country for the address field.
    parts = [p.strip() for p in location.split(",")]
    city = parts[0] if parts else ""
    region = parts[1] if len(parts) > 1 else ""

    return {
        "id":        f"pga-2026-{suffix}",
        "name":      full_name,
        "shortName": short_name,
        "date":      start_iso,
        "endDate":   end_iso,
        "status":    {"type": {"name": "STATUS_SCHEDULED"}},
        "competitions": [{
            "venue": {
                "fullName": course,
                "address":  {"city": city, "state": region},
            },
        }],
        "links":     [{"href": "https://www.pgatour.com/schedule"}],
    }


def get_fallback_events(now_utc: datetime | None = None, lookahead_days: int = 21) -> list[dict]:
    """
    Return upcoming tournaments within the next `lookahead_days` window,
    formatted like ESPN's event dicts so parse_pga_event handles them
    transparently. Past tournaments are filtered out.

    Default lookahead of 21 days surfaces this week's tournament plus the
    next 2 weekends — gives the slate a buffer when ESPN is unreliable.
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    today_utc_date = now_utc.date()
    cutoff_date = (now_utc + timedelta(days=lookahead_days)).date()

    out = []
    for t in _TOURNAMENTS:
        _, _, _, _, _, start_d, end_d = t
        # Drop tournaments that ended before today (UTC date comparison)
        if end_d < today_utc_date:
            continue
        # Drop tournaments that start beyond the lookahead window
        if start_d > cutoff_date:
            continue
        out.append(_tournament_to_espn_dict(t))
    return out
