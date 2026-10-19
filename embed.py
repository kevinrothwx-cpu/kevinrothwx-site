"""embed — per-game forecast card for partner articles, via iframe (2026-10-19).

First consumer: Covers. Partner doc: docs/EMBED_v1.md (safe to send).

WHY AN IFRAME, NOT A JAVASCRIPT EMBED
    A script embed writes our forecast text into the partner's page, so
    search engines credit that content to them. An iframe keeps the content
    on a mysportsweather.com URL. Partners also paste a plain attribution
    link under the iframe (see the doc); that link sits in their article HTML.

SEO GUARDRAILS (Kevin: "positive changes only")
    - Every card carries noindex (header + meta), so these never compete
      with the real game pages. Not in robots.txt Disallow on purpose:
      Google has to be able to fetch the card to see the noindex.
    - /embed/ is listed in app._hidden_from_google, which keeps it off the
      sitemap and the IndexNow list.
    - No canonical tag (noindex + canonical sends mixed signals).
    - The link inside the card goes to the real game page, branded text.

LOAD
    Reads the warm caches only (find_game_in_slate uses allow_build=False),
    so embed traffic can never trigger NWS / HRRR / Odds API calls. Cards
    get the site's normal public max-age=60 edge cache. No odds, no
    write-ups: the same weather-only shaping as partner_api.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from flask import Blueprint, Response, render_template, request

embed_bp = Blueprint("embed", __name__)

SITE = "https://mysportsweather.com"
EASTERN = ZoneInfo("America/New_York")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SLUG_RE = re.compile(r"^[a-z0-9-]{1,120}$")

SPORTS = {
    # url segment: (partner_api sport key, hub path, label)
    "nfl":   ("nfl", "/nfl", "NFL"),
    "ncaaf": ("cfb", "/ncaaf", "College Football"),
}

_PRECIP_LABEL = {"snow": "Snow", "mix": "Wintry mix", "freezing": "Freezing rain"}


def _find(sport_seg: str, date_str: str, slug: str):
    if sport_seg == "nfl":
        from nfl.cache import find_game_in_slate
    else:
        from cfb.cache import find_game_in_slate
    return find_game_in_slate(date_str, slug)


def _parse_utc(iso):
    if not iso:
        return None
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _et(dt, fmt):
    if not dt:
        return ""
    return dt.astimezone(EASTERN).strftime(fmt)


def _hour_label(dt):
    if not dt:
        return ""
    local = dt.astimezone(EASTERN)
    h = local.hour % 12 or 12
    return f"{h} {'AM' if local.hour < 12 else 'PM'}"


def _precip_label(ptype):
    return _PRECIP_LABEL.get((ptype or "").lower(), "Rain")


def _team_name(raw_team: dict, shaped_team: dict, prefer_short: bool) -> str:
    """NFL: full name ("Houston Texans"). CFB: short school name ("Ohio
    State"), since full CFB names ("Ohio State Buckeyes") crowd the card."""
    raw_team = raw_team or {}
    first = ("short", "name") if prefer_short else ("name", "short")
    return (raw_team.get(first[0]) or raw_team.get(first[1])
            or shaped_team.get("name") or shaped_team.get("abbrev") or "TBD")


def _card_context(sport_seg, date_str, slug, raw):
    from partner_api import _game
    from wind_gusts import gust_is_notable

    sport_key, hub, label = SPORTS[sport_seg]
    shaped = _game(raw, sport_key)
    kickoff = _parse_utc(shaped.get("kickoff_utc"))
    venue = shaped.get("venue") or {}

    ko = shaped.get("kickoff_forecast") or None
    if ko:
        ko = dict(ko)
        ko["show_gust"] = gust_is_notable(ko.get("wind_mph"), ko.get("gust_mph"))
        ko["precip_label"] = _precip_label(ko.get("precip_type"))

    rows = [r for r in shaped.get("hourly") or [] if r.get("in_game")]
    if not rows and kickoff:
        rows = [r for r in shaped.get("hourly") or []
                if (_parse_utc(r.get("time_utc")) or kickoff) >= kickoff]
    hourly = []
    for r in rows[:5]:
        hourly.append({
            "label": _hour_label(_parse_utc(r.get("time_utc"))),
            "temp_f": r.get("temp_f"),
            "wind_mph": r.get("wind_mph"),
            "wind_dir": r.get("wind_dir"),
            "precip_pct": r.get("precip_pct"),
        })

    return {
        "sport_label": label,
        "away": _team_name(raw.get("away"), shaped.get("away") or {},
                          sport_seg == "ncaaf"),
        "home": _team_name(raw.get("home"), shaped.get("home") or {},
                          sport_seg == "ncaaf"),
        "kickoff_str": _et(kickoff, "%a, %b %-d · %-I:%M %p ET"),
        "venue_name": venue.get("name") or "",
        "venue_city": venue.get("city") or "",
        "roof": venue.get("roof_type") or "open",
        "status": shaped.get("forecast_status"),
        "ko": ko,
        "game_max": shaped.get("game_max_precip_pct"),
        "hourly": hourly,
        "game_url": f"{SITE}/{sport_seg}/{date_str}/{slug}",
        "hub_url": f"{SITE}{hub}",
    }


def _finish(html: str, status: int = 200, cache: str | None = None):
    resp = Response(html, status=status, mimetype="text/html")
    resp.headers["X-Robots-Tag"] = "noindex"
    # Explicitly framable by any site. Nothing else on the site sends
    # X-Frame-Options, but say it out loud here in case that ever changes.
    resp.headers["Content-Security-Policy"] = "frame-ancestors *"
    if cache:
        resp.headers["Cache-Control"] = cache
    return resp


@embed_bp.route("/embed/<sport_seg>/<date_str>/<slug>")
def embed_card(sport_seg, date_str, slug):
    if sport_seg not in SPORTS:
        return _finish("Not found", 404, "no-store")
    _, hub, label = SPORTS[sport_seg]

    raw = None
    if _DATE_RE.match(date_str or "") and _SLUG_RE.match(slug or ""):
        try:
            raw = _find(sport_seg, date_str, slug)
        except Exception as e:
            print(f"[embed] lookup failed {sport_seg}/{date_str}/{slug}: "
                  f"{type(e).__name__}: {e}", flush=True)

    ref = urlparse(request.headers.get("Referer") or "").netloc or "-"

    if not raw:
        # Game is over, not on the slate yet, or a bad URL. Old articles
        # keep their iframes forever, so show a small card that sends
        # readers to the live hub instead of a broken box. 404 status, but
        # edge-cacheable for 5 minutes so old articles don't hammer origin.
        html = render_template("embed/card.html", missing=True,
                               sport_label=label, hub_url=f"{SITE}{hub}")
        return _finish(html, 404, "public, max-age=300")

    try:
        ctx = _card_context(sport_seg, date_str, slug, raw)
    except Exception as e:
        print(f"[embed] card failed {sport_seg}/{date_str}/{slug}: "
              f"{type(e).__name__}: {e}", flush=True)
        html = render_template("embed/card.html", missing=True,
                               sport_label=label, hub_url=f"{SITE}{hub}")
        return _finish(html, 200, "no-store")

    # One line per origin hit (the edge cache absorbs repeats), so Kevin can
    # see in the Render logs which sites are showing cards.
    print(f"[embed] {sport_seg}/{date_str}/{slug} ref={ref}", flush=True)
    return _finish(render_template("embed/card.html", missing=False, **ctx))


# ── Picker: hidden page for partner writers (2026-10-19) ─────────────────
# Lists the current slate with a "Copy embed code" button per game so
# nobody has to hand-build URLs. Not linked anywhere on the site, noindex,
# nofollow, out of the sitemap (/embed/ is in app._hidden_from_google).
# Reads warm caches only, like the cards.

def _picker_games(sport_seg):
    if sport_seg == "nfl":
        from nfl.cache import get_nfl_slate
        games, _ = get_nfl_slate(allow_build=False)
        date_key = "kickoff_date_eastern"
    else:
        from cfb.cache import get_cfb_slate
        games, _ = get_cfb_slate(allow_build=False)
        date_key = "date_local"
    out = []
    for g in games or []:
        try:
            day, slug = g.get(date_key), g.get("slug")
            if not day or not slug:
                continue
            ko = g.get("kickoff_utc")
            ko = ko if isinstance(ko, datetime) else _parse_utc(ko)
            venue = g.get("venue") or {}
            short = sport_seg == "ncaaf"
            out.append({
                "away": _team_name(g.get("away"), {}, short),
                "home": _team_name(g.get("home"), {}, short),
                "kickoff_str": _et(ko, "%a, %b %-d · %-I:%M %p ET") if ko else "Time TBD",
                "sort": ko.timestamp() if ko else 9e12,
                "venue": venue.get("name") or "",
                "page_url": f"{SITE}/{sport_seg}/{day}/{slug}",
                "embed_url": f"{SITE}/embed/{sport_seg}/{day}/{slug}",
            })
        except Exception as e:
            print(f"[embed] picker skipped a {sport_seg} game: {type(e).__name__}: {e}", flush=True)
    out.sort(key=lambda x: x["sort"])
    return out


def _picker_response(html):
    resp = Response(html, mimetype="text/html")
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    resp.headers["Cache-Control"] = "no-store"
    return resp


@embed_bp.route("/embed")
@embed_bp.route("/embed/")
def embed_index():
    return _picker_response(render_template("embed/picker.html", index=True,
                                            sports=[(k, v[2]) for k, v in SPORTS.items()]))


@embed_bp.route("/embed/<sport_seg>")
def embed_picker(sport_seg):
    if sport_seg not in SPORTS:
        return _finish("Not found", 404, "no-store")
    try:
        games = _picker_games(sport_seg)
    except Exception as e:
        print(f"[embed] picker failed for {sport_seg}: {type(e).__name__}: {e}", flush=True)
        games = []
    return _picker_response(render_template(
        "embed/picker.html", index=False, sport_seg=sport_seg,
        sport_label=SPORTS[sport_seg][2], games=games,
        sports=[(k, v[2]) for k, v in SPORTS.items()]))


def register(app):
    app.register_blueprint(embed_bp)


# EOF-CANARY 2026-10-19-embed
