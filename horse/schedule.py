"""horse.schedule — hand-curated marquee US thoroughbred stakes calendar.

Every entry here is manually maintained. There's no clean ESPN-style
scoreboard endpoint for thoroughbred stakes racing, so we treat this
like the NASCAR fallback: a Python list Kevin edits directly.

Dates and post times need verification before publication. The
`verified` field flags entries Kevin has confirmed against the track's
official condition book or Equibase. Unverified entries render on
/horse but with a "verify" tag in the admin view.

Add a new stakes day by appending to STAKES_DAYS and setting the
track slug to a key from horse.venues.HORSE_TRACKS.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from .venues import HORSE_TRACKS


# Each entry:
#   race_id       — stable slug, "{track}-{yyyymmdd}-{race-slug}"
#   race_name     — display name
#   track         — venue slug from HORSE_TRACKS
#   date_local    — YYYY-MM-DD, venue local calendar date
#   post_time_local — HH:MM 24h, venue local time. None = TBD.
#   grade         — 1, 2, 3, or None (listed / not graded)
#   distance      — text, e.g. "1 1/4 miles"
#   surface       — "dirt" | "turf" | "all-weather"
#   purse_usd     — approximate, for display only
#   notes         — optional short handicapping note
#   verified      — True once Kevin has confirmed against official source
STAKES_DAYS: list[dict] = [
    # ── Saratoga summer meet 2026 ───────────────────────────────────
    {
        "race_id": "saratoga-20260801-whitney",
        "race_name": "Whitney Stakes",
        "track": "saratoga",
        "date_local": "2026-08-01",
        "post_time_local": None,
        "grade": 1,
        "distance": "1 1/8 miles",
        "surface": "dirt",
        "purse_usd": 1_000_000,
        "notes": "Older-horse handicap traditionally run on Whitney Day at Saratoga.",
        "verified": False,
    },
    {
        "race_id": "saratoga-20260822-travers",
        "race_name": "Travers Stakes",
        "track": "saratoga",
        "date_local": "2026-08-22",
        "post_time_local": None,
        "grade": 1,
        "distance": "1 1/4 miles",
        "surface": "dirt",
        "purse_usd": 1_250_000,
        "notes": "The Mid-Summer Derby, run at Saratoga since 1864. Traditionally the last Saturday in August.",
        "verified": False,
    },
    # ── Del Mar summer 2026 ─────────────────────────────────────────
    {
        "race_id": "del-mar-20260905-pacific-classic",
        "race_name": "Pacific Classic",
        "track": "del-mar",
        "date_local": "2026-09-05",
        "post_time_local": None,
        "grade": 1,
        "distance": "1 1/4 miles",
        "surface": "dirt",
        "purse_usd": 1_000_000,
        "notes": "Del Mar's premier summer stakes. Marine layer + late-afternoon post can move the tote.",
        "verified": False,
    },
    # ── Breeders' Cup 2026 ──────────────────────────────────────────
    # 2026 Breeders' Cup announced at Del Mar. Two-day event.
    {
        "race_id": "del-mar-20261106-bc-friday",
        "race_name": "Breeders' Cup Friday",
        "track": "del-mar",
        "date_local": "2026-11-06",
        "post_time_local": None,
        "grade": 1,
        "distance": "multi-race",
        "surface": "dirt/turf",
        "purse_usd": 0,
        "notes": "Breeders' Cup Friday card: Juvenile Fillies, Juvenile, Filly & Mare Turf. Verify card and post times against BreedersCup.com before publish.",
        "verified": False,
    },
    {
        "race_id": "del-mar-20261107-bc-classic",
        "race_name": "Breeders' Cup Classic",
        "track": "del-mar",
        "date_local": "2026-11-07",
        "post_time_local": None,
        "grade": 1,
        "distance": "1 1/4 miles",
        "surface": "dirt",
        "purse_usd": 7_000_000,
        "notes": "The world's richest thoroughbred race, headlines Breeders' Cup Saturday. Verify against BreedersCup.com before publish.",
        "verified": False,
    },
    # ── 2027 season openers ─────────────────────────────────────────
    {
        "race_id": "gulfstream-20270123-pegasus",
        "race_name": "Pegasus World Cup",
        "track": "gulfstream",
        "date_local": "2027-01-23",
        "post_time_local": None,
        "grade": 1,
        "distance": "1 1/8 miles",
        "surface": "dirt",
        "purse_usd": 3_000_000,
        "notes": "Late-January stakes at Gulfstream. Date is traditional last Saturday in January — verify against Gulfstream condition book.",
        "verified": False,
    },
]


def upcoming_stakes(within_days: int = 45) -> list[dict]:
    """Return stakes days from today up to `within_days` out, chronological.

    Uses UTC today as the reference (the calendar boundary is close
    enough — we're within a day either way for planning purposes).
    """
    today_utc = datetime.utcnow().date()
    out = []
    for race in STAKES_DAYS:
        try:
            d = datetime.strptime(race["date_local"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        delta = (d - today_utc).days
        if -1 <= delta <= within_days:
            out.append(dict(race, _parsed_date=d))
    out.sort(key=lambda r: r["_parsed_date"])
    return out


def get_stakes_race(race_id: str) -> dict | None:
    """Fetch a single race by race_id. Returns None on miss."""
    for race in STAKES_DAYS:
        if race.get("race_id") == race_id:
            return dict(race)
    return None
