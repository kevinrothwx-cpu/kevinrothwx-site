"""tennis.schedule — Grand Slam date windows.

Hard-coded annual fixtures, same pattern as cws/venue.py.

2026 dates per official tournament announcements (best available estimates
where 2026 hasn't been formally published yet — update if/when ATP/WTA
finalize). Each Slam runs 14 calendar days, Mon–Sun (Australian Open has
moved to a Sunday-start 15-day format since 2024).

The card on the homepage is gated by active_slam(): if None, the card is
hidden. If a Slam is active, the card surfaces it with link to /tennis.
"""

from __future__ import annotations

from datetime import datetime, date
from zoneinfo import ZoneInfo

from .venues import SLAM_VENUES


# Slam windows: (slam_id, start_date, end_date, display_name).
# Dates are local to the venue (we compare in venue-local time so the
# card flips on/off cleanly at midnight at the venue rather than at some
# unrelated US timezone).
SLAM_WINDOWS_2026 = [
    # Australian Open 2026: Sun Jan 18 → Sun Feb 1 (15-day format)
    ("australian_open", date(2026, 1, 18), date(2026, 2,  1), "Australian Open 2026"),
    # French Open 2026: Sun May 24 → Sun Jun 7
    ("french_open",     date(2026, 5, 24), date(2026, 6,  7), "Roland Garros 2026"),
    # Wimbledon 2026: Mon Jun 29 → Sun Jul 12
    ("wimbledon",       date(2026, 6, 29), date(2026, 7, 12), "Wimbledon 2026"),
    # US Open 2026: Mon Aug 31 → Sun Sep 13
    ("us_open",         date(2026, 8, 31), date(2026, 9, 13), "US Open 2026"),
]


def _today_at_venue(venue_meta: dict) -> date:
    """Return today's date in the venue's local timezone."""
    return datetime.now(ZoneInfo(venue_meta["timezone"])).date()


def active_slam() -> dict | None:
    """Return the currently-active Slam (date is within window in venue-local
    time), or None if no Slam is in session. If two Slams' windows happened
    to overlap (they shouldn't), returns the first.

    Return shape:
      {
          "slam_id":      "wimbledon",
          "display_name": "Wimbledon 2026",
          "start_date":   date(2026, 6, 29),
          "end_date":     date(2026, 7, 12),
          "venue":        {... venue dict ...},
      }
    """
    for slam_id, start, end, display in SLAM_WINDOWS_2026:
        venue = SLAM_VENUES.get(slam_id)
        if not venue:
            continue
        today_local = _today_at_venue(venue)
        if start <= today_local <= end:
            return {
                "slam_id":      slam_id,
                "display_name": display,
                "start_date":   start,
                "end_date":     end,
                "venue":        venue,
            }
    return None


def next_slam() -> dict | None:
    """Return the next upcoming Slam (start_date >= today), or None if no
    further Slams remain in the calendar window. Used to render a 'Next:
    Wimbledon Jun 29' style placeholder if we ever want one (not used by
    the current homepage card, but useful for SEO landing pages).
    """
    # Use a generic "today" in Eastern for cross-Slam comparison
    today = datetime.now(ZoneInfo("America/New_York")).date()
    candidates = [(start, slam_id, end, display) for slam_id, start, end, display
                  in SLAM_WINDOWS_2026 if start >= today]
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    start, slam_id, end, display = candidates[0]
    venue = SLAM_VENUES.get(slam_id)
    return {
        "slam_id":      slam_id,
        "display_name": display,
        "start_date":   start,
        "end_date":     end,
        "venue":        venue,
    }


def get_slam_by_id(slam_id: str) -> dict | None:
    """Lookup any Slam (active or not) by ID. Used by /tennis/<slug> route."""
    for sid, start, end, display in SLAM_WINDOWS_2026:
        if sid == slam_id:
            venue = SLAM_VENUES.get(sid)
            return {
                "slam_id":      sid,
                "display_name": display,
                "start_date":   start,
                "end_date":     end,
                "venue":        venue,
            }
    return None


def is_any_slam_active() -> bool:
    """Cheap boolean for sport-nav strip — should the Tennis tab show?"""
    return active_slam() is not None
