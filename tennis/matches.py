"""tennis.matches — ESPN scoreboard fetcher for ATP + WTA matches by date.

CORRECTED NESTING (was wrong in v1): ESPN tennis returns ONE event per
TOURNAMENT, not one event per match. The actual matches live two levels
deep:

    event (tournament, e.g. "Wimbledon")
      .groupings[]                    (division: Men's Singles, etc.)
        .competitions[]               (the actual matches)
          .competitors[]              (player A, player B)
            .athlete                  (player metadata)

v1 was treating event-level as match-level and getting empty results.

ESPN tennis scoreboard URL shapes:
  https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=YYYYMMDD
  https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard?dates=YYYYMMDD

The `?dates=` filter is on the TOURNAMENT window (event has startDate/endDate
spanning the whole Slam). To get only THIS DAY's matches we filter inside
the response: each competition has its own `date` field.

Returns list of normalized match dicts sorted by start time. Never raises;
on fetch failure returns [] so the per-day page still renders.
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

# Substring matchers against event.name / event.shortName.
# ESPN uses "Wimbledon", "US Open", "French Open", "Australian Open"
# as the tournament names — straightforward substring match.
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
    day_iso_prefix = day.strftime("%Y-%m-%d")  # competition.date starts with this
    out: list[dict] = []
    # During a Slam, ESPN's ATP and WTA scoreboard endpoints BOTH return the
    # entire Wimbledon event with every grouping (Men's/Women's/Doubles/etc.),
    # so the same match shows up twice if we don't dedup. Key by ESPN
    # competition.id which is unique per match across tours.
    seen_ids: set[str] = set()

    for endpoint_tour, url in (("ATP", ESPN_ATP_URL), ("WTA", ESPN_WTA_URL)):
        try:
            resp = requests.get(
                url, params={"dates": date_str},
                headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SEC,
            )
            if resp.status_code != 200:
                log.warning(f"[tennis.matches] {endpoint_tour} fetch returned {resp.status_code}")
                continue
            data = resp.json()
        except Exception as e:
            log.warning(f"[tennis.matches] {endpoint_tour} fetch failed: {e}")
            continue

        for event in (data.get("events") or []):
            ev_name = (event.get("name") or "").lower()
            ev_short = (event.get("shortName") or "").lower()
            combined = f"{ev_name} {ev_short}"
            if not any(m in combined for m in matchers):
                continue

            # Drill into groupings -> competitions to find individual matches
            for grouping in (event.get("groupings") or []):
                division = ((grouping.get("grouping") or {}).get("displayName") or "")
                # Map division → actual tour. Don't trust the endpoint label:
                # ATP endpoint returns women's matches too during Slams, so
                # tagging them "ATP" would mislabel WTA singles as ATP.
                div_low = division.lower()
                if "women" in div_low:
                    tour = "WTA"
                elif "men" in div_low:
                    tour = "ATP"
                else:
                    # Mixed Doubles / Wheelchair / Juniors / etc. — fall back
                    # to endpoint label (better than nothing)
                    tour = endpoint_tour
                for comp in (grouping.get("competitions") or []):
                    parsed = _parse_competition(comp, tour, division, day_iso_prefix)
                    if parsed and parsed["match_id"] not in seen_ids:
                        seen_ids.add(parsed["match_id"])
                        out.append(parsed)

    out.sort(key=lambda m: m.get("start_epoch") or 0)
    return out


def _parse_competition(comp: dict, tour: str, division: str,
                       day_iso_prefix: str) -> Optional[dict]:
    """Parse a single competition (match) into our normalized shape.
    Returns None if it's not on the requested date or has missing data."""
    comp_date = comp.get("date") or ""
    # Filter by date — competition.date is a full ISO timestamp like
    # "2026-06-29T10:05Z". Match the YYYY-MM-DD prefix.
    if comp_date and not comp_date.startswith(day_iso_prefix):
        return None

    competitors = comp.get("competitors") or []
    if len(competitors) < 2:
        return None

    p_a = _athlete_name(competitors[0])
    p_b = _athlete_name(competitors[1])
    if not p_a or not p_b:
        return None

    round_name = ((comp.get("type") or {}).get("text") or "")

    # Status: pre/in/post → scheduled/in_progress/final
    status_state = ((comp.get("status") or {}).get("type") or {}).get("state") or ""
    status_map = {"pre": "scheduled", "in": "in_progress", "post": "final"}
    status = status_map.get(status_state, status_state)

    # Start epoch for sorting
    start_epoch = 0
    if comp_date:
        try:
            dt = datetime.fromisoformat(comp_date.replace("Z", "+00:00"))
            start_epoch = int(dt.timestamp())
        except (ValueError, TypeError):
            pass

    # Score (live/final only): each competitor's linescores → "6-4, 7-5"
    score_parts = []
    for c in competitors:
        sets = [str(int(s.get("value", 0))) for s in (c.get("linescores") or [])]
        if sets:
            score_parts.append("-".join(sets))
    score = ", ".join(score_parts) if len(score_parts) == 2 else ""

    return {
        "match_id":    str(comp.get("id") or f"{tour}_{p_a}_{p_b}"),
        "tour":        tour,
        "division":    division,
        "round":       round_name,
        "player_a":    p_a,
        "player_b":    p_b,
        "court":       "",
        "start_iso":   comp_date,
        "start_epoch": start_epoch,
        "status":      status,
        "score":       score,
    }


def _athlete_name(competitor: dict) -> str:
    athlete = competitor.get("athlete") or {}
    name = (athlete.get("shortName")
            or athlete.get("displayName")
            or athlete.get("fullName")
            or competitor.get("displayName")
            or "").strip()
    return name


def format_local_time(start_iso: str, tz_name: str) -> str:
    """Format an ISO UTC start time as venue-local hh:mm AM/PM. Empty on failure."""
    if not start_iso:
        return ""
    try:
        dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        local = dt.astimezone(ZoneInfo(tz_name))
        return local.strftime("%-I:%M %p").lstrip("0")
    except Exception:
        return ""
