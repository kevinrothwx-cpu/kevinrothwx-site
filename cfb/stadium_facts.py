"""cfb.stadium_facts — factual, per-stadium content for CFB venue pages.

WHY THIS EXISTS
    cfb/stadium_content.py holds hand-written copy for 25 stadiums. The
    other 109 FBS venues had no page at all. The obvious move was to write
    109 more entries in the same shape, but the existing ones average 48
    words of unique text and read interchangeably:

        "Southeast humidity and afternoon thunderstorm risk are the primary
         early-season weather variables."

    Mass-producing a hundred more of those is the pattern Google's
    scaled-content policy targets, and it would put the existing pages at
    risk rather than adding value.

WHAT THIS DOES INSTEAD
    Generates content from data we actually hold and that no competitor
    has: each stadium's verified field bearing, its roof state, and its
    location. Every sentence is either a measured fact or a geometric
    consequence of one.

THE RULE THIS MODULE FOLLOWS
    Nothing predictive. Nothing climatological.

    We do NOT say "the prevailing wind here pushes field goals wide."
    Prevailing wind is a long-run average and says nothing about any
    specific Saturday. Dressing an average up as a game-day insight is
    wrong, and a meteorologist's site should not do it.

    We DO say "a west wind at this stadium crosses the field; a north wind
    runs goal to goal." That is a fact about the geometry of the venue. It
    is true on every date, it is never a forecast, and combined with the
    live forecast on the same page it is the piece a reader cannot get
    from a generic weather site.
"""

from __future__ import annotations

from typing import Optional


# Compass sectors for describing a bearing in words. 16-point rose, matching
# the 22.5-degree convention the bearings themselves were recorded in.
_POINTS = [
    (0, "north"), (22.5, "north-northeast"), (45, "northeast"),
    (67.5, "east-northeast"), (90, "east"), (112.5, "east-southeast"),
    (135, "southeast"), (157.5, "south-southeast"), (180, "south"),
    (202.5, "south-southwest"), (225, "southwest"), (247.5, "west-southwest"),
    (270, "west"), (292.5, "west-northwest"), (315, "northwest"),
    (337.5, "north-northwest"), (360, "north"),
]

ROOF_LABELS = {
    "open": "Open-air",
    "retractable": "Retractable roof",
    "fixed_dome": "Fixed dome",
    "fixed_canopy": "Fixed canopy",
}


def compass_word(deg: Optional[float]) -> Optional[str]:
    """Nearest 16-point compass word for a bearing in degrees."""
    if deg is None:
        return None
    deg = float(deg) % 360
    best = min(_POINTS, key=lambda p: abs(p[0] - deg))
    return best[1]


def axis_words(bearing: Optional[float]) -> Optional[tuple[str, str]]:
    """The two compass words describing the field's axis.

    A field is an axis, not a direction, so 0 and 180 describe the same
    field. Returns the pair (e.g. ("north", "south")) for readable copy.
    """
    if bearing is None:
        return None
    a = compass_word(bearing)
    b = compass_word((float(bearing) + 180) % 360)
    return (a, b)


def orientation_sentence(bearing: Optional[float], roof: Optional[str],
                         stadium_name: str) -> Optional[str]:
    """One factual sentence about how the field is laid out."""
    if (roof or "") == "fixed_dome":
        return (f"{stadium_name} is a fixed dome, so wind and precipitation "
                f"do not reach the field. Field orientation has no weather "
                f"effect here.")
    pair = axis_words(bearing)
    if not pair:
        return None
    a, b = pair
    return (f"The field at {stadium_name} runs {a} to {b} "
            f"({int(round(float(bearing) % 180))} degrees). Endzones sit at "
            f"the {a} and {b} ends.")


