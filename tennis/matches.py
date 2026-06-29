"""tennis.matches — ESPN scoreboard fetcher for ATP + WTA matches by date.

Pulls both tours simultaneously (each Slam has men's and women's draws on
the same days) and merges into a single normalized list for the per-day
detail pages.

ESPN tennis scoreboard URL shapes:
  https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=YYYYMMDD
  https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard?dates=YYYYMMDD

Filtering: the scoreboard returns ALL ATP/WTA matches on that date globally
(including non-Slam tour events that overlap a Slam window). We filter to
only matches whose league/tournament name matches the active Slam.

Output: list of normalized match dicts, sorted by start time:
  {
      "match_id":    str,
      "tour":        "ATP" | "WTA",
      "round":       "First Round" | "Quarterfinals" | etc.,
      "player_a":    "Sinner",
      "player_b":    "Alcaraz",
      "court":       "Centre Court" | "" (often blank from ESPN),
      "start_local": "2:00 PM" | "",
      "status":      "scheduled" | "in_progress" | "final",
      "score":       "6-4, 7-5" | "" (live/final only),
  }

Never raises — on fetch failure returns [] so the per-day page still
renders with the weather data, just without matchups.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import requests

log = logging.getLogger(__name__)


ESPN_ATP_URL = "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard"
ESPN_WTA_URL = "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard"

REQUEST_HEADERS = {
    "User-Agent": "kevinrothwx-site/1.0 tennis (kevinrothwx@gmail.com)",
}
REQUEST_TIMEOUT_SEC = 15

# Friendly names per slam ID — used to filter ESPN's league/tournament
# field. ESPN's name strings vary slightly so we use substring matching.
SLAM_NAME_MATCHERS = {
    "australian_open": ["australian open"],
    "french_open":     ["french open", "roland-garros", "roland garros"],
    "wimbledon":       ["wimbledon"],
    "us_open":         ["us open"],
}


def get_matches_for_day(slam_id: str, day: date) -> list[dict]:
    """Fetch + filter ATP + WTA matches for a Slam on a specific calendar
    date. Returns normalized list (possibly empty). Never raises."""
    matchers = SLAM_NAME_MATCHERS.get(slam_id, [])
    if not matchers:
        return []

    date_str = day.strftime("%Y%m%d")
    out: list[dict] = []

    for tour, url in (("ATP", ESPN_ATP_URL), ("WTA", ESPN_WTA_URL)):
        try:
            resp = requests.get(
                url, params={"dates": date_str},
                headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SEC,
            )
            if resp.status_code != 200:
                log.warning(f"[tennis.matches] {tour} fetch returned {resp.status_code} for {date_str}")
                continue
            data = resp.json()
        except Exception as e:
            log.warning(f"[tennis.matches] {tour} fetch failed for {date_str}: {e}")
            continue

        for event in (data.get("events") or []):
            parsed = _parse_event(event, tour, matchers)
            if parsed:
                out.append(parsed)

    out.sort(key=lambda m: m.get("start_epoch") or 0)
    return out


def _parse_event(event: dict, tour: str, matchers: list[str]) -> Optional[dict]:
    """Parse a single ESPN event into our normalized match shape.
    Returns None if the event doesn't belong to the target Slam."""
    league_name = ((event.get("season") or {}).get("displayName")
                   or event.get("name") or "").lower()
    short_name = (event.get("shortName") or "").lower()
    # ESPN puts the tournament name in different places depending on the
    # endpoint version — check both.
    combined = f"{league_name} {short_name}"
    if not any(m in combined for m in matchers):
        return None

    comp = (event.get("competitions") or [{}])[0]
    competitors = comp.get("competitors") or []
    if len(competitors) < 2:
        return None

    def _last_name(c):
        athlete = (c.get("athlete") or {})
        return (athlete.get("shortName") or athlete.get("displayName")
                or c.get("displayName") or "").strip()

    player_a = _last_name(competitors[0])
    player_b = _last_name(competitors[1])
    if not player_a or not player_b:
        return None

    # Round info
    round_name = ((comp.get("type") or {}).get("text")
                  or (event.get("status") or {}).get("type", {}).get("description")
                  or "")
    # Status: scheduled / in_progress / final
    status_state = ((event.get("status") or {}).get("type") or {}).get("state", "")
    status = "scheduled" if status_state == "pre" else \
             "in_progress" if status_state == "in" else \
             "final" if status_state == "post" else status_state or ""

    # Start time — keep both UTC epoch (for sorting) and ISO (for display)
    start_iso = comp.get("date") or event.get("date") or ""
    start_epoch = 0
    if start_iso:
        try:
            dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
            start_epoch = int(dt.timestamp())
        except (ValueError, TypeError):
            pass

    # Court / venue (rarely populated by ESPN at this layer)
    venue = (comp.get("venue") or {}).get("fullName") or ""

    # Score (live/final only)
    score_parts = []
    for c in competitors:
        # ESPN puts sets in "linescores"
        sets = [str(s.get("value", "")) for s in (c.get("linescores") or [])]
        if sets:
            score_parts.append("-".join(sets))
    score = ", ".join(score_parts) if len(score_parts) == 2 else ""

    return {
        "match_id":    str(event.get("id") or f"{tour}_{player_a}_{player_b}"),
        "tour":        tour,
        "round":       round_name,
        "player_a":    player_a,
        "player_b":    player_b,
        "court":       venue,
        "start_iso":   start_iso,
        "start_epoch": start_epoch,
        "status":      status,
        "score":       score,
    }


def format_local_time(start_iso: str, tz_name: str) -> str:
    """Format an ISO UTC start time as venue-local hh:mm AM/PM. Returns
    empty string on parse failure."""
    if not start_iso:
        return ""
    try:
        dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        local = dt.astimezone(ZoneInfo(tz_name))
        return local.strftime("%-I:%M %p").lstrip("0")
    except Exception:
        return ""
