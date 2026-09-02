"""landing_index.py — internal-link index for the evergreen landing pages.

WHY THIS EXISTS (2026-09-02)
    The site has ~380 evergreen landing pages — one per stadium, team,
    track, course and venue across every sport. An audit found that
    essentially NOTHING linked to them:

        /nfl/team/*      linked only from other landing pages
        /ncaaf/stadium/* linked only from other landing pages
        /mls/team/*      linked from nothing at all
        the sport hubs   linked to ZERO landing pages
        the homepage     linked to ZERO landing pages

    They were orphans. Google can discover an orphan page from a sitemap,
    but orphans routinely sit in "Discovered - currently not indexed"
    forever, because no internal link signals that the page matters. That
    is the likely reason Search Console showed 45 indexed pages against
    ~500 live ones.

    This module builds, once at import, a per-sport index of every landing
    page that actually exists. templates/_landing_index.html renders it at
    the bottom of each sport hub, so every landing page gets a real
    internal link from a crawled, indexed page.

DESIGN NOTES
    - Built ONCE at import, not per request. The content dicts are static
      module-level data; rebuilding per request would be pure waste on a
      context processor that runs on every page render.
    - Only emits links for pages that EXIST. CFB has 134 teams but only 25
      stadium landing pages, so linking every stadium would manufacture
      109 internal 404s — worse than the orphan problem it fixes.
    - Sorted by display label so the rendered block is stable between
      deploys. A link list that reshuffles on every render looks like
      churn to a crawler.
"""

from __future__ import annotations


def _rows(content: dict, url_prefix: str, label_key: str | None = None) -> list[dict]:
    """Turn a CONTENT dict into sorted {label, url} rows.

    The dicts are keyed by display name (e.g. "Michigan Stadium") and carry
    a 'slug'. Some also carry a 'team' we can use for a friendlier label.
    """
    out = []
    for name, entry in (content or {}).items():
        slug = (entry or {}).get("slug")
        if not slug:
            continue
        label = name
        if label_key:
            alt = (entry or {}).get(label_key)
            if alt:
                label = f"{alt} — {name}"
        out.append({"label": label, "url": f"{url_prefix}/{slug}"})
    out.sort(key=lambda r: r["label"].lower())
    return out


def build_landing_index() -> dict:
    """{sport_key: [{heading, rows}, ...]} for every sport with landings."""
    # Imported here rather than at module top so this file stays importable
    # in isolation (tests, tooling) even if a sport module is unavailable.
    # Import paths mirror app.py exactly — several of these are aliased
    # there (nfl.stadium_content exports STADIUM_CONTENT, not
    # NFL_STADIUM_CONTENT), and MLS/Prem/IPL consolidate team+venue into
    # a single content module rather than two.
    from mlb.stadium_content import STADIUM_CONTENT
    from mlb.team_content import TEAM_CONTENT
    from nfl.stadium_content import STADIUM_CONTENT as NFL_STADIUM_CONTENT
    from nfl.team_content import TEAM_CONTENT_NFL
    from cfb.stadium_content import STADIUM_CONTENT_CFB
    from nascar.track_content import TRACK_CONTENT
    from golf.course_content import COURSE_CONTENT
    from mls.content import TEAM_CONTENT_MLS, STADIUM_CONTENT_MLS
    from prem.content import TEAM_CONTENT_PREM, STADIUM_CONTENT_PREM
    from ipl.content import TEAM_CONTENT_IPL, GROUND_CONTENT_IPL
    from tennis.venue_content import VENUE_CONTENT as TENNIS_VENUE_CONTENT

    return {
        "mlb": [
            {"heading": "MLB ballpark weather guides",
             "rows": _rows(STADIUM_CONTENT, "/mlb/stadium")},
            {"heading": "MLB team weather guides",
             "rows": _rows(TEAM_CONTENT, "/mlb/team")},
        ],
        "nfl": [
            {"heading": "NFL stadium weather guides",
             "rows": _rows(NFL_STADIUM_CONTENT, "/nfl/stadium")},
            {"heading": "NFL team weather guides",
             "rows": _rows(TEAM_CONTENT_NFL, "/nfl/team")},
        ],
        "ncaaf": [
            {"heading": "College football stadium weather guides",
             "rows": _rows(STADIUM_CONTENT_CFB, "/ncaaf/stadium")},
        ],
        "nascar": [
            {"heading": "NASCAR track weather guides",
             "rows": _rows(TRACK_CONTENT, "/nascar/track")},
        ],
        "golf": [
            {"heading": "PGA Tour course weather guides",
             "rows": _rows(COURSE_CONTENT, "/golf/course")},
        ],
        "mls": [
            {"heading": "MLS team weather guides",
             "rows": _rows(TEAM_CONTENT_MLS, "/mls/team")},
            {"heading": "MLS stadium weather guides",
             "rows": _rows(STADIUM_CONTENT_MLS, "/mls/stadium")},
        ],
        "prem": [
            {"heading": "Premier League club weather guides",
             "rows": _rows(TEAM_CONTENT_PREM, "/prem/team")},
            {"heading": "Premier League stadium weather guides",
             "rows": _rows(STADIUM_CONTENT_PREM, "/prem/stadium")},
        ],
        "ipl": [
            {"heading": "IPL franchise weather guides",
             "rows": _rows(TEAM_CONTENT_IPL, "/ipl/team")},
            {"heading": "IPL ground weather guides",
             "rows": _rows(GROUND_CONTENT_IPL, "/ipl/ground")},
        ],
        "tennis": [
            {"heading": "Grand Slam venue weather guides",
             "rows": _rows(TENNIS_VENUE_CONTENT, "/tennis/venue")},
        ],
    }


# Built once at import. See DESIGN NOTES above.
try:
    LANDING_INDEX = build_landing_index()
except Exception as _e:  # pragma: no cover
    # A missing content module must not take the whole site down over a
    # link block. Degrade to no index rather than failing to boot.
    print(f"[landing_index] build failed, link blocks disabled: "
          f"{type(_e).__name__}: {_e}", flush=True)
    LANDING_INDEX = {}


def landing_index_for(sport: str) -> list[dict]:
    """Sections for one sport, or [] if that sport has no landing pages."""
    return LANDING_INDEX.get(sport) or []


def total_links() -> int:
    """Diagnostic — how many landing pages this index links to."""
    return sum(len(sec["rows"]) for secs in LANDING_INDEX.values() for sec in secs)