def wind_reading_rows(bearing: Optional[float]) -> list[dict]:
    """How to read each wind direction against THIS field.

    Geometry only. For each of the eight primary compass directions, we
    state whether a wind from that direction runs along the field axis or
    across it. No claim is made about how often that wind occurs, or what
    it will do to any particular kick or pass.

    'Along the field' means roughly goal to goal. 'Across the field' means
    roughly sideline to sideline. Anything in between is called diagonal,
    because pretending to more precision than the geometry supports would
    be its own kind of overreach.
    """
    if bearing is None:
        return []
    field = float(bearing) % 180
    rows = []
    for deg, word in [(0, "North"), (45, "Northeast"), (90, "East"),
                      (135, "Southeast"), (180, "South"), (225, "Southwest"),
                      (270, "West"), (315, "Northwest")]:
        # Angle between the wind line and the field axis, folded to 0-90.
        diff = abs((deg % 180) - field)
        diff = min(diff, 180 - diff)
        if diff <= 30:
            rel = "Along the field, goal to goal"
        elif diff >= 60:
            rel = "Across the field, sideline to sideline"
        else:
            rel = "Diagonal to the field"
        rows.append({"direction": f"{word} wind", "effect": rel})
    return rows


def build_facts(stadium: dict, team_name: str) -> list[tuple]:
    """Fact rows for the landing page. Only fields we actually hold."""
    roof = stadium.get("roof") or "open"
    facts = [
        ("Team", team_name or ""),
        ("City", stadium.get("city") or ""),
        ("Roof", ROOF_LABELS.get(roof, "Open-air")),
    ]
    cap = stadium.get("cap")
    if cap:
        facts.append(("Capacity", f"{cap:,}"))
    bearing = stadium.get("field_bearing_degrees")
    if bearing is not None and roof != "fixed_dome":
        pair = axis_words(bearing)
        if pair:
            facts.append(("Field orientation",
                          f"{pair[0].title()} to {pair[1].title()} "
                          f"({int(round(float(bearing) % 180))}°)"))
    return facts


def build_sections(stadium: dict, stadium_name: str,
                   hand_written: Optional[dict] = None) -> list[tuple]:
    """Prose sections. Hand-written copy is used when it exists; the
    generated orientation text is added either way because it is
    stadium-specific and the hand-written entries do not cover it."""
    sections = []
    if hand_written:
        if hand_written.get("intro"):
            sections.append(("Overview", hand_written["intro"]))
        if hand_written.get("angle"):
            sections.append(("Weather angle", hand_written["angle"]))

    sent = orientation_sentence(stadium.get("field_bearing_degrees"),
                                stadium.get("roof"), stadium_name)
    if sent:
        body = sent
        if (stadium.get("roof") or "") != "fixed_dome":
            body += (" Wind direction on a forecast is the direction the "
                     "wind is coming from, so use the table below to read "
                     "it against this field rather than against a compass.")
        sections.append(("Field orientation", body))
    return sections


# ── Full-coverage slug map ────────────────────────────────────────────────
#
# stadium_content.py covers 25 stadiums. This builds a slug map for all 134
# FBS venues, reusing the hand-written slug wherever one exists so no
# existing URL changes (those pages are indexed; changing their slugs would
# throw away whatever ranking they have).
#
# Collision handling matters here: there are FOUR different "Memorial
# Stadium" entries (Lincoln NE, Champaign IL, Clemson SC, Bloomington IN),
# plus repeated "Alumni Stadium" and similar. Slugifying on name alone
# would collapse them onto one URL and point three schools at the wrong
# venue. Same failure that produced wrong field bearings when matching was
# done on city alone.

import re as _re


def _slugify(text: str) -> str:
    s = (text or "").lower()
    s = s.replace("&", " and ")
    s = _re.sub(r"[^a-z0-9]+", "-", s)
    return _re.sub(r"-+", "-", s).strip("-")


