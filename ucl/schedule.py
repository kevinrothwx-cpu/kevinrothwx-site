"""
ucl.schedule — Champions League fixtures.

Single source: The Odds API, via ucl/odds_api_schedule.py. There is
deliberately NO ESPN fallback here. ESPN 403-blocks Render (NFL 2026-08-14,
MLS 2026-08-24), and a fallback that always fails is worse than none — it
hides the real failure behind a second empty result. If the Odds API is
down, we return [] and the slate shows its empty state honestly.
"""

from __future__ import annotations

from datetime import datetime

from .odds_api_schedule import (
    fetch_ucl_matches_from_odds_api,
    filter_to_window,
)


def get_ucl_week_matches(start_date: datetime, days_ahead: int = 7) -> list[dict]:
    """UCL fixtures kicking off within the window. Empty list on failure."""
    all_matches = fetch_ucl_matches_from_odds_api()
    if not all_matches:
        print("[ucl.schedule] no fixtures returned from Odds API", flush=True)
        return []
    windowed = filter_to_window(all_matches, start_date, days_ahead=days_ahead)
    print(f"[ucl.schedule] {len(all_matches)} fixtures upcoming, "
          f"{len(windowed)} in {days_ahead}d window", flush=True)
    return windowed