def build_stadium_slug_map() -> dict:
    """{slug: {"name", "stadium", "team", "hand_written"}} for all 134."""
    from .venues import FBS_TEAMS
    from .stadium_content import STADIUM_CONTENT_CFB

    # Match hand-written copy on TEAM, not on stadium name.
    #
    # stadium_content.py is keyed by a display name that sometimes differs
    # from venues.py — "Memorial Stadium (Clemson)" vs "Memorial Stadium".
    # Matching on name therefore did two wrong things at once: it failed to
    # find Clemson's and Nebraska's entries at all, and it would have handed
    # Clemson's copy to Illinois, Indiana and Nebraska, since all four share
    # the bare name "Memorial Stadium". Every entry carries a full team name
    # and team names are unique, so that is the safe key.
    by_team = {}
    for _name, entry in STADIUM_CONTENT_CFB.items():
        team = (entry or {}).get("team")
        if team:
            by_team[team] = entry

    used, out = {}, {}
    # Deterministic order so slugs never shuffle between deploys.
    teams = sorted(FBS_TEAMS.values(), key=lambda t: (t.get("short") or ""))
    for t in teams:
        s = t.get("stadium") or {}
        name = s.get("name")
        if not name:
            continue
        hw = by_team.get(t.get("name") or "")
        if hw and hw.get("slug"):
            slug = hw["slug"]                      # preserve indexed URLs
        else:
            base = _slugify(name)
            slug = base
            if slug in used:
                # Disambiguate with the team, not the city: two schools can
                # share a city name (Columbia MO / Columbia SC) but not a
                # team name.
                slug = f"{base}-{_slugify(t.get('short') or '')}"
                n = 2
                while slug in used:
                    slug = f"{base}-{_slugify(t.get('short') or '')}-{n}"
                    n += 1
        used[slug] = True
        out[slug] = {
            "name": name,
            "stadium": s,
            "team": t.get("name") or t.get("short") or "",
            "team_short": t.get("short") or "",
            "hand_written": hw,
        }
    return out


STADIUM_SLUG_MAP = build_stadium_slug_map()


# ── Next home game at a venue ─────────────────────────────────────────────
#
# WHY: a visitor who lands on /ncaaf/stadium/<x> from a search wants the
# forecast, not a geometry lesson. Without this the page is an SEO trap —
# it ranks, someone clicks, and there is nothing they came for. That is bad
# for the reader and it is also what makes a page look thin to Google.
#
# The live slate only covers ~7 days, so for most stadiums most of the year
# it has nothing. fetch_cfbd_games_for_year() already pulls the WHOLE season
# in one disk-cached call for the slate builder, so we can answer "when do
# they next play here" year-round at zero additional API cost.

import threading as _threading
from datetime import datetime as _dt, timezone as _tz

_venue_next_lock = _threading.Lock()
_venue_next_cache: dict = {"built_at": None, "by_team": {}}
_VENUE_NEXT_TTL_SEC = 3600


def _season_year() -> int:
    """CFB season year. A January game belongs to the previous season."""
    now = _dt.now(_tz.utc)
    return now.year - 1 if now.month == 1 else now.year


def _build_next_home_game_index() -> dict:
    """{home_team_name: {"date", "opponent", "kickoff_utc"}} for the next
    future home game of each team. Built from the cached season schedule."""
    from .cfbd_client import fetch_cfbd_games_for_year
    out = {}
    try:
        raw_games = fetch_cfbd_games_for_year(_season_year()) or []
    except Exception as e:
        print(f"[cfb.stadium_facts] season fetch failed: "
              f"{type(e).__name__}: {e}", flush=True)
        return out

    now = _dt.now(_tz.utc)
    for g in raw_games:
        start = g.get("startDate") or g.get("start_date")
        home = g.get("homeTeam") or g.get("home_team")
        away = g.get("awayTeam") or g.get("away_team")
        if not (start and home and away):
            continue
        try:
            ko = _dt.fromisoformat(str(start).replace("Z", "+00:00"))
            if ko.tzinfo is None:
                ko = ko.replace(tzinfo=_tz.utc)
        except Exception:
            continue
        if ko < now:
            continue
        prev = out.get(home)
        if prev is None or ko < prev["kickoff_utc"]:
            out[home] = {"kickoff_utc": ko, "opponent": away,
                         "date": ko.strftime("%b %-d")}
    return out


def next_home_game(team_name: str) -> Optional[dict]:
    """Next scheduled home game for a team, or None.

    Cached for an hour. Returns date + opponent only; there is no forecast
    attached, because a forecast weeks out would be worse than none. The
    page links through to the hub for the actual numbers.
    """
    if not team_name:
        return None
    with _venue_next_lock:
        built = _venue_next_cache["built_at"]
        fresh = built and (_dt.now(_tz.utc) - built).total_seconds() < _VENUE_NEXT_TTL_SEC
        if not fresh:
            _venue_next_cache["by_team"] = _build_next_home_game_index()
            _venue_next_cache["built_at"] = _dt.now(_tz.utc)
        return (_venue_next_cache["by_team"] or {}).get(team_name)
