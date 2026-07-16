"""
kevinrothwx.com — Flask app for Kevin Roth's personal authority hub.
Phase 1: marketing, bio, press, evergreen sport-weather explainers.
Phase 2 (now): automated MLB weather slate + per-game pages.
Phase 3 (later): admin UI for manual write-ups (storage hook is ready).
"""

import os
import time
import functools
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, abort, Response,
)

from mlb.cache import get_slate, start_warmer
from mlb.slate import precip_color, precip_icon
from mlb.storage import save_writeup, attach_writeups_to_slate, get_writeup
from mlb.wind import wind_compass
from mlb.park_metadata import PARK_METADATA
from mlb.stadium_content import STADIUM_CONTENT, STADIUM_BY_SLUG
from mlb.team_content import (
    TEAM_CONTENT, TEAM_BY_SLUG, TEAM_TO_DIVISION, DIVISIONS,
)
from nfl.venues import NFL_TEAMS
from nfl.stadium_content import (
    STADIUM_CONTENT as NFL_STADIUM_CONTENT,
    STADIUM_BY_SLUG_NFL,
)
from nfl.team_content import (
    TEAM_CONTENT_NFL, TEAM_BY_SLUG_NFL,
    TEAM_TO_DIVISION_NFL, DIVISIONS_NFL,
)
from nascar.tracks import NASCAR_TRACKS
from nascar.track_content import TRACK_CONTENT, TRACK_BY_SLUG
from golf.courses import PGA_COURSES
from golf.course_content import COURSE_CONTENT, COURSE_BY_SLUG
from cfb.venues import FBS_TEAMS
from cfb.stadium_content import STADIUM_CONTENT_CFB, STADIUM_BY_SLUG_CFB
from mls.venues import MLS_TEAMS
from mls.content import (
    TEAM_CONTENT_MLS, TEAM_BY_SLUG_MLS,
    STADIUM_CONTENT_MLS, STADIUM_BY_SLUG_MLS,
    TEAM_TO_CONF_MLS,
)
from tennis.venue_content import VENUE_CONTENT as TENNIS_VENUE_CONTENT, VENUE_BY_SLUG_TENNIS
from prem.content import (
    TEAM_CONTENT_PREM, TEAM_BY_SLUG_PREM,
    STADIUM_CONTENT_PREM, STADIUM_BY_SLUG_PREM,
)
from ipl.content import (
    TEAM_CONTENT_IPL, TEAM_BY_SLUG_IPL,
    GROUND_CONTENT_IPL, GROUND_BY_SLUG_IPL,
)

from worldcup.cache import get_matchday, start_warmer as start_wc_warmer
from worldcup.schedule import match_slug as wc_match_slug
from worldcup.storage import (
    save_writeup as wc_save_writeup,
    get_writeup as wc_get_writeup,
    attach_writeups_to_slate as wc_attach_writeups,
)

from golf.cache import get_pga_slate, start_warmer as start_golf_warmer
from golf.storage import (
    save_writeup as golf_save_writeup,
    get_writeup as golf_get_writeup,
    attach_writeups_to_slate as golf_attach_writeups,
)

from nascar.cache import get_nascar_slate, start_warmer as start_nascar_warmer
from nascar.storage import (
    save_writeup as nascar_save_writeup,
    get_writeup as nascar_get_writeup,
    attach_writeups_to_slate as nascar_attach_writeups,
)

from cws.cache import get_cws_slate, start_warmer as start_cws_warmer, is_in_window as cws_in_window
from cws.storage import (
    save_writeup as cws_save_writeup,
    get_writeup as cws_get_writeup,
    attach_writeups_to_slate as cws_attach_writeups,
)
from cws.overcast_impact import render_impact_strip as _cws_render_impact_strip

from tennis.cache import (
    get_active_slam_slate, get_slam_slate_by_id,
    start_warmer as start_tennis_warmer,
)
from tennis.schedule import (
    active_slam, next_slam, is_any_slam_active, get_slam_by_id,
)
from tennis.matches import get_matches_for_day as tennis_matches_for_day, format_local_time as tennis_local_time
from tennis.daily_summary import generate_daily_summary as tennis_daily_summary

from cfb.cache import (
    get_cfb_slate, start_warmer as start_cfb_warmer,
    find_game_in_slate as find_cfb_game,
    frozen_count as cfb_frozen_count,
)
from cfb.analysis import generate_analysis as cfb_generate_analysis
from cfb.nws_client import circuit_status as cfb_nws_circuit_status, gridpoint_cache_size as cfb_gridpoint_cache_size
from cfb.slate import _hourly_window as cfb_hourly_window
from hrrr import get_hrrr_periods

from mls.cache import (
    get_mls_slate, start_warmer as start_mls_warmer,
    find_match_in_slate as find_mls_match,
    frozen_count as mls_frozen_count,
)
from mls.analysis import generate_analysis as mls_generate_analysis
from mls.storage import (
    save_writeup as mls_save_writeup,
    get_writeup as mls_get_writeup,
    attach_writeups_to_slate as mls_attach_writeups,
)

from nfl.cache import (
    get_nfl_slate, start_warmer as start_nfl_warmer,
    find_game_in_slate as find_nfl_game,
    frozen_count as nfl_frozen_count,
)
from nfl.analysis import generate_analysis as nfl_generate_analysis
from nfl.slate import _hourly_window as nfl_hourly_window
from nfl.storage import (
    save_writeup as nfl_save_writeup,
    get_writeup as nfl_get_writeup,
    attach_writeups_to_slate as nfl_attach_writeups,
)

from horse.cache import get_horse_slate, start_warmer as start_horse_warmer
from horse.schedule import get_stakes_race as get_horse_stakes_race
from horse.slate import build_stakes_day as build_horse_stakes_day

from prem.cache import (
    get_epl_slate as get_prem_slate,
    start_warmer as start_prem_warmer,
    find_match_in_slate as find_prem_match,
    frozen_count as prem_frozen_count,
)
from prem.storage import (
    save_writeup as prem_save_writeup,
    get_writeup as prem_get_writeup,
    attach_writeups_to_slate as prem_attach_writeups,
)

from indexnow import INDEXNOW_KEY, notify as indexnow_notify
from nws_health import snapshot as nws_health_snapshot

import api as msw_api

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

# Templates get the precip color/icon helpers as filters
app.jinja_env.filters["precip_color"] = precip_color
app.jinja_env.filters["precip_icon"]  = precip_icon
app.jinja_env.filters["wind_compass"] = wind_compass


def md_bold(text):
    """Lightweight Markdown bold filter for writeup bodies.

    Converts **double-asterisks** to <strong>...</strong>. HTML-escapes
    everything else first so user-supplied text can never inject markup
    (even though only Kevin writes these — defense in depth). Returns a
    Markup so the asterisks-stripped HTML renders correctly.

    Usage in template: {{ writeup.text|md_bold }}
    No filter chaining with |safe needed — the return value is already safe.
    """
    if not text:
        return ""
    import re as _re
    from markupsafe import Markup, escape
    safe = str(escape(text))
    # Match **bold** but only on a single line (no \n inside), and require
    # at least one char between the asterisk pairs. Non-greedy so two
    # separate **bold** **runs** on the same line both render correctly.
    safe = _re.sub(r"\*\*([^\*\n]+?)\*\*", r"<strong>\1</strong>", safe)
    return Markup(safe)


app.jinja_env.filters["md_bold"] = md_bold


# Expose timedelta to Jinja templates so per-sport detail pages can compute
# schema.org endDate from startDate + duration (e.g. first_pitch_utc + 3h).
# Used inside <script type="application/ld+json"> blocks in game/match/race
# detail templates. Keeps the schema fully template-side without needing
# Python pre-computation of every event's end time.
from datetime import timedelta as _timedelta
app.jinja_env.globals["timedelta"] = _timedelta


def cws_impact_strip(forecast):
    """Render the OVERcast CWS weather-impact strip as safe HTML.
    Always returns a Markup string; on any error returns an empty Markup
    so the page renders cleanly even if the engine has a bad day."""
    from markupsafe import Markup
    if not forecast:
        return Markup("")
    try:
        html = _cws_render_impact_strip(
            temp=forecast.get("temp"),
            dew=forecast.get("dew"),
            wind_mph=forecast.get("wind_speed"),
            wind_dir_deg=forecast.get("wind_deg"),
        )
        return Markup(html)
    except Exception as e:
        print(f"[cws.impact] render failed: {e}", flush=True)
        return Markup("")


app.jinja_env.globals["cws_impact_strip"] = cws_impact_strip

EASTERN_TZ = ZoneInfo("America/New_York")

# Start the slate warmer thread on import (gunicorn imports app:app once per worker)
start_warmer()
start_wc_warmer()
start_golf_warmer()
start_nascar_warmer()
start_cws_warmer()
start_tennis_warmer()
start_cfb_warmer()
start_mls_warmer()
start_nfl_warmer()
start_horse_warmer()
start_prem_warmer()

# Register the JSON API blueprint (docs/FORECAST_API_CONTRACT_v1.md).
# Consumers: OVERcast NFL + OVERcast CFB. Auth via MSW_API_KEYS env var.
msw_api.register(app)


# ===== Multi-domain support: kevinrothwx.com (personal) + mysportsweather.com (product) =====
#
# The same Flask app serves both domains from one Render service. Hostname
# detection swaps the brand (header, canonical, schema.org) per request,
# and a before_request middleware 301-redirects sport sections from
# kevinrothwx.com to mysportsweather.com so old links keep working and
# link equity flows to the new product domain.

KEVINROTHWX_HOSTS = {"kevinrothwx.com", "www.kevinrothwx.com"}
MYSPORTSWEATHER_HOSTS = {"mysportsweather.com", "www.mysportsweather.com"}

# Sport sections that live on mysportsweather.com going forward. Requests
# for these on kevinrothwx.com get 301-redirected.
SPORT_PATH_PREFIXES = ("/mlb", "/cws", "/worldcup", "/golf", "/nascar", "/nfl", "/ncaaf", "/mls")
SPORT_PATH_EXACT = {"/mlb-weather", "/nfl-weather", "/pga-weather"}


def _normalize_host(host):
    """Strip port and lowercase a Host header value."""
    return (host or "").lower().split(":", 1)[0]


def get_site_brand(host):
    """Return brand info for the request's hostname. Templates use the
    returned values to render the correct header, canonical URL, OG tags,
    and schema.org markup for each domain."""
    h = _normalize_host(host)
    if h in MYSPORTSWEATHER_HOSTS:
        return {
            "brand_id":         "mysportsweather",
            "site_name":        "MySportsWeather",
            "site_subtitle":    "By Kevin Roth, Sports Meteorologist",
            "site_url":         "https://mysportsweather.com",
            "is_personal_site": False,
            "is_product_site":  True,
        }
    # Default: kevinrothwx.com (also covers dev/localhost).
    return {
        "brand_id":         "kevinrothwx",
        "site_name":        "Kevin Roth",
        "site_subtitle":    "Sports Meteorologist",
        "site_url":         "https://kevinrothwx.com",
        "is_personal_site": True,
        "is_product_site":  False,
    }


def _is_sport_path(path):
    """True if path belongs to a sport section that should live on
    mysportsweather.com only."""
    if path in SPORT_PATH_EXACT:
        return True
    return any(path == p or path.startswith(p + "/") for p in SPORT_PATH_PREFIXES)


@app.before_request
def redirect_sport_paths_to_product_site():
    """When a sport-section URL hits kevinrothwx.com, 301-redirect to the
    same path on mysportsweather.com. Personal pages (/, /about, /press,
    /contact, /overcast) stay on kevinrothwx.com. Admin paths stay on
    both for convenience.
    """
    h = _normalize_host(request.host)
    if h not in KEVINROTHWX_HOSTS:
        return None  # only redirect from kevinrothwx.com
    if not _is_sport_path(request.path):
        return None
    # Preserve query string if present
    suffix = request.path
    if request.query_string:
        suffix += "?" + request.query_string.decode("utf-8", errors="replace")
    return redirect("https://mysportsweather.com" + suffix, code=301)


@app.context_processor
def inject_globals():
    """Make a few values available in every template, including the
    hostname-aware brand info (site_name, site_url, is_personal_site, etc.)."""
    brand = get_site_brand(request.host if request else None)
    # GA4 measurement ID is per-hostname so each property gets its own data
    # stream. kevinrothwx.com uses GA_MEASUREMENT_ID (existing KevinRothWx
    # property); mysportsweather.com uses GA_MEASUREMENT_ID_MYSPORTSWEATHER
    # (new MySportsWeather property). Local dev leaves both unset, no tracking.
    if brand.get("brand_id") == "mysportsweather":
        ga_id = os.environ.get("GA_MEASUREMENT_ID_MYSPORTSWEATHER", "").strip()
    else:
        ga_id = os.environ.get("GA_MEASUREMENT_ID", "").strip()
    return {
        "current_year":     datetime.utcnow().year,
        "ga_measurement_id": ga_id,
        **brand,
    }


@app.context_processor
def inject_sport_nav():
    """Inject sport_counts so the sport-nav strip shows live indicators per sport."""
    counts = {}
    today = datetime.now(EASTERN_TZ).date()
    today_str = today.strftime("%Y-%m-%d")

    # MLB — today's game count (warmer keeps cache fresh)
    try:
        mlb_slate, _ = get_slate(today_str, allow_build=False)
        if mlb_slate:
            counts["mlb"] = str(len(mlb_slate))
    except Exception:
        pass

    # World Cup — count matches whose Eastern-Time date is today. Late-night
    # ET kickoffs (e.g. midnight ET) are technically the NEXT UTC day, so we
    # check today + tomorrow UTC slates and filter to ET-today. Previously
    # we showed a 3-day rolling total ("16") which was misleading on days
    # when only a few matches were actually scheduled for today.
    try:
        total_wc = 0
        for offset in (0, 1):
            d = (today + timedelta(days=offset)).strftime("%Y-%m-%d")
            wc_slate, _ = get_matchday(d, allow_build=False)
            if not wc_slate:
                continue
            for m in wc_slate:
                ko_dt = m.get("kickoff_utc_dt")
                if ko_dt is None:
                    continue
                if ko_dt.astimezone(EASTERN_TZ).date() == today:
                    total_wc += 1
        if total_wc > 0:
            counts["worldcup"] = str(total_wc)
    except Exception:
        pass

    # PGA — no badge by design (per Kevin). "2" tournaments was awkward; the
    # tab itself signals the section. If we want to differentiate "in progress"
    # later, "Live" during round days would be the move (mirrors CWS).
    # Intentionally not setting counts["pga"].

    # NASCAR — no badge by design (per Kevin). "Sun" day-of-week was treated
    # as redundant; people know NASCAR races are on Sunday. Intentionally
    # not setting counts["nascar"].

    # CWS — live during 10-day window. Window is controlled by CWS_2026_END
    # in cws/venue.py; once that date passes, cws_in_window returns False
    # and the badge auto-hides for the rest of the off-season.
    if cws_in_window():
        counts["cws"] = "Live"

    # Tennis — live during active Slam window. Same pattern as CWS:
    # is_any_slam_active() reflects the 4 hard-coded Slam date windows in
    # tennis/schedule.py. Auto-shows during Slams, hides between.
    if is_any_slam_active():
        counts["tennis"] = "Live"

    # NCAAF — during the season, show the game count for the upcoming/active
    # window. Off-season this returns 0 games and the badge stays hidden,
    # mirroring the NFL pattern.
    try:
        cfb_games, _ = get_cfb_slate(allow_build=False)
        if cfb_games:
            counts["ncaaf"] = str(len(cfb_games))
    except Exception:
        pass

    # NFL — count games whose Eastern date is today. Off-season returns 0
    # naturally and the badge stays hidden.
    try:
        nfl_games, _ = get_nfl_slate(allow_build=False)
        if nfl_games:
            today_nfl = sum(1 for g in nfl_games
                            if g.get("kickoff_date_eastern") == today_str)
            if today_nfl > 0:
                counts["nfl"] = str(today_nfl)
    except Exception:
        pass

    # MLS — count today's matches (Eastern). Late-night PT kickoffs roll
    # into the next UTC day, so we walk the full window and filter to
    # today-ET. Off-season (between MLS Cup and February preseason) this
    # naturally returns 0 and the badge stays hidden.
    try:
        mls_matches, _ = get_mls_slate(allow_build=False)
        if mls_matches:
            today_mls = 0
            for m in mls_matches:
                ko = m.get("kickoff_utc")
                if ko and ko.astimezone(EASTERN_TZ).date() == today:
                    today_mls += 1
            if today_mls > 0:
                counts["mls"] = str(today_mls)
    except Exception:
        pass

    # NFL — no badge during off-season (cleaner header).
    # The sport tab still shows; just no countdown number next to it.

    return {"sport_counts": counts}


# Optional: contact form email destination (set in Render env vars)
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "kevin@kevinrothwx.com")
SITE_URL = "https://kevinrothwx.com"


# ===== Marketing / static routes =====

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/press")
def press():
    return render_template("press.html")


@app.route("/overcast")
def overcast():
    return render_template("overcast.html")


@app.route("/mlb-weather")
def mlb_weather():
    # Provide the per-park content list so the hub page can index all
    # /mlb/stadium/<slug> landing pages (inbound links help discovery).
    stadium_list = [
        {"park_name": name, "slug": c["slug"]}
        for name, c in sorted(STADIUM_CONTENT.items())
    ]
    return render_template("mlb_weather.html", stadium_content_list=stadium_list)


# ===== MLB Weather deep-dive articles (long-form SEO content) =====
# Each article is nested under /mlb-weather/* to cluster topically and lift
# the whole /mlb-weather/* subpath in Google's topical authority scoring.
# Linked from the /mlb-weather evergreen page and /mlb hub, not homepage.

@app.route("/mlb-weather/wind-rules")
def mlb_weather_wind_rules():
    return render_template("mlb-weather/wind-rules.html", canonical_path="/mlb-weather/wind-rules")


@app.route("/mlb-weather/retractable-roofs")
def mlb_weather_retractable_roofs():
    return render_template("mlb-weather/retractable-roofs.html", canonical_path="/mlb-weather/retractable-roofs")


@app.route("/mlb-weather/stadium-rankings")
def mlb_weather_stadium_rankings():
    return render_template("mlb-weather/stadium-rankings.html", canonical_path="/mlb-weather/stadium-rankings")


@app.route("/nfl-weather")
def nfl_weather():
    return render_template("nfl_weather.html")


@app.route("/pga-weather")
def pga_weather():
    return render_template("pga_weather.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        organization = request.form.get("organization", "").strip()
        message = request.form.get("message", "").strip()

        # Simple honeypot for spam
        if request.form.get("website"):
            return redirect(url_for("contact_thanks"))

        if not name or not email or not message:
            flash("Please fill out name, email, and message.", "error")
            return render_template("contact.html",
                                   name=name, email=email,
                                   organization=organization, message=message)

        # TODO: actually send the email. For now we log to stdout.
        print(f"[CONTACT] From: {name} <{email}> ({organization})\n{message}", flush=True)

        return redirect(url_for("contact_thanks"))

    return render_template("contact.html")


@app.route("/contact/thanks")
def contact_thanks():
    return render_template("contact_thanks.html")


@app.route("/admin")
def admin():
    """Phase 2 stub. Noindex'd in the template."""
    return render_template("admin.html")


# ===== MLB weather forecasts =====

def _eastern_today() -> str:
    return datetime.now(EASTERN_TZ).strftime("%Y-%m-%d")


def _eastern_tomorrow() -> str:
    return (datetime.now(EASTERN_TZ) + timedelta(days=1)).strftime("%Y-%m-%d")


def _valid_date_str(date_str: str) -> bool:
    """Reject malformed dates and dates outside [yesterday, +7 days]."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return False
    today = datetime.now(EASTERN_TZ).date()
    return (today - timedelta(days=1)) <= d <= (today + timedelta(days=7))


def _render_mlb_slate(date_str, canonical_path):
    """Render the MLB slate for date_str with an explicit canonical URL.
    Used by all the MLB landing routes (/mlb, /mlb/today, /mlb/tomorrow,
    /mlb/<date>) so they render inline instead of redirecting — Google
    flagged the old redirect-to-date pattern as a Search Console error."""
    if not _valid_date_str(date_str):
        abort(404)
    slate, meta = get_slate(date_str)
    if slate is None:
        slate, meta = [], {"build_err": "Slate not yet built"}

    attach_writeups_to_slate(slate)

    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    pretty_date = d.strftime("%A, %B %-d")

    today = datetime.now(EASTERN_TZ).date()
    is_today    = (d == today)
    is_tomorrow = (d == today + timedelta(days=1))
    is_past     = (d < today)

    return render_template(
        "mlb/slate.html",
        slate=slate,
        meta=meta,
        date_str=date_str,
        pretty_date=pretty_date,
        is_today=is_today,
        is_tomorrow=is_tomorrow,
        is_past=is_past,
        canonical_path=canonical_path,
    )


@app.route("/mlb")
def mlb_root():
    """Render today's MLB slate inline. /mlb is the canonical hub URL
    Google should rank for 'MLB weather' queries."""
    return _render_mlb_slate(_eastern_today(), canonical_path="/mlb")


@app.route("/mlb/today")
def mlb_today():
    """Permalink alias for today's slate, canonicalizes back to /mlb."""
    return _render_mlb_slate(_eastern_today(), canonical_path="/mlb")


@app.route("/mlb/tomorrow")
def mlb_tomorrow():
    """Permalink alias for tomorrow's slate, self-canonical."""
    return _render_mlb_slate(_eastern_tomorrow(), canonical_path="/mlb/tomorrow")


@app.route("/mlb/<date_str>")
def mlb_slate(date_str):
    """Slate page for a specific date. Today's date canonicalizes back
    to /mlb so link equity accumulates on the stable hub URL instead of
    fragmenting across daily-rotating URLs."""
    today = _eastern_today()
    canonical = "/mlb" if date_str == today else f"/mlb/{date_str}"
    return _render_mlb_slate(date_str, canonical_path=canonical)


@app.route("/mlb/<date_str>/<slug>")
def mlb_game(date_str, slug):
    """Per-game detail page."""
    if not _valid_date_str(date_str):
        abort(404)
    slate, meta = get_slate(date_str)
    if slate is None:
        abort(404)

    game = next((g for g in slate if g["slug"] == slug), None)
    if not game:
        abort(404)

    game["writeup"] = get_writeup(game["game_pk"])

    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    pretty_date = d.strftime("%A, %B %-d")

    return render_template(
        "mlb/game.html",
        game=game,
        meta=meta,
        date_str=date_str,
        pretty_date=pretty_date,
    )


# ===== MLB stadium landing pages =====
# Evergreen per-ballpark weather guides. One page per current MLB stadium
# using PARK_METADATA (geographic facts) + STADIUM_CONTENT (per-park
# narrative Kevin can hand-verify).

def _cf_direction_label(bearing_degrees):
    """Convert CF bearing (0-359) into a short human direction label."""
    if bearing_degrees is None:
        return "—"
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int(((bearing_degrees + 11.25) % 360) / 22.5)
    return dirs[idx]


@app.route("/mlb/stadium/<slug>")
def mlb_stadium(slug):
    """Per-ballpark evergreen weather guide."""
    entry = STADIUM_BY_SLUG.get(slug)
    if not entry:
        abort(404)
    park_name, content = entry
    park = PARK_METADATA.get(park_name)
    if not park:
        abort(404)
    cf_direction = _cf_direction_label(park.get("cf_bearing_degrees"))
    # Look up today/tomorrow's game at this park so the page can show the
    # actual live forecast, not just a "go to /mlb" link. Users landing
    # from search for "Wrigley Field weather" get the forecast right here.
    next_game, next_date, next_when = _find_next_mlb_game_at_park(park_name)
    return render_template(
        "mlb/stadium.html",
        park_name=park_name,
        park=park,
        content=content,
        cf_direction=cf_direction,
        next_game=next_game,
        next_date=next_date,
        next_when=next_when,
        canonical_path=f"/mlb/stadium/{slug}",
    )


def _park_slug_for_team(team_name):
    """Look up stadium slug given a team name by scanning STADIUM_CONTENT."""
    for name, c in STADIUM_CONTENT.items():
        pm = PARK_METADATA.get(name, {})
        if pm.get("team") == team_name:
            return c["slug"]
    return None


def _find_next_mlb_game_for_team(team_name):
    """Return (game_dict, date_str, when_label) for today's or tomorrow's
    game featuring this team, or (None, None, None). Used on team pages to
    show today's forecast inline instead of just a link."""
    today = _eastern_today()
    tomorrow = _eastern_tomorrow()
    for date_str, label in [(today, "Today"), (tomorrow, "Tomorrow")]:
        slate, _ = get_slate(date_str, allow_build=False)
        if not slate:
            continue
        for g in slate:
            if g.get("home_name") == team_name or g.get("away_name") == team_name:
                return g, date_str, label
    return None, None, None


def _find_next_mlb_game_at_park(park_name):
    """Return (game_dict, date_str, when_label) for today's or tomorrow's
    game at this park. Used on stadium pages."""
    today = _eastern_today()
    tomorrow = _eastern_tomorrow()
    for date_str, label in [(today, "Today"), (tomorrow, "Tomorrow")]:
        slate, _ = get_slate(date_str, allow_build=False)
        if not slate:
            continue
        for g in slate:
            if g.get("venue") == park_name:
                return g, date_str, label
    return None, None, None


@app.route("/mlb/team/<slug>")
def mlb_team(slug):
    """Per-team evergreen weather playbook. Cross-links to the team's
    stadium page and to division-rival pages so the SEO graph is dense
    with natural internal links."""
    entry = TEAM_BY_SLUG.get(slug)
    if not entry:
        abort(404)
    team_name, content = entry
    park = PARK_METADATA.get(content["home_park"])
    if not park:
        abort(404)
    home_park_slug = STADIUM_CONTENT[content["home_park"]]["slug"]
    division = TEAM_TO_DIVISION.get(team_name, "")

    # Build division-rival cross-links (skip self)
    rivals = []
    for rival_team in DIVISIONS.get(division, []):
        if rival_team == team_name:
            continue
        rival_content = TEAM_CONTENT.get(rival_team)
        rival_park_slug = _park_slug_for_team(rival_team)
        if not rival_content or not rival_park_slug:
            continue
        rivals.append({
            "team_name": rival_team,
            "team_slug": rival_content["slug"],
            "park_name": rival_content["home_park"],
            "park_slug": rival_park_slug,
        })

    # Look up today/tomorrow's game featuring this team so the page can
    # show the actual forecast inline. This is the whole point of the SEO
    # pages: deliver the forecast to the searcher, then funnel back to /mlb.
    next_game, next_date, next_when = _find_next_mlb_game_for_team(team_name)
    return render_template(
        "mlb/team.html",
        team_name=team_name,
        content=content,
        park=park,
        home_park_slug=home_park_slug,
        division=division,
        division_rivals=rivals,
        next_game=next_game,
        next_date=next_date,
        next_when=next_when,
        canonical_path=f"/mlb/team/{slug}",
    )


# ===== World Cup 2026 =====

@app.route("/worldcup")
def worldcup_root():
    """Matchday view: today + next 2 days."""
    return _render_worldcup_matchday(_eastern_today(), days=3)


@app.route("/worldcup/<date_str>")
def worldcup_date(date_str):
    """Specific-date matchday."""
    if not _valid_date_str(date_str):
        abort(404)
    return _render_worldcup_matchday(date_str, days=1)


@app.route("/worldcup/<date_str>/<slug>")
def worldcup_match(date_str, slug):
    """Per-match detail page."""
    if not _valid_date_str(date_str):
        abort(404)
    slate, meta = get_matchday(date_str)
    if slate is None:
        abort(404)
    match = next((m for m in slate if m["slug"] == slug), None)
    if not match:
        abort(404)
    match["writeup"] = wc_get_writeup(match["event_id"])
    # Attach climatological notes for the venue (used on the match page).
    from worldcup.stadium_notes import get_stadium_notes
    match["stadium_notes"] = get_stadium_notes(match.get("venue", ""))
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    pretty_date = d.strftime("%A, %B %-d")
    return render_template(
        "worldcup/match.html",
        match=match, meta=meta, date_str=date_str, pretty_date=pretty_date,
    )


def _render_worldcup_matchday(start_date_str, days=3):
    """Helper: render one or multiple days of matches on the matchday page."""
    if not _valid_date_str(start_date_str):
        start_date_str = _eastern_today()

    days_data = []
    start_d = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    today = datetime.now(EASTERN_TZ).date()
    for i in range(days):
        d = start_d + timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        # allow_build=True so a fresh page load after a deploy/restart builds
        # the slate inline instead of showing empty. Matches MLB behavior.
        slate, meta = get_matchday(ds, allow_build=True)
        if slate is None:
            slate, meta = [], None
        wc_attach_writeups(slate)
        days_data.append({
            "date_str":    ds,
            "pretty_date": d.strftime("%A, %B %-d"),
            "is_today":    (d == today),
            "is_tomorrow": (d == today + timedelta(days=1)),
            "is_past":     (d < today),
            "slate":       slate,
            "match_count": len(slate),
        })

    total_matches = sum(day["match_count"] for day in days_data)

    # /worldcup is the canonical hub; specific-date pages are self-canonical.
    canonical_path = "/worldcup" if days > 1 else f"/worldcup/{start_date_str}"

    return render_template(
        "worldcup/slate.html",
        days_data=days_data,
        total_matches=total_matches,
        start_date_str=start_date_str,
        showing_multiple=(days > 1),
        canonical_path=canonical_path,
    )




# ===== Tennis Grand Slams =====
#
# Tennis is a SEO-focused, automated-only product. Card auto-shows during
# Slams (~14 days each) and hides between. No manual writeups by design
# per Kevin's scoping: this is a coverage play, not a commentary play.

def _today_local_for_venue(venue_meta):
    """Compute today's date in the venue's local timezone. Used by the
    tennis template to decide which day's hourly to auto-expand. Falls
    back to UTC date if venue/timezone missing."""
    try:
        tz = ZoneInfo((venue_meta or {}).get("timezone") or "UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz).date()


@app.route("/tennis")
def tennis_root():
    """Active Grand Slam slate. Shows whichever Slam is in window now.
    If no Slam active, render an upcoming-Slam placeholder so the URL
    still resolves cleanly (helpful for SEO and any sport-nav links)."""
    slam_meta = active_slam()
    if slam_meta is None:
        upcoming = next_slam()
        return render_template(
            "tennis/slate.html",
            slam=None, upcoming=upcoming, meta=None,
            today_local=_today_local_for_venue((upcoming or {}).get("venue")),
            canonical_path="/tennis",
        )
    slam, meta = get_active_slam_slate()
    display_slam = slam or slam_meta
    return render_template(
        "tennis/slate.html",
        slam=display_slam, upcoming=None, meta=meta,
        today_local=_today_local_for_venue(display_slam.get("venue")),
        canonical_path="/tennis",
    )


@app.route("/tennis/<slam_id>/<date_str>")
def tennis_slam_day(slam_id, date_str):
    """Per-day Slam detail page. SEO long-tail target — each Slam has ~14
    days × 4 Slams/year = ~56 indexable URLs annually for queries like
    'wimbledon weather july 4' or 'us open weather day 5'."""
    if not _valid_date_str(date_str):
        abort(404)
    slam_meta = get_slam_by_id(slam_id)
    if slam_meta is None:
        abort(404)

    # Pull the live slam (with weather attached) and find the requested day
    slam, meta = get_slam_slate_by_id(slam_id)
    display_slam = slam or slam_meta
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    day = None
    for d in (display_slam.get("days") or []):
        if d.get("date_local") == target_date:
            day = d
            break
    if day is None:
        abort(404)

    # ESPN match schedule for this day. Never raises; empty on failure.
    raw_matches = tennis_matches_for_day(slam_id, target_date)
    tz = display_slam["venue"]["timezone"]
    matches = [{**m, "local_time": tennis_local_time(m.get("start_iso", ""), tz)} for m in raw_matches]

    # Pure-weather summary (no game-impact speculation — tennis brand
    # discipline mirrors cfb/analysis.py)
    summary = tennis_daily_summary(day, display_slam["venue"])

    brand = get_site_brand(request.host)
    return render_template(
        "tennis/day.html",
        slam=display_slam,
        day=day,
        matches=matches,
        summary=summary,
        site_url=brand["site_url"],
        canonical_path=f"/tennis/{slam_id}/{date_str}",
    )


@app.route("/tennis/<slam_id>")
def tennis_slam(slam_id):
    """Per-Slam permanent URL (e.g. /tennis/wimbledon). Always resolves,
    even when the Slam isn't currently active. Google can index these as
    evergreen SEO pages year-round; users land on a forecast during the
    tournament and a 'starts <date>' page in the off-window."""
    slam_meta = get_slam_by_id(slam_id)
    if slam_meta is None:
        abort(404)
    slam, meta = get_slam_slate_by_id(slam_id)
    display_slam = slam or slam_meta
    return render_template(
        "tennis/slate.html",
        slam=display_slam,
        upcoming=None if slam else slam_meta,
        meta=meta,
        today_local=_today_local_for_venue(display_slam.get("venue")),
        canonical_path=f"/tennis/{slam_id}",
    )


# ===== NFL + NCAAF stubs (live forecasts coming when season starts) =====

NFL_KICKOFF_2026   = datetime(2026, 9, 10).date()   # Thursday night opener
NCAAF_KICKOFF_2026 = datetime(2026, 8, 29).date()    # Week 1 Saturday


def _nfl_to_wc_shape(g: dict) -> dict:
    """Alias NFL game fields to match worldcup's expected shape so we can
    reuse the wc_cheat_card / wc_summary_panel / wc_hourly_table macros —
    the same MLB-style visual treatment Kevin approved for MLS.

    Wc macros read: away.logo, away.abbreviation, away.short_name,
    venue (str), venue_meta (dict), kickoff_eastern (datetime),
    kickoff_utc_dt, hourly[i].hour_eastern.
    """
    out = dict(g)
    venue = g.get("venue") or {}
    out["venue_meta"] = venue
    out["venue"] = venue.get("name", "")
    ko = g.get("kickoff_utc")
    if ko is not None:
        out["kickoff_utc_dt"] = ko
        out["kickoff_eastern"] = ko.astimezone(EASTERN_TZ)
    for side in ("home", "away"):
        t = dict(g.get(side) or {})
        if "logo_url" in t and "logo" not in t:
            t["logo"] = t["logo_url"]
        if "abbrev" in t and "abbreviation" not in t:
            t["abbreviation"] = t["abbrev"]
        if "short" in t and "short_name" not in t:
            t["short_name"] = t["short"]
        out[side] = t
    def _enrich_periods(periods):
        result = []
        for h in (periods or []):
            h2 = dict(h)
            if "hour_eastern" not in h2 or not h2["hour_eastern"]:
                # Prefer pre-computed label; else format ISO start_time as 12-hr ET
                label = h.get("local_hour_label")
                if not label and h.get("start_time"):
                    try:
                        from datetime import datetime as _dt
                        dt = _dt.fromisoformat(h["start_time"].replace("Z", "+00:00"))
                        label = dt.astimezone(EASTERN_TZ).strftime("%-I %p").lstrip("0")
                    except Exception:
                        label = (h.get("start_time") or "")[11:16]
                h2["hour_eastern"] = label
            result.append(h2)
        return result

    out["hourly"] = _enrich_periods(g.get("hourly"))
    # Also enrich HRRR periods so the slate HRRR toggle shows 12-hr ET times
    if g.get("hrrr_hourly"):
        out["hrrr_hourly"] = _enrich_periods(g.get("hrrr_hourly"))
    return out


@app.route("/nfl")
def nfl_root():
    """NFL slate — preseason through Super Bowl. Empty state shows
    "Preseason begins August 7" copy until games appear in the window.
    Uses MLB-style layout: cheat cards → writeup section → per-game blocks
    with summary panel + hourly table side-by-side."""
    games, meta = get_nfl_slate(allow_build=True)
    shaped = []
    if games:
        nfl_attach_writeups(games)
        for g in games:
            wc = _nfl_to_wc_shape(g)
            wc["url_path"] = f"/nfl/{g.get('kickoff_date_eastern')}/{g.get('slug')}"
            shaped.append(wc)

    return render_template(
        "nfl/slate.html",
        games=shaped,
        total_games=len(shaped),
        meta=meta,
        canonical_path="/nfl",
    )


@app.route("/nfl/<date_str>/<slug>")
def nfl_game(date_str, slug):
    """Per-game NFL detail page with schema.org SportsEvent + hourly forecast
    + meteorologist analysis. Dome venues render an indoor notice instead
    of a forecast. Retractable venues default to Closed with a toggle to Open."""
    if not _valid_date_str(date_str):
        abort(404)
    game_raw = find_nfl_game(date_str, slug)
    if not game_raw:
        abort(404)
    game = _nfl_to_wc_shape(game_raw)

    kickoff = game.get("kickoff_utc")
    if kickoff:
        game["kickoff_end_utc"] = kickoff + timedelta(hours=4)

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        pretty_date = d.strftime("%A, %B %-d")
    except ValueError:
        pretty_date = date_str

    try:
        analysis = nfl_generate_analysis(game)
    except Exception as e:
        print(f"[nfl.game] analysis failed for {date_str}/{slug}: {e}", flush=True)
        analysis = None

    # HRRR high-res overlay — 3 km CONUS, includes wind gusts NWS smooths out.
    # Fail-soft: if HRRR is unavailable (dome venue skips lat/lon, API down,
    # beyond the ~48h HRRR horizon) the template's `{% if hrrr_hourly %}`
    # simply hides the toggle. Skipped entirely for dome venues.
    hrrr_hourly = []
    venue = game.get("venue_meta") or {}
    roof = (venue.get("roof_type") or "").lower()
    if roof != "fixed_dome":
        lat, lon = venue.get("lat"), venue.get("lon")
        kickoff = game.get("kickoff_utc")
        if lat is not None and lon is not None and kickoff is not None:
            try:
                hrrr_periods = get_hrrr_periods(lat, lon)
                if hrrr_periods:
                    hrrr_hourly = nfl_hourly_window(hrrr_periods, kickoff)
            except Exception as e:
                print(f"[nfl.game] HRRR fetch failed for {date_str}/{slug}: {e}", flush=True)

    brand = get_site_brand(request.host)
    return render_template(
        "nfl/game.html",
        game=game,
        analysis=analysis,
        hrrr_hourly=hrrr_hourly,
        date_str=date_str,
        pretty_date=pretty_date,
        site_url=brand["site_url"],
        canonical_path=f"/nfl/{date_str}/{slug}",
    )


# ===== NFL stadium landing pages =====

def _find_next_nfl_game_at_venue(stadium_name):
    """Return (game_dict, date_str, when_label) for today's or tomorrow's
    NFL game at this stadium. Used on NFL stadium pages to surface the
    forecast inline. Returns (None, None, None) during offseason."""
    try:
        games, _ = get_nfl_slate(allow_build=False)
    except Exception:
        return None, None, None
    if not games:
        return None, None, None
    today = _eastern_today()
    tomorrow = _eastern_tomorrow()
    for date_label, label in [(today, "Today"), (tomorrow, "Tomorrow")]:
        for g in games:
            venue_meta = g.get("venue_meta") or {}
            if venue_meta.get("name") == stadium_name and g.get("kickoff_date_eastern") == date_label:
                return g, date_label, label
    return None, None, None


@app.route("/nfl/stadium/<slug>")
def nfl_stadium(slug):
    """Per-NFL-stadium evergreen weather guide."""
    entry = STADIUM_BY_SLUG_NFL.get(slug)
    if not entry:
        abort(404)
    stadium_name, content = entry
    # Look up the stadium dict from NFL_TEAMS (any team that plays there
    # will do — MetLife and SoFi are shared but the stadium data is the
    # same for both).
    stadium = None
    for t in NFL_TEAMS.values():
        if t.get("stadium", {}).get("name") == stadium_name:
            stadium = t["stadium"]
            break
    if not stadium:
        abort(404)
    next_game, next_date, next_when = _find_next_nfl_game_at_venue(stadium_name)
    return render_template(
        "nfl/stadium.html",
        stadium_name=stadium_name,
        stadium=stadium,
        content=content,
        next_game=next_game,
        next_date=next_date,
        next_when=next_when,
        canonical_path=f"/nfl/stadium/{slug}",
    )


# ===== NFL team landing pages =====

@app.route("/nfl/team/<slug>")
def nfl_team_page(slug):
    entry = TEAM_BY_SLUG_NFL.get(slug)
    if not entry:
        abort(404)
    team_name, content = entry
    # Look up NFL_TEAMS row
    team_data = None
    for t in NFL_TEAMS.values():
        if t.get("name") == team_name:
            team_data = t
            break
    if not team_data:
        abort(404)
    stadium = team_data.get("stadium", {})
    division = TEAM_TO_DIVISION_NFL.get(team_name, "")
    facts = [
        ("Home stadium", content["home_stadium"]),
        ("City", stadium.get("city", "")),
        ("Roof", {"open": "Open-air", "retractable": "Retractable",
                  "fixed_dome": "Fixed dome", "fixed_canopy": "Fixed canopy"}
                 .get(stadium.get("roof_type"), "Open-air")),
        ("Division", division),
    ]
    sections = [
        ("Home advantage", content["home_advantage"]),
        ("Division road environments", content["road_challenges"]),
        ("For DFS and bettors", content["betting_angle"]),
    ]
    return render_template(
        "_shared/landing.html",
        kicker="NFL Team Weather Playbook",
        back_url="/nfl", back_label="NFL Weather",
        title=content["headline"],
        facts=facts, sections=sections,
        cta_url="/nfl",
        cta_label=f"See today's {team_name} game forecast",
        breadcrumb_hub_url="/nfl",
        breadcrumb_hub_label="NFL Weather",
        breadcrumb_entity=team_name,
        canonical_path=f"/nfl/team/{slug}",
    )


# ===== NASCAR track landing pages =====

@app.route("/nascar/track/<slug>")
def nascar_track_page(slug):
    entry = TRACK_BY_SLUG.get(slug)
    if not entry:
        abort(404)
    track_name, content = entry
    track_data = NASCAR_TRACKS.get(track_name, {})
    facts = [
        ("Length", f"{track_data.get('length_miles', '?')} mi"),
        ("City", track_data.get("city", "")),
        ("Track type", track_data.get("track_type", "").replace("_", " ").title()),
    ]
    sections = [
        ("Overview", content["context"]),
        ("Weather angle", content["weather_angle"]),
        ("For DFS and bettors", content["betting_angle"]),
    ]
    return render_template(
        "_shared/landing.html",
        kicker="NASCAR Track Weather Guide",
        back_url="/nascar", back_label="NASCAR Weather",
        title=content["headline"],
        facts=facts, sections=sections,
        cta_url="/nascar",
        cta_label="See this weekend's Cup race weather forecast",
        breadcrumb_hub_url="/nascar",
        breadcrumb_hub_label="NASCAR Weather",
        breadcrumb_entity=track_name,
        canonical_path=f"/nascar/track/{slug}",
    )


# ===== PGA course landing pages =====

@app.route("/golf/course/<slug>")
def golf_course_page(slug):
    entry = COURSE_BY_SLUG.get(slug)
    if not entry:
        abort(404)
    course_name, content = entry
    course_data = PGA_COURSES.get(course_name, {})
    facts = [
        ("Location", course_data.get("city", "")),
        ("Country", course_data.get("country", "")),
    ]
    sections = [
        ("Overview", content["intro"]),
        ("Weather angle", content["angle"]),
    ]
    return render_template(
        "_shared/landing.html",
        kicker="PGA Tour Course Weather Guide",
        back_url="/golf", back_label="PGA Tour Weather",
        title=content["headline"],
        facts=facts, sections=sections,
        cta_url="/golf",
        cta_label="See this week's PGA Tour weather forecast",
        breadcrumb_hub_url="/golf",
        breadcrumb_hub_label="PGA Tour Weather",
        breadcrumb_entity=course_name,
        canonical_path=f"/golf/course/{slug}",
    )


# ===== NCAAF stadium landing pages =====

@app.route("/ncaaf/stadium/<slug>")
def ncaaf_stadium_page(slug):
    entry = STADIUM_BY_SLUG_CFB.get(slug)
    if not entry:
        abort(404)
    stadium_name, content = entry
    # Look up the stadium data by matching team
    stadium_data = None
    team_name = content.get("team", "")
    for t in FBS_TEAMS.values():
        if t.get("name") == team_name:
            stadium_data = t.get("stadium", {})
            break
    if not stadium_data:
        stadium_data = {}
    facts = [
        ("Team", content["team"]),
        ("City", stadium_data.get("city", "")),
        ("Roof", {"open": "Open-air", "retractable": "Retractable",
                  "fixed_dome": "Fixed dome", "fixed_canopy": "Fixed canopy"}
                 .get(stadium_data.get("roof"), "Open-air")),
        ("Capacity", f"{stadium_data.get('cap', 0):,}" if stadium_data.get('cap') else ""),
    ]
    sections = [
        ("Overview", content["intro"]),
        ("Weather angle", content["angle"]),
    ]
    return render_template(
        "_shared/landing.html",
        kicker="NCAAF Stadium Weather Guide",
        back_url="/ncaaf", back_label="NCAAF Weather",
        title=content["headline"],
        facts=facts, sections=sections,
        cta_url="/ncaaf",
        cta_label="See this weekend's CFB weather forecast",
        breadcrumb_hub_url="/ncaaf",
        breadcrumb_hub_label="NCAAF Weather",
        breadcrumb_entity=stadium_name,
        canonical_path=f"/ncaaf/stadium/{slug}",
    )


# ===== MLS stadium + team landing pages =====

@app.route("/mls/team/<slug>")
def mls_team_page(slug):
    entry = TEAM_BY_SLUG_MLS.get(slug)
    if not entry:
        abort(404)
    team_name, content = entry
    team_data = None
    for t in MLS_TEAMS.values():
        if t.get("name") == team_name:
            team_data = t
            break
    if not team_data:
        abort(404)
    stadium = team_data.get("stadium", {})
    conf = TEAM_TO_CONF_MLS.get(team_name, "")
    facts = [
        ("Home stadium", content["stadium"]),
        ("City", stadium.get("city", "")),
        ("Roof", {"open": "Open-air", "retractable": "Retractable",
                  "fixed_dome": "Fixed dome", "fixed_roof": "Fixed roof"}
                 .get(stadium.get("roof_type"), "Open-air")),
        ("Conference", conf),
    ]
    sections = [
        ("Home advantage", content["home"]),
        ("Road environments", content["road"]),
        ("Weather angle", content["angle"]),
    ]
    return render_template(
        "_shared/landing.html",
        kicker="MLS Team Weather Playbook",
        back_url="/mls", back_label="MLS Weather",
        title=content["headline"],
        facts=facts, sections=sections,
        cta_url="/mls",
        cta_label=f"See today's {team_name} match forecast",
        breadcrumb_hub_url="/mls",
        breadcrumb_hub_label="MLS Weather",
        breadcrumb_entity=team_name,
        canonical_path=f"/mls/team/{slug}",
    )


@app.route("/mls/stadium/<slug>")
def mls_stadium_page(slug):
    entry = STADIUM_BY_SLUG_MLS.get(slug)
    if not entry:
        abort(404)
    stadium_name, content = entry
    stadium_data = {}
    for t in MLS_TEAMS.values():
        s = t.get("stadium", {})
        if s.get("name") == stadium_name:
            stadium_data = s
            break
    facts = [
        ("Team", content["team"]),
        ("City", stadium_data.get("city", "")),
        ("Roof", {"open": "Open-air", "retractable": "Retractable",
                  "fixed_dome": "Fixed dome", "fixed_roof": "Fixed roof"}
                 .get(stadium_data.get("roof_type"), "Open-air")),
    ]
    sections = [
        ("Overview", content["climate"]),
        ("Weather angle", content["angle"]),
    ]
    return render_template(
        "_shared/landing.html",
        kicker="MLS Stadium Weather Guide",
        back_url="/mls", back_label="MLS Weather",
        title=content["headline"],
        facts=facts, sections=sections,
        cta_url="/mls",
        cta_label="See this week's MLS forecast",
        breadcrumb_hub_url="/mls",
        breadcrumb_hub_label="MLS Weather",
        breadcrumb_entity=stadium_name,
        canonical_path=f"/mls/stadium/{slug}",
    )


# ===== Tennis Grand Slam venue landing pages =====

@app.route("/tennis/venue/<slug>")
def tennis_venue_page(slug):
    entry = VENUE_BY_SLUG_TENNIS.get(slug)
    if not entry:
        abort(404)
    slam_key, content = entry
    facts = [
        ("Venue", content["name"]),
        ("Location", content["location"]),
        ("Tournament", content["tournament"]),
        ("Window", content["window"]),
    ]
    sections = [
        ("Climate", content["climate"]),
        ("Weather angle", content["angle"]),
    ]
    return render_template(
        "_shared/landing.html",
        kicker="Grand Slam Venue Weather Guide",
        byline_audience="sports fans and bettors",
        back_url="/tennis", back_label="Tennis Weather",
        title=content["headline"],
        facts=facts, sections=sections,
        cta_url="/tennis",
        cta_label=f"See today's {content['tournament']} matches forecast",
        breadcrumb_hub_url="/tennis",
        breadcrumb_hub_label="Tennis Weather",
        breadcrumb_entity=content["name"],
        canonical_path=f"/tennis/venue/{slug}",
    )


# ===== Premier League team + stadium landing pages =====

@app.route("/prem")
def prem_root():
    """Premier League slate hub. Groups matches by venue-local date (UK) and
    shows cheat cards per match with WeatherAPI-only weather (no NWS since
    the UK sits outside NWS coverage, no HRRR since UK is outside CONUS).
    Off-season (May–August) returns an empty slate; template renders a
    'season resumes' message.
    """
    matches, meta = get_prem_slate(allow_build=True)
    prem_attach_writeups(matches)

    # Group matches by their UK-local date (date_local field is YYYY-MM-DD).
    uk_today = datetime.now(ZoneInfo("Europe/London")).date()
    grouped: dict[str, list[dict]] = {}
    for m in matches:
        d = m.get("date_local")
        if not d:
            continue
        grouped.setdefault(d, []).append(m)

    days_data = []
    for date_str in sorted(grouped.keys()):
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        days_data.append({
            "date_str":    date_str,
            "pretty_date": d.strftime("%A, %B %-d"),
            "is_today":    (d == uk_today),
            "is_tomorrow": (d == uk_today + timedelta(days=1)),
            "matches":     grouped[date_str],
            "slate":       grouped[date_str],
            "match_count": len(grouped[date_str]),
        })

    return render_template(
        "prem/slate.html",
        days_data=days_data,
        showing_multiple=(len(days_data) > 1),
        total_matches=len(matches),
        meta=meta,
        canonical_path="/prem",
    )


@app.route("/prem/guides")
def prem_hub():
    """Team + stadium landing-page index. Kept live so the /prem/team/<slug>
    and /prem/stadium/<slug> pages have a hub to link back to for internal
    linking / SEO. The main /prem is now the live match slate."""
    teams = [(name, c) for name, c in sorted(TEAM_CONTENT_PREM.items())]
    stadiums = [(name, c) for name, c in sorted(STADIUM_CONTENT_PREM.items())]
    return render_template("prem_hub.html", teams=teams, stadiums=stadiums,
                           canonical_path="/prem/guides")


@app.route("/prem/<date_str>/<slug>")
def prem_match(date_str, slug):
    """Per-match Premier League detail page with schema.org SportsEvent +
    hourly forecast around kickoff. UK-local dates."""
    if not _valid_date_str(date_str):
        abort(404)
    match = find_prem_match(date_str, slug)
    if not match:
        abort(404)

    # Schema.org end time: 3h after kickoff covers 90-min match + halftime +
    # injury time + a buffer.
    kickoff = match.get("kickoff_utc")
    if kickoff:
        match["kickoff_end_utc"] = kickoff + timedelta(hours=3)

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        pretty_date = d.strftime("%A, %B %-d")
    except ValueError:
        pretty_date = date_str

    brand = get_site_brand(request.host)
    return render_template(
        "prem/match.html",
        match=match,
        date_str=date_str,
        pretty_date=pretty_date,
        site_url=brand["site_url"],
        canonical_path=f"/prem/{date_str}/{slug}",
    )


@app.route("/ipl")
def ipl_hub():
    """Simple index hub for IPL landing pages."""
    teams = [(name, c) for name, c in sorted(TEAM_CONTENT_IPL.items())]
    grounds = [(name, c) for name, c in sorted(GROUND_CONTENT_IPL.items())]
    return render_template("ipl_hub.html", teams=teams, grounds=grounds,
                           canonical_path="/ipl")


@app.route("/prem/team/<slug>")
def prem_team_page(slug):
    entry = TEAM_BY_SLUG_PREM.get(slug)
    if not entry:
        abort(404)
    team_name, content = entry
    facts = [
        ("Home stadium", content["stadium"]),
        ("City", content["city"]),
        ("Capacity", f"{content['capacity']:,}"),
    ]
    sections = [
        ("Home advantage", content["home"]),
        ("Road environments", content["road"]),
        ("Weather angle", content["angle"]),
    ]
    return render_template(
        "_shared/landing.html",
        kicker="Premier League Club Weather Playbook",
        byline_audience="sports fans and bettors",
        back_url="/prem", back_label="Premier League Weather",
        title=content["headline"],
        facts=facts, sections=sections,
        cta_url="/prem",
        cta_label=f"See {team_name}'s next match forecast",
        breadcrumb_hub_url="/prem",
        breadcrumb_hub_label="Premier League Weather",
        breadcrumb_entity=team_name,
        canonical_path=f"/prem/team/{slug}",
    )


@app.route("/prem/stadium/<slug>")
def prem_stadium_page(slug):
    entry = STADIUM_BY_SLUG_PREM.get(slug)
    if not entry:
        abort(404)
    stadium_name, content = entry
    facts = [
        ("Home club", content["team"]),
        ("City", content["city"]),
        ("Capacity", f"{content['capacity']:,}"),
    ]
    sections = [
        ("Overview", content["overview"]),
        ("Weather angle", content["angle"]),
    ]
    return render_template(
        "_shared/landing.html",
        kicker="Premier League Stadium Weather Guide",
        byline_audience="sports fans and bettors",
        back_url="/prem", back_label="Premier League Weather",
        title=content["headline"],
        facts=facts, sections=sections,
        cta_url="/prem",
        cta_label="See this week's Premier League forecast",
        breadcrumb_hub_url="/prem",
        breadcrumb_hub_label="Premier League Weather",
        breadcrumb_entity=stadium_name,
        canonical_path=f"/prem/stadium/{slug}",
    )


# ===== IPL team + ground landing pages =====

@app.route("/ipl/team/<slug>")
def ipl_team_page(slug):
    entry = TEAM_BY_SLUG_IPL.get(slug)
    if not entry:
        abort(404)
    team_name, content = entry
    facts = [
        ("Home ground", content["ground"]),
        ("City", content["city"]),
        ("Abbrev", content["abbrev"]),
        ("Capacity", f"{content['capacity']:,}"),
    ]
    sections = [
        ("Home advantage", content["home"]),
        ("Road environments", content["road"]),
        ("Weather angle", content["angle"]),
    ]
    return render_template(
        "_shared/landing.html",
        kicker="IPL Franchise Weather Playbook",
        byline_audience="sports fans and bettors",
        back_url="/ipl", back_label="IPL Weather",
        title=content["headline"],
        facts=facts, sections=sections,
        cta_url="/ipl",
        cta_label=f"See {team_name}'s next match forecast",
        breadcrumb_hub_url="/ipl",
        breadcrumb_hub_label="IPL Weather",
        breadcrumb_entity=team_name,
        canonical_path=f"/ipl/team/{slug}",
    )


@app.route("/ipl/ground/<slug>")
def ipl_ground_page(slug):
    entry = GROUND_BY_SLUG_IPL.get(slug)
    if not entry:
        abort(404)
    ground_name, content = entry
    facts = [
        ("Home franchise", content["team"]),
        ("City", content["city"]),
        ("Capacity", f"{content['capacity']:,}"),
    ]
    sections = [
        ("Overview", content["overview"]),
        ("Weather angle", content["angle"]),
    ]
    return render_template(
        "_shared/landing.html",
        kicker="IPL Ground Weather Guide",
        byline_audience="sports fans and bettors",
        back_url="/ipl", back_label="IPL Weather",
        title=content["headline"],
        facts=facts, sections=sections,
        cta_url="/ipl",
        cta_label="See this week's IPL forecast",
        breadcrumb_hub_url="/ipl",
        breadcrumb_hub_label="IPL Weather",
        breadcrumb_entity=ground_name,
        canonical_path=f"/ipl/ground/{slug}",
    )


@app.route("/ncaaf")
def ncaaf_root():
    """CFB slate for the current week. During the off-season (kickoff > 7 days
    away) falls back to the coming-soon page since the cache will be empty."""
    today = datetime.now(EASTERN_TZ).date()
    days_until = max(0, (NCAAF_KICKOFF_2026 - today).days)

    # Try to fetch the slate. If we get games, render the live page.
    games, meta = get_cfb_slate(allow_build=True)
    if games:
        return render_template(
            "ncaaf/slate.html",
            games=games, meta=meta,
            canonical_path="/ncaaf",
        )

    # No games in the window. Fall back to the coming-soon page if the season
    # hasn't started yet; otherwise show the empty slate with a friendly message.
    if days_until > 7:
        return render_template("ncaaf/coming-soon.html",
                               sport_name="NCAAF", days_until=days_until,
                               kickoff_date=NCAAF_KICKOFF_2026.strftime("%B %-d"))
    return render_template(
        "ncaaf/slate.html",
        games=[], meta=meta,
        canonical_path="/ncaaf",
    )


@app.route("/ncaaf/<date_str>/<slug>")
def ncaaf_game(date_str, slug):
    """Per-game CFB detail page.

    AI-SEO money page: schema.org SportsEvent + WeatherForecast, embedded
    meteorologist analysis paragraph from cfb/analysis.py, NWS cheat-sheet
    hourly table. Every FBS game gets a unique indexable URL with
    structured weather data attributed to mysportsweather.com.
    """
    if not _valid_date_str(date_str):
        abort(404)
    game = find_cfb_game(date_str, slug)
    if not game:
        abort(404)

    # End time for schema.org: kickoff + ~3.5h game window
    kickoff = game.get("kickoff_utc")
    if kickoff:
        game["kickoff_end_utc"] = kickoff + timedelta(hours=4)

    # Pretty date for templates / titles
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        pretty_date = d.strftime("%A, %B %-d")
    except ValueError:
        pretty_date = date_str

    # Meteorologist analysis (deterministic, rule-based — preserves
    # "built by a meteorologist, not AI" brand)
    try:
        analysis = cfb_generate_analysis(game)
    except Exception as e:
        print(f"[ncaaf.game] analysis failed for {date_str}/{slug}: {e}", flush=True)
        analysis = None

    # HRRR high-resolution overlay. Open-Meteo paid endpoint; CONUS-only.
    # Fail soft — if HRRR unavailable (outside CONUS, API down, beyond
    # the ~48h HRRR horizon), the template's `{% if hrrr_hourly %}` just
    # hides the toggle. No user-facing error.
    hrrr_hourly = []
    venue = game.get("venue") or {}
    lat, lon = venue.get("lat"), venue.get("lon")
    kickoff = game.get("kickoff_utc")
    if lat is not None and lon is not None and kickoff is not None:
        try:
            hrrr_periods = get_hrrr_periods(lat, lon)
            if hrrr_periods:
                hrrr_hourly = cfb_hourly_window(hrrr_periods, kickoff)
        except Exception as e:
            print(f"[ncaaf.game] HRRR fetch failed for {date_str}/{slug}: {e}", flush=True)

    brand = get_site_brand(request.host)
    return render_template(
        "ncaaf/game.html",
        game=game,
        analysis=analysis,
        hrrr_hourly=hrrr_hourly,
        date_str=date_str,
        pretty_date=pretty_date,
        site_url=brand["site_url"],
        canonical_path=f"/ncaaf/{date_str}/{slug}",
    )


# ===== MLS weather forecasts =====
#
# Slate is built by mls/cache.py warmer (25-min cycle, 30-min stale self-heal,
# kickoff freeze for in-match stability). NWS-primary via cfb/nws_client,
# WeatherAPI fallback. Three Canadian venues (Toronto/Montreal/Vancouver)
# route directly to WeatherAPI since NWS doesn't cover Canada.
#
# URL shape mirrors World Cup: /mls (slate hub) + /mls/<date>/<slug> per match.

def _mls_to_wc_shape(m: dict) -> dict:
    """Alias MLS match fields to match worldcup's expected shape so we can
    reuse the wc_cheat_card / wc_summary_panel / wc_hourly_table macros
    and inherit all of style.css's polished card/summary/hourly styling.

    World Cup expects:
      - match.away.logo, .abbreviation, .short_name (we have logo_url, abbrev, short)
      - match.venue (str) and match.venue_meta (dict) — we have only venue (dict)
      - match.kickoff_eastern (datetime) — we have only kickoff_utc + str
      - match.kickoff_utc_dt — alias of kickoff_utc
      - hourly[i].hour_eastern — we have local_hour_label

    Mutation-free: returns a shallow copy with the aliased keys layered on top.
    """
    out = dict(m)
    venue = m.get("venue") or {}
    # Stash dict under venue_meta, then replace venue with the string name
    out["venue_meta"] = venue
    out["venue"] = venue.get("name", "")
    # Kickoff datetimes
    ko = m.get("kickoff_utc")
    if ko is not None:
        out["kickoff_utc_dt"] = ko
        out["kickoff_eastern"] = ko.astimezone(EASTERN_TZ)
    # Team aliases — wc macros read .logo / .abbreviation / .short_name
    for side in ("home", "away"):
        t = dict(m.get(side) or {})
        if "logo_url" in t and "logo" not in t:
            t["logo"] = t["logo_url"]
        if "abbrev" in t and "abbreviation" not in t:
            t["abbreviation"] = t["abbrev"]
        if "short" in t and "short_name" not in t:
            t["short_name"] = t["short"]
        out[side] = t
    # Hourly aliases — wc table reads .hour_eastern
    hourly_out = []
    for h in (m.get("hourly") or []):
        h2 = dict(h)
        if "hour_eastern" not in h2:
            h2["hour_eastern"] = h.get("local_hour_label") or (h.get("start_time", "")[11:16])
        hourly_out.append(h2)
    out["hourly"] = hourly_out
    return out


@app.route("/mls")
def mls_root():
    """MLS slate hub. Groups matches by venue-local date, shows cheat cards
    + writeups + per-day blocks. Off-season returns an empty slate; we
    render the same template with no matches rather than a coming-soon
    page since MLS is a long season (Feb–Nov) and the off-season window
    is short."""
    matches, meta = get_mls_slate(allow_build=True)
    mls_attach_writeups(matches)

    # Group matches by their venue-local date (date_local field already
    # YYYY-MM-DD). Build a days_data list the template iterates.
    today_et = datetime.now(EASTERN_TZ).date()
    grouped: dict[str, list[dict]] = {}
    for m in matches:
        d = m.get("date_local")
        if not d:
            continue
        grouped.setdefault(d, []).append(_mls_to_wc_shape(m))

    days_data = []
    for date_str in sorted(grouped.keys()):
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        days_data.append({
            "date_str":     date_str,
            "pretty_date":  d.strftime("%A, %B %-d"),
            "is_today":     (d == today_et),
            "is_tomorrow":  (d == today_et + timedelta(days=1)),
            "slate":        grouped[date_str],   # wc template iterates day.slate
            "matches":      grouped[date_str],   # keep both keys for safety
            "match_count":  len(grouped[date_str]),
        })

    return render_template(
        "mls/slate.html",
        days_data=days_data,
        showing_multiple=(len(days_data) > 1),
        total_matches=len(matches),
        meta=meta,
        canonical_path="/mls",
    )


@app.route("/mls/<date_str>/<slug>")
def mls_match(date_str, slug):
    """Per-match MLS detail page with schema.org SportsEvent + hourly
    forecast + meteorologist analysis paragraph."""
    if not _valid_date_str(date_str):
        abort(404)
    match_raw = find_mls_match(date_str, slug)
    if not match_raw:
        abort(404)
    match = _mls_to_wc_shape(match_raw)

    # End time for schema.org: kickoff + 2.5h covers 90-min match +
    # halftime + injury time + (rare) extra time
    kickoff = match.get("kickoff_utc")
    if kickoff:
        match["kickoff_end_utc"] = kickoff + timedelta(hours=3)

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        pretty_date = d.strftime("%A, %B %-d")
    except ValueError:
        pretty_date = date_str

    try:
        analysis = mls_generate_analysis(match)
    except Exception as e:
        print(f"[mls.match] analysis failed for {date_str}/{slug}: {e}", flush=True)
        analysis = None

    brand = get_site_brand(request.host)
    return render_template(
        "mls/match.html",
        match=match,
        analysis=analysis,
        date_str=date_str,
        pretty_date=pretty_date,
        site_url=brand["site_url"],
        canonical_path=f"/mls/{date_str}/{slug}",
    )


# ===== College World Series =====

def _build_cws_day(d, today):
    """Build the data dict for a single CWS day. Used by both the single-day
    /cws/<date> route and the multi-day /cws hub. Always returns a dict —
    empty slate just means no games scheduled that day, which is normal
    during bracket off-days."""
    ds = d.strftime("%Y-%m-%d")
    slate, meta = get_cws_slate(ds)
    if slate is None:
        slate = []
    cws_attach_writeups(slate)
    return {
        "date_str":      ds,
        "pretty_date":   d.strftime("%A, %B %-d"),
        "is_today":      (d == today),
        "is_tomorrow":   (d == today + timedelta(days=1)),
        "is_past":       (d < today),
        "slate":         slate,
        "daily_writeup": cws_get_writeup(ds),
        "game_count":    len(slate),
        "meta":          meta or {},
    }


def _render_cws_slate(date_str, canonical_path, multi_day=False):
    """Render the CWS slate with an explicit canonical URL.

    When multi_day=True (the /cws hub), shows today + next 2 days so the
    page is never empty during bracket off-days. When False (/cws/<date>),
    shows a single specific date — same as before.

    Used by /cws hub and /cws/<date> so /cws renders inline instead of
    redirecting — Google flagged the old redirect as a Search Console
    error on Jun 12, 2026.
    """
    if not _valid_date_str(date_str):
        abort(404)
    today = datetime.now(EASTERN_TZ).date()

    if multi_day:
        days_data = [_build_cws_day(today + timedelta(days=i), today) for i in range(3)]
    else:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        days_data = [_build_cws_day(d, today)]

    total_games = sum(day["game_count"] for day in days_data)

    return render_template(
        "cws/slate.html",
        days_data=days_data,
        showing_multiple=multi_day,
        total_games=total_games,
        date_str=date_str,
        canonical_path=canonical_path,
    )


@app.route("/cws")
def cws_root():
    """Render the CWS hub — today + next 2 days. /cws is the canonical hub URL.
    Multi-day view keeps the page useful on bracket off-days when today has
    no scheduled games."""
    return _render_cws_slate(_eastern_today(), canonical_path="/cws", multi_day=True)


@app.route("/cws/<date_str>")
def cws_date(date_str):
    """CWS slate for a specific date. Today canonicalizes back to /cws."""
    today = _eastern_today()
    canonical = "/cws" if date_str == today else f"/cws/{date_str}"
    return _render_cws_slate(date_str, canonical_path=canonical)


@app.route("/cws/<date_str>/<slug>")
def cws_game(date_str, slug):
    if not _valid_date_str(date_str):
        abort(404)
    slate, meta = get_cws_slate(date_str)
    if slate is None:
        abort(404)
    game = next((g for g in slate if g["slug"] == slug), None)
    if not game:
        abort(404)
    game["writeup"] = cws_get_writeup(game["event_id"])
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return render_template("cws/game.html", game=game, meta=meta, date_str=date_str,
                           pretty_date=d.strftime("%A, %B %-d"))


# ===== PGA Tour =====

@app.route("/golf")
def golf_root():
    """Current PGA slate — usually 1-3 active/upcoming tournaments."""
    slate, meta = get_pga_slate()
    if slate is None:
        slate, meta = [], {"build_err": "Slate not yet built"}
    golf_attach_writeups(slate)
    return render_template(
        "golf/slate.html",
        slate=slate, meta=meta,
        canonical_path="/golf",
    )



@app.route("/nascar")
def nascar_root():
    """NASCAR current/upcoming Cup races."""
    slate, meta = get_nascar_slate()
    if slate is None:
        slate, meta = [], {"build_err": "Slate not yet built"}
    nascar_attach_writeups(slate)
    return render_template("nascar/slate.html", slate=slate, meta=meta,
                           canonical_path="/nascar")


@app.route("/nascar/<slug>")
def nascar_race(slug):
    slate, meta = get_nascar_slate()
    if slate is None:
        abort(404)
    race = next((r for r in slate if r["slug"] == slug), None)
    if not race:
        abort(404)
    race["writeup"] = nascar_get_writeup(race["event_id"])
    return render_template("nascar/race.html", race=race, meta=meta)


@app.route("/golf/<slug>")
def golf_tournament(slug):
    """Per-tournament detail."""
    slate, meta = get_pga_slate()
    if slate is None:
        abort(404)
    tournament = next((t for t in slate if t["slug"] == slug), None)
    if not tournament:
        abort(404)
    tournament["writeup"] = golf_get_writeup(tournament["event_id"])

    # Hide rounds whose day has fully passed in course-local time. Once it's
    # Friday at the course, Round 1's Thursday hourly forecast is no longer
    # useful — drop it so the page leads with the next upcoming round.
    # Cutoff is midnight course-local: at 12:01 AM Friday, Round 1 disappears;
    # at 12:01 AM Saturday, Round 2 disappears; etc. (Kevin's manual writeup
    # is rendered separately above and is not affected.)
    #
    # Filter at REQUEST time (not in the cached slate) so the midnight cutoff
    # is exact — building the filter into the cache would lag by up to a
    # full 25-min warmer cycle. Shallow-copy the tournament dict and replace
    # only the rounds list so the cached slate is left intact for other
    # requests.
    visible_rounds = tournament.get("rounds") or []
    course_meta = tournament.get("course_meta")
    if course_meta and visible_rounds:
        try:
            tz = ZoneInfo(course_meta["timezone"])
            today_local = datetime.now(tz).date()
            visible_rounds = [
                r for r in visible_rounds
                if r.get("date_local") and r["date_local"] >= today_local
            ]
        except Exception as e:
            # If timezone lookup or date math ever fails, fall back to
            # showing all rounds rather than blanking the page.
            print(f"[golf] past-round filter failed for {slug}: {e}", flush=True)

    tournament_view = dict(tournament)
    tournament_view["rounds"] = visible_rounds

    return render_template(
        "golf/tournament.html",
        tournament=tournament_view, meta=meta,
    )


# ===== Admin write-up route (in-memory storage; not yet used) =====

def _check_admin_auth() -> bool:
    """Basic auth against ADMIN_PASSWORD env var. No password set = disabled."""
    expected = os.environ.get("ADMIN_PASSWORD", "")
    if not expected:
        return False
    auth = request.authorization
    return bool(auth and auth.username == "kevin" and auth.password == expected)


def _admin_required(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not _check_admin_auth():
            return Response(
                "Auth required", 401,
                {"WWW-Authenticate": 'Basic realm="kevinrothwx admin"'},
            )
        return fn(*args, **kwargs)
    return wrapper


@app.route("/admin/mlb", methods=["GET", "POST"])
@_admin_required
def admin_mlb():
    """Write-up admin: dropdown of today's games + textarea."""
    date_str = request.args.get("date", _eastern_today())
    if not _valid_date_str(date_str):
        date_str = _eastern_today()

    if request.method == "POST":
        try:
            game_pk = int(request.form.get("game_pk", "0"))
        except ValueError:
            game_pk = 0
        text = request.form.get("text", "")
        color = request.form.get("color", "").strip() or None
        if game_pk:
            save_writeup(game_pk, text, color=color)
            flash("Write-up saved.", "success")
        return redirect(url_for("admin_mlb", date=date_str))

    slate, _ = get_slate(date_str)
    if slate is None:
        slate = []
    attach_writeups_to_slate(slate)

    return render_template("mlb/admin.html", slate=slate, date_str=date_str)




@app.route("/admin/worldcup", methods=["GET", "POST"])
@_admin_required
def admin_worldcup():
    """Write-up admin for World Cup matches. Color tag supported."""
    date_str = request.args.get("date", _eastern_today())
    if not _valid_date_str(date_str):
        date_str = _eastern_today()

    if request.method == "POST":
        event_id = request.form.get("event_id", "").strip()
        text = request.form.get("text", "")
        color = request.form.get("color", "").strip() or None
        if event_id:
            wc_save_writeup(event_id, text, color=color)
            flash("Write-up saved.", "success")
        return redirect(url_for("admin_worldcup", date=date_str))

    slate, _ = get_matchday(date_str)
    if slate is None:
        slate = []
    wc_attach_writeups(slate)

    return render_template("worldcup/admin.html", slate=slate, date_str=date_str)


@app.route("/admin/golf", methods=["GET", "POST"])
@_admin_required
def admin_golf():
    """PGA write-up admin."""
    if request.method == "POST":
        event_id = request.form.get("event_id", "").strip()
        text = request.form.get("text", "")
        color = request.form.get("color", "").strip() or None
        if event_id:
            golf_save_writeup(event_id, text, color=color)
            flash("Write-up saved.", "success")
        return redirect(url_for("admin_golf"))

    slate, _ = get_pga_slate()
    if slate is None:
        slate = []
    golf_attach_writeups(slate)
    return render_template("golf/admin.html", slate=slate)


@app.route("/admin/nfl", methods=["GET", "POST"])
@_admin_required
def admin_nfl():
    """NFL write-up admin. One note per game keyed by ESPN event_id."""
    if request.method == "POST":
        event_id = request.form.get("event_id", "").strip()
        text = request.form.get("text", "")
        color = request.form.get("color", "").strip() or None
        if event_id:
            nfl_save_writeup(event_id, text, color=color)
            flash("Write-up saved.", "success")
        return redirect(url_for("admin_nfl"))

    games, _ = get_nfl_slate()
    if games is None:
        games = []
    nfl_attach_writeups(games)
    return render_template("nfl/admin.html", slate=games)


@app.route("/admin/cfb", methods=["GET", "POST"])
@_admin_required
def admin_cfb():
    """CFB write-up admin. One note per game keyed by ESPN event_id.
    Kevin's stated intent: wire the capability in even if he doesn't post
    notes every week — the option is there for marquee matchups."""
    from cfb import storage as cfb_storage
    if request.method == "POST":
        event_id = request.form.get("event_id", "").strip()
        text = request.form.get("text", "")
        color = request.form.get("color", "").strip() or None
        if event_id:
            cfb_storage.save_writeup(event_id, text, color=color)
            flash("Write-up saved.", "success")
        return redirect(url_for("admin_cfb"))

    games, _ = get_cfb_slate()
    if games is None:
        games = []
    cfb_storage.attach_writeups_to_slate(games)
    return render_template("ncaaf/admin.html", slate=games)


@app.route("/admin/mls", methods=["GET", "POST"])
@_admin_required
def admin_mls():
    """MLS write-up admin. One note per match keyed by ESPN event_id.
    Notes auto-expire when the match drops off the slate (mls/cache.py
    calls mls.storage.delete_orphaned at the end of each rebuild)."""
    if request.method == "POST":
        event_id = request.form.get("event_id", "").strip()
        text = request.form.get("text", "")
        color = request.form.get("color", "").strip() or None
        if event_id:
            mls_save_writeup(event_id, text, color=color)
            flash("Write-up saved.", "success")
        return redirect(url_for("admin_mls"))

    matches, _ = get_mls_slate()
    if matches is None:
        matches = []
    mls_attach_writeups(matches)
    return render_template("mls/admin.html", slate=matches)


@app.route("/admin/prem", methods=["GET", "POST"])
@_admin_required
def admin_prem():
    """Premier League write-up admin. One note per match keyed by ESPN
    event_id. Notes auto-delete when matches drop off the slate
    (prem/cache.py calls prem.storage.delete_orphaned after each rebuild)."""
    if request.method == "POST":
        event_id = request.form.get("event_id", "").strip()
        text = request.form.get("text", "")
        color = request.form.get("color", "").strip() or None
        if event_id:
            prem_save_writeup(event_id, text, color=color)
            flash("Write-up saved.", "success")
        return redirect(url_for("admin_prem"))

    matches, _ = get_prem_slate()
    if matches is None:
        matches = []
    prem_attach_writeups(matches)
    return render_template("prem/admin.html", slate=matches)


@app.route("/admin/nascar", methods=["GET", "POST"])
@_admin_required
def admin_nascar():
    """NASCAR write-up admin."""
    if request.method == "POST":
        event_id = request.form.get("event_id", "").strip()
        text = request.form.get("text", "")
        color = request.form.get("color", "").strip() or None
        if event_id:
            nascar_save_writeup(event_id, text, color=color)
            flash("Write-up saved.", "success")
        return redirect(url_for("admin_nascar"))

    slate, _ = get_nascar_slate()
    if slate is None:
        slate = []
    nascar_attach_writeups(slate)
    return render_template("nascar/admin.html", slate=slate)


@app.route("/admin/cws", methods=["GET", "POST"])
@_admin_required
def admin_cws():
    """CWS write-up admin — one note per DAY, covers all games that day.
    The writeup is keyed by date_str (YYYY-MM-DD) instead of per game."""
    date_str = request.args.get("date", _eastern_today())
    if not _valid_date_str(date_str):
        date_str = _eastern_today()
    if request.method == "POST":
        target_date = request.form.get("event_id", "").strip()
        text = request.form.get("text", "")
        color = request.form.get("color", "").strip() or None
        if target_date:
            cws_save_writeup(target_date, text, color=color)
            flash("Daily note saved.", "success")
        return redirect(url_for("admin_cws", date=date_str))

    # Build the tournament-window date list from the canonical CWS constants
    # so we don't drift from the actual schedule.
    from cws.venue import CWS_2026_START, CWS_2026_END
    start = datetime.strptime(CWS_2026_START, "%Y-%m-%d").date()
    end   = datetime.strptime(CWS_2026_END,   "%Y-%m-%d").date()
    dates = []
    cur = start
    while cur <= end:
        ds = cur.strftime("%Y-%m-%d")
        dates.append({
            "date_str": ds,
            "display":  cur.strftime("%a %b %-d"),
            "writeup":  cws_get_writeup(ds),
        })
        cur += timedelta(days=1)
    return render_template("cws/admin.html", dates=dates, date_str=date_str)


# ===== SEO files =====

# Personal-site sitemap (kevinrothwx.com)
# Format: (path, priority, changefreq, lastmod). If lastmod is None the
# sitemap route substitutes today's date. Explicit lastmod dates should
# reflect the last meaningful edit — this is what Google actually uses
# as a freshness signal.
KEVINROTHWX_STATIC_URLS = [
    ("/",         "1.0", "weekly",  "2026-06-15"),
    ("/about",    "0.9", "monthly", "2026-06-15"),
    ("/press",    "0.8", "monthly", "2026-06-15"),
    ("/overcast", "0.9", "monthly", "2026-06-15"),
    ("/contact",  "0.5", "yearly",  "2026-06-01"),
]

# Product-site sitemap (mysportsweather.com)
# Sport hubs are refreshed continually — use today. Evergreen content
# (articles, about, contact) gets a fixed lastmod tied to publication or
# last edit, so Google doesn't treat every URL as freshly modified daily.
MYSPORTSWEATHER_STATIC_URLS = [
    ("/",                                 "1.0",  "daily",   None),
    ("/mlb",                              "0.95", "hourly",  None),
    ("/mlb/tomorrow",                     "0.9",  "hourly",  None),
    ("/worldcup",                         "0.9",  "hourly",  None),
    ("/cws",                              "0.85", "hourly",  None),
    ("/golf",                             "0.85", "daily",   None),
    ("/nascar",                           "0.85", "daily",   None),
    ("/ncaaf",                            "0.85", "daily",   None),
    ("/nfl",                              "0.9",  "hourly",  None),
    ("/mls",                              "0.85", "hourly",  None),
    ("/prem",                             "0.9",  "hourly",  None),
    ("/prem/guides",                      "0.75", "monthly", "2026-07-03"),
    ("/ipl",                              "0.8",  "monthly", "2026-07-03"),
    ("/horse",                            "0.85", "daily",   None),
    ("/mlb-weather",                      "0.8",  "monthly", "2026-06-27"),
    ("/mlb-weather/wind-rules",           "0.8",  "monthly", "2026-06-27"),
    ("/mlb-weather/retractable-roofs",    "0.8",  "monthly", "2026-06-27"),
    ("/mlb-weather/stadium-rankings",     "0.8",  "monthly", "2026-06-27"),
    ("/nfl-weather",                      "0.8",  "monthly", "2026-06-15"),
    ("/pga-weather",                      "0.8",  "monthly", "2026-06-15"),
    ("/overcast",                         "0.9",  "monthly", "2026-06-15"),
    ("/about",                            "0.7",  "monthly", "2026-06-15"),
    ("/contact",                          "0.5",  "yearly",  "2026-06-01"),
]


@app.route("/sitemap.xml")
def sitemap():
    """Sitemap is per-hostname. kevinrothwx.com lists only personal pages;
    mysportsweather.com lists sport pages plus the dynamic per-date hubs.
    The same Flask service emits a different sitemap for each domain so
    Google doesn't see duplicate content across the two.
    """
    brand = get_site_brand(request.host)
    base_url = brand["site_url"]

    if brand["is_product_site"]:
        static_urls = list(MYSPORTSWEATHER_STATIC_URLS)
        # Dynamic MLB date-specific URLs (today + tomorrow)
        dynamic_urls = []
        # Evergreen MLB stadium landing pages (one per current park). These
        # are essentially static content, so use a fixed lastmod tied to
        # the batch publication date.
        for content in STADIUM_CONTENT.values():
            dynamic_urls.append(
                (f"/mlb/stadium/{content['slug']}", "0.8", "monthly", "2026-07-02")
            )
        # Evergreen MLB team landing pages (one per current MLB team).
        for content in TEAM_CONTENT.values():
            dynamic_urls.append(
                (f"/mlb/team/{content['slug']}", "0.8", "monthly", "2026-07-02")
            )
        # Evergreen NFL stadium landing pages (30 unique stadiums for 32 teams;
        # MetLife and SoFi are shared).
        for content in NFL_STADIUM_CONTENT.values():
            dynamic_urls.append(
                (f"/nfl/stadium/{content['slug']}", "0.8", "monthly", "2026-07-02")
            )
        # Evergreen NFL team landing pages (32 teams).
        for content in TEAM_CONTENT_NFL.values():
            dynamic_urls.append(
                (f"/nfl/team/{content['slug']}", "0.8", "monthly", "2026-07-02")
            )
        # Evergreen NASCAR track landing pages.
        for content in TRACK_CONTENT.values():
            dynamic_urls.append(
                (f"/nascar/track/{content['slug']}", "0.75", "monthly", "2026-07-02")
            )
        # Evergreen PGA course landing pages.
        for content in COURSE_CONTENT.values():
            dynamic_urls.append(
                (f"/golf/course/{content['slug']}", "0.75", "monthly", "2026-07-02")
            )
        # Evergreen NCAAF top-25 stadium landing pages.
        for content in STADIUM_CONTENT_CFB.values():
            dynamic_urls.append(
                (f"/ncaaf/stadium/{content['slug']}", "0.75", "monthly", "2026-07-02")
            )
        # Evergreen MLS team + stadium landing pages.
        for content in TEAM_CONTENT_MLS.values():
            dynamic_urls.append(
                (f"/mls/team/{content['slug']}", "0.75", "monthly", "2026-07-02")
            )
        for content in STADIUM_CONTENT_MLS.values():
            dynamic_urls.append(
                (f"/mls/stadium/{content['slug']}", "0.75", "monthly", "2026-07-02")
            )
        # Evergreen Grand Slam venue landing pages.
        for content in TENNIS_VENUE_CONTENT.values():
            dynamic_urls.append(
                (f"/tennis/venue/{content['slug']}", "0.8", "monthly", "2026-07-02")
            )
        # Evergreen Premier League team + stadium landing pages.
        for content in TEAM_CONTENT_PREM.values():
            dynamic_urls.append(
                (f"/prem/team/{content['slug']}", "0.75", "monthly", "2026-07-03")
            )
        for content in STADIUM_CONTENT_PREM.values():
            dynamic_urls.append(
                (f"/prem/stadium/{content['slug']}", "0.75", "monthly", "2026-07-03")
            )
        # Evergreen IPL franchise + ground landing pages.
        for content in TEAM_CONTENT_IPL.values():
            dynamic_urls.append(
                (f"/ipl/team/{content['slug']}", "0.75", "monthly", "2026-07-03")
            )
        for content in GROUND_CONTENT_IPL.values():
            dynamic_urls.append(
                (f"/ipl/ground/{content['slug']}", "0.75", "monthly", "2026-07-03")
            )
        for d in (_eastern_today(), _eastern_tomorrow()):
            slate, _ = get_slate(d, allow_build=False)
            if not slate:
                continue
            dynamic_urls.append((f"/mlb/{d}", "0.85", "hourly"))
            for g in slate:
                dynamic_urls.append((f"/mlb/{d}/{g['slug']}", "0.7", "hourly"))
        # World Cup matchday + per-match URLs (today + next 2 days)
        for offset in (0, 1, 2):
            d = (datetime.now(EASTERN_TZ) + timedelta(days=offset)).strftime("%Y-%m-%d")
            wc_slate, _ = get_matchday(d, allow_build=False)
            if not wc_slate:
                continue
            dynamic_urls.append((f"/worldcup/{d}", "0.85", "hourly"))
            for m in wc_slate:
                dynamic_urls.append((f"/worldcup/{d}/{m['slug']}", "0.7", "hourly"))
        # NFL per-game URLs across the 8-day cache window.
        try:
            nfl_games, _ = get_nfl_slate(allow_build=False)
            if nfl_games:
                for g in nfl_games:
                    d_iso = g.get("kickoff_date_eastern")
                    slug = g.get("slug")
                    if d_iso and slug:
                        dynamic_urls.append((f"/nfl/{d_iso}/{slug}", "0.75", "hourly"))
        except Exception as e:
            print(f"[sitemap] NFL dynamic URLs failed: {e}", flush=True)

        # Premier League per-match URLs. Slate covers ~7 days; emit a
        # /prem/<date>/<slug> URL per match so each is independently
        # indexable. Off-season returns an empty list, which is fine.
        try:
            prem_matches, _ = get_prem_slate(allow_build=False)
            if prem_matches:
                for m in prem_matches:
                    d_iso = m.get("date_local")
                    slug = m.get("slug")
                    if d_iso and slug:
                        dynamic_urls.append((f"/prem/{d_iso}/{slug}", "0.7", "hourly"))
        except Exception as e:
            print(f"[sitemap] Premier League dynamic URLs failed: {e}", flush=True)

        # MLS per-match URLs. Slate covers ~7 days; emit a /mls/<date>/<slug>
        # URL for every match so each is independently indexable. The
        # /mls hub itself is already in the static block.
        try:
            mls_slate, _ = get_mls_slate(allow_build=False)
            if mls_slate:
                emitted_dates = set()
                for m in mls_slate:
                    d_iso = m.get("date_local")
                    slug = m.get("slug")
                    if not d_iso or not slug:
                        continue
                    if d_iso not in emitted_dates:
                        emitted_dates.add(d_iso)
                    dynamic_urls.append((f"/mls/{d_iso}/{slug}", "0.7", "hourly"))
        except Exception as e:
            print(f"[sitemap] MLS dynamic URLs failed: {e}", flush=True)

        # Tennis Grand Slam URLs — only when a Slam is active. Per-Slam
        # permanent URLs (e.g. /tennis/wimbledon) are listed in the static
        # block below since they're evergreen SEO targets. Per-day URLs
        # (e.g. /tennis/wimbledon/2026-07-04) are added dynamically while
        # the slam is in window so each day is independently indexable.
        if is_any_slam_active():
            dynamic_urls.append(("/tennis", "0.9", "hourly"))
            slam = active_slam()
            if slam:
                dynamic_urls.append((f"/tennis/{slam['slam_id']}", "0.85", "hourly"))
                # Add per-day URLs for the active slam window
                slam_slate, _ = get_slam_slate_by_id(slam["slam_id"])
                if slam_slate and slam_slate.get("days"):
                    for day in slam_slate["days"]:
                        d_iso = day["date_local"].isoformat()
                        dynamic_urls.append(
                            (f"/tennis/{slam['slam_id']}/{d_iso}", "0.7", "daily")
                        )
        all_urls = static_urls + dynamic_urls
    else:
        # Personal site — no sport pages, no dynamic.
        all_urls = list(KEVINROTHWX_STATIC_URLS)

    today_str = datetime.now(EASTERN_TZ).strftime("%Y-%m-%d")
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for entry in all_urls:
        # Entries are either (path, priority, changefreq) — legacy 3-tuple
        # from the dynamic builders — or (path, priority, changefreq, lastmod)
        # from the static tables. lastmod=None means "use today's date."
        if len(entry) == 4:
            path, priority, changefreq, lastmod = entry
        else:
            path, priority, changefreq = entry
            lastmod = None
        lastmod_str = lastmod or today_str
        xml.append("  <url>")
        xml.append(f"    <loc>{base_url}{path}</loc>")
        xml.append(f"    <lastmod>{lastmod_str}</lastmod>")
        xml.append(f"    <changefreq>{changefreq}</changefreq>")
        xml.append(f"    <priority>{priority}</priority>")
        xml.append("  </url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    """robots.txt with explicit allowlists for major AI crawlers.

    The wildcard User-agent: * already grants access to AI bots, but explicit
    blocks signal active welcome. Each AI bot block repeats the /admin Disallow
    so the boundary is preserved (UA-specific rules override the wildcard
    entirely under the robots.txt spec, so they don't inherit Disallow rules
    from the wildcard block).
    """
    brand = get_site_brand(request.host)
    base_url = brand["site_url"]

    blocks = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin",
        "Disallow: /admin/",
        "",
    ]

    ai_bots = [
        "GPTBot",
        "OAI-SearchBot",
        "ChatGPT-User",
        "ClaudeBot",
        "anthropic-ai",
        "Claude-Web",
        "PerplexityBot",
        "Perplexity-User",
        "Google-Extended",
        "Bingbot",
        "Applebot",
        "Applebot-Extended",
        "Bytespider",
        "Meta-ExternalAgent",
    ]
    for bot in ai_bots:
        blocks.extend([
            f"User-agent: {bot}",
            "Allow: /",
            "Disallow: /admin",
            "Disallow: /admin/",
            "",
        ])

    blocks.append(f"Sitemap: {base_url}/sitemap.xml")
    body = "\n".join(blocks) + "\n"
    return Response(body, mimetype="text/plain")


# ===== IndexNow + LLM discoverability =====
# IndexNow protocol pushes URL updates directly to Bing and Yandex (and
# indirectly ChatGPT search, which reads the Bing index). The verification
# file at /<KEY>.txt is required so search engines can confirm site ownership.
# llms.txt is an emerging convention (llmstxt.org) for AI crawlers.

@app.route(f"/{INDEXNOW_KEY}.txt")
def indexnow_key_file():
    """IndexNow ownership verification file. Must contain only the key."""
    return Response(INDEXNOW_KEY, mimetype="text/plain")


@app.route("/llms.txt")
def llms_txt():
    """LLM-friendly site overview. Only served on the product site."""
    brand = get_site_brand(request.host)
    if not brand["is_product_site"]:
        abort(404)

    base = brand["site_url"]
    body = (
        "# MySportsWeather\n\n"
        "> Free sports weather forecasts by Kevin Roth, a professional meteorologist "
        "with 15+ years of experience covering MLB, NFL, NCAAF, PGA Tour, NASCAR, "
        "World Cup soccer, and Grand Slam tennis. Every forecast is stadium-specific "
        "with hourly temperature, wind direction relative to field orientation, "
        "precipitation probability, retractable-roof toggles for indoor venues, and "
        "written notes from Kevin when weather actually affects game outcomes.\n\n"
        "Built by a meteorologist, not generated by AI. Forecasts cited by ESPN, "
        "MLB Network, Action Network, and major sportsbooks.\n\n"
        "## Sport Coverage\n\n"
        f"- [MLB Weather Today]({base}/mlb): All 30 ballparks. Hourly forecast at first pitch, wind direction relative to home plate, retractable-roof toggles for the seven indoor venues.\n"
        f"- [World Cup 2026]({base}/worldcup): Match weather across all 16 host cities in the US, Canada, and Mexico.\n"
        f"- [PGA Tour]({base}/golf): Round-by-round tournament forecasts with HRRR high-resolution model overlay.\n"
        f"- [NASCAR Cup Series]({base}/nascar): Race-day forecasts for every Cup round.\n"
        f"- [MLS]({base}/mls): Major League Soccer match weather for all 29 venues, with retractable-roof flags for Atlanta and Vancouver.\n"
        f"- [Grand Slam Tennis]({base}/tennis): Wimbledon, US Open, Australian Open, Roland-Garros — only active during Slam weeks.\n"
        f"- [College Football]({base}/ncaaf): FBS coverage launching August 29, 2026 (Week 1).\n"
        f"- [NFL]({base}/nfl): Game-day forecasts for every preseason, regular-season, and playoff game across all 32 stadiums. Indoor venues flagged; retractable-roof toggles for Atlanta, Dallas, Houston, Indianapolis, Arizona.\n\n"
        "## About\n\n"
        f"- [About Kevin Roth]({base}/about): Background, credentials, press citations.\n"
        f"- [OVERcast]({base}/overcast): Kevin's professional sports betting app with park-tuned weather impact scoring.\n\n"
        "## Evergreen Reference\n\n"
        f"- [MLB Weather Guide]({base}/mlb-weather): How weather affects baseball.\n"
        f"- [NFL Weather Guide]({base}/nfl-weather): How weather affects football.\n"
        f"- [PGA Weather Guide]({base}/pga-weather): How weather affects golf.\n\n"
        "## Author\n\n"
        "Kevin Roth is a professional sports meteorologist. "
        "X: [@KevinRothWx](https://x.com/KevinRothWx). "
        "Personal site: [kevinrothwx.com](https://kevinrothwx.com).\n"
    )
    return Response(body, mimetype="text/markdown; charset=utf-8")


@app.route("/admin/nws-health")
@_admin_required
def admin_nws_health():
    """NWS API health dashboard — rolling counts + circuit breaker state."""
    health = nws_health_snapshot()
    circuit = cfb_nws_circuit_status()

    rows = []
    for ev in reversed(health.get("sample_recent") or []):
        ts = ev["epoch"]
        ago_sec = int(time.time() - ts) if ts else 0
        rows.append({
            "outcome": ev["outcome"],
            "info": ev["info"],
            "ago": f"{ago_sec // 60}m {ago_sec % 60}s ago" if ago_sec > 60 else f"{ago_sec}s ago",
        })

    counts = health.get("counts") or {}
    recent_5min = health.get("recent_rate_limits_5min", 0)
    threshold = health.get("alert_threshold", 5)
    over_threshold = recent_5min >= threshold

    alert_banner = (
        '<div class="alert"><strong>Over threshold:</strong> '
        f'{recent_5min} rate-limit events in the last 5 minutes (threshold '
        f'{threshold}). Email alert was sent (or suppressed by cooldown).</div>'
    ) if over_threshold else (
        '<div class="ok"><strong>Healthy:</strong> '
        f'{recent_5min}/{threshold} rate-limit events in the last 5 minutes. '
        'No alerts pending.</div>'
    )

    style = (
        "body{font-family:-apple-system,system-ui,sans-serif;max-width:900px;"
        "margin:2rem auto;padding:0 1rem;color:#1a1a1a}"
        "h1{margin-top:0}"
        ".alert{background:#fee;border-left:4px solid #c33;padding:1rem;margin:1rem 0}"
        ".ok{background:#efe;border-left:4px solid #393;padding:1rem;margin:1rem 0}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem;margin:1rem 0}"
        ".stat{background:#f8f8f8;padding:1rem;border-radius:4px}"
        ".stat-label{font-size:.85rem;color:#666;text-transform:uppercase;letter-spacing:.05em}"
        ".stat-value{font-size:2rem;font-weight:600;margin-top:.25rem}"
        ".stat-value.warn{color:#c33}"
        "table{width:100%;border-collapse:collapse;margin-top:1rem}"
        "th,td{text-align:left;padding:.5rem;border-bottom:1px solid #eee;font-size:.9rem}"
        "th{background:#f0f0f0}"
        ".outcome-ok{color:#393}"
        ".outcome-rate_limit{color:#c33;font-weight:600}"
        ".outcome-timeout,.outcome-server_error,.outcome-other_error{color:#c80}"
        "code{background:#f0f0f0;padding:.1rem .3rem;border-radius:2px;font-size:.85rem}"
    )

    stats_html = (
        '<div class="grid">'
        f'<div class="stat"><div class="stat-label">OK responses (1h)</div><div class="stat-value">{counts.get("ok", 0)}</div></div>'
        f'<div class="stat"><div class="stat-label">Rate limits (1h)</div><div class="stat-value{" warn" if counts.get("rate_limit", 0) > 0 else ""}">{counts.get("rate_limit", 0)}</div></div>'
        f'<div class="stat"><div class="stat-label">Server errors (1h)</div><div class="stat-value">{counts.get("server_error", 0)}</div></div>'
        f'<div class="stat"><div class="stat-label">Timeouts (1h)</div><div class="stat-value">{counts.get("timeout", 0)}</div></div>'
        f'<div class="stat"><div class="stat-label">CFB circuit breaker</div><div class="stat-value{" warn" if circuit["open"] else ""}">{"OPEN" if circuit["open"] else "closed"}</div></div>'
        f'<div class="stat"><div class="stat-label">CFB gridpoint cache</div><div class="stat-value">{cfb_gridpoint_cache_size()}</div></div>'
        f'<div class="stat"><div class="stat-label">Frozen CFB snapshots</div><div class="stat-value">{cfb_frozen_count()}</div></div>'
        f'<div class="stat"><div class="stat-label">Frozen MLS snapshots</div><div class="stat-value">{mls_frozen_count()}</div></div>'
        f'<div class="stat"><div class="stat-label">Frozen NFL snapshots</div><div class="stat-value">{nfl_frozen_count()}</div></div>'
        f'<div class="stat"><div class="stat-label">Frozen Prem snapshots</div><div class="stat-value">{prem_frozen_count()}</div></div>'
        '</div>'
    )

    rows_html = ""
    if rows:
        for r in rows:
            rows_html += (
                f'<tr><td>{r["ago"]}</td>'
                f'<td class="outcome-{r["outcome"]}">{r["outcome"]}</td>'
                f'<td><code>{r["info"]}</code></td></tr>'
            )
    else:
        rows_html = '<tr><td colspan="3" style="color:#888">No NWS calls recorded yet.</td></tr>'

    body = (
        f'<!DOCTYPE html><html><head><title>NWS health</title><style>{style}</style></head>'
        f'<body><h1>NWS API health</h1>{alert_banner}{stats_html}'
        f'<h2>Recent events (last 20)</h2>'
        f'<table><thead><tr><th>When</th><th>Outcome</th><th>Detail</th></tr></thead>'
        f'<tbody>{rows_html}</tbody></table>'
        f'<p style="color:#888;font-size:.85rem;margin-top:2rem">'
        f'Counters reset on server restart. Email alerts go to ALERTS_TO_EMAIL '
        f'when rate-limit count crosses threshold, with a 1-hour cooldown.</p>'
        f'</body></html>'
    )
    return Response(body, mimetype="text/html")


def _msw_all_url_paths() -> list[str]:
    """Return every URL path mysportsweather.com's sitemap would emit.

    Mirrors the URL-building logic in the /sitemap.xml route but returns
    only paths (not lastmod/changefreq/priority tuples). Used by the
    IndexNow admin push so a single click submits ALL landing pages —
    not just the ~23 static hubs + today's MLB games (which was the old
    behavior and missed all evergreen team/stadium/course/venue pages).

    Duplicates the sitemap's URL enumeration intentionally: the sitemap
    route is SEO-critical and we don't want to refactor it in the same
    change as the IndexNow fix. If we add a new sport later, both places
    need updating.
    """
    paths = [entry[0] for entry in MYSPORTSWEATHER_STATIC_URLS]

    # Evergreen landing pages (all sports)
    for content in STADIUM_CONTENT.values():
        paths.append(f"/mlb/stadium/{content['slug']}")
    for content in TEAM_CONTENT.values():
        paths.append(f"/mlb/team/{content['slug']}")
    for content in NFL_STADIUM_CONTENT.values():
        paths.append(f"/nfl/stadium/{content['slug']}")
    for content in TEAM_CONTENT_NFL.values():
        paths.append(f"/nfl/team/{content['slug']}")
    for content in TRACK_CONTENT.values():
        paths.append(f"/nascar/track/{content['slug']}")
    for content in COURSE_CONTENT.values():
        paths.append(f"/golf/course/{content['slug']}")
    for content in STADIUM_CONTENT_CFB.values():
        paths.append(f"/ncaaf/stadium/{content['slug']}")
    for content in TEAM_CONTENT_MLS.values():
        paths.append(f"/mls/team/{content['slug']}")
    for content in STADIUM_CONTENT_MLS.values():
        paths.append(f"/mls/stadium/{content['slug']}")
    for content in TENNIS_VENUE_CONTENT.values():
        paths.append(f"/tennis/venue/{content['slug']}")
    for content in TEAM_CONTENT_PREM.values():
        paths.append(f"/prem/team/{content['slug']}")
    for content in STADIUM_CONTENT_PREM.values():
        paths.append(f"/prem/stadium/{content['slug']}")
    for content in TEAM_CONTENT_IPL.values():
        paths.append(f"/ipl/team/{content['slug']}")
    for content in GROUND_CONTENT_IPL.values():
        paths.append(f"/ipl/ground/{content['slug']}")

    # MLB per-game URLs (today + tomorrow)
    for d in (_eastern_today(), _eastern_tomorrow()):
        slate, _ = get_slate(d, allow_build=False)
        if not slate:
            continue
        paths.append(f"/mlb/{d}")
        for g in slate:
            paths.append(f"/mlb/{d}/{g['slug']}")

    # World Cup per-match URLs (next 3 days)
    for offset in (0, 1, 2):
        d = (datetime.now(EASTERN_TZ) + timedelta(days=offset)).strftime("%Y-%m-%d")
        wc_slate, _ = get_matchday(d, allow_build=False)
        if not wc_slate:
            continue
        paths.append(f"/worldcup/{d}")
        for m in wc_slate:
            paths.append(f"/worldcup/{d}/{m['slug']}")

    # NFL per-game URLs across the ~8-day cache window
    try:
        nfl_games, _ = get_nfl_slate(allow_build=False)
        if nfl_games:
            for g in nfl_games:
                d_iso = g.get("kickoff_date_eastern")
                slug = g.get("slug")
                if d_iso and slug:
                    paths.append(f"/nfl/{d_iso}/{slug}")
    except Exception as e:
        print(f"[indexnow] NFL dynamic URLs failed: {e}", flush=True)

    # Premier League per-match URLs
    try:
        prem_matches, _ = get_prem_slate(allow_build=False)
        if prem_matches:
            for m in prem_matches:
                d_iso = m.get("date_local")
                slug = m.get("slug")
                if d_iso and slug:
                    paths.append(f"/prem/{d_iso}/{slug}")
    except Exception as e:
        print(f"[indexnow] Premier League dynamic URLs failed: {e}", flush=True)

    # MLS per-match URLs
    try:
        mls_slate, _ = get_mls_slate(allow_build=False)
        if mls_slate:
            for m in mls_slate:
                d_iso = m.get("date_local")
                slug = m.get("slug")
                if d_iso and slug:
                    paths.append(f"/mls/{d_iso}/{slug}")
    except Exception as e:
        print(f"[indexnow] MLS dynamic URLs failed: {e}", flush=True)

    # Tennis Grand Slam URLs (only when active)
    if is_any_slam_active():
        paths.append("/tennis")
        slam = active_slam()
        if slam:
            paths.append(f"/tennis/{slam['slam_id']}")
            slam_slate, _ = get_slam_slate_by_id(slam["slam_id"])
            if slam_slate and slam_slate.get("days"):
                for day in slam_slate["days"]:
                    d_iso = day["date_local"].isoformat()
                    paths.append(f"/tennis/{slam['slam_id']}/{d_iso}")

    # De-duplicate while preserving order
    seen = set()
    unique = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


@app.route("/admin/indexnow", methods=["GET", "POST"])
@_admin_required
def admin_indexnow_push():
    """Manual IndexNow push of current sitemap URLs to Bing/Yandex/ChatGPT-search.

    Submits the FULL sitemap URL list (~400 URLs including every evergreen
    landing page + active per-game URLs), not just the static hubs. IndexNow
    accepts up to 10K URLs per request so a single push covers everything.
    """
    brand = get_site_brand(request.host)
    if not brand["is_product_site"]:
        return Response("IndexNow only configured for mysportsweather.com.", 400)

    base_url = brand["site_url"]

    if request.method == "POST":
        paths = _msw_all_url_paths()
        urls = [f"{base_url}{p}" for p in paths]
        ok = indexnow_notify(urls, host="mysportsweather.com")
        msg = f"Pushed {len(urls)} URLs to IndexNow. Result: {'OK' if ok else 'FAILED (check logs)'}"
        return Response(
            f"<html><body><p>{msg}</p><p><a href='/admin/indexnow'>Back</a></p></body></html>",
            mimetype="text/html"
        )

    return Response(
        "<html><body>"
        "<h2>IndexNow push</h2>"
        "<p>Pushes the sitemap URL list to Bing/Yandex (and indirectly ChatGPT search).</p>"
        f"<p>Verification file: <a href='/{INDEXNOW_KEY}.txt'>/{INDEXNOW_KEY}.txt</a></p>"
        "<form method='POST'><button type='submit'>Push now</button></form>"
        "</body></html>",
        mimetype="text/html"
    )


# ── Horse racing routes ─────────────────────────────────────────────
# Hand-curated marquee US thoroughbred stakes days. WeatherAPI primary
# (via horse.slate), HRRR toggle overlay per race, freeze-at-post-time
# for post-race review.

@app.route("/horse")
def horse_root():
    """Horse racing stakes-day hub. Lists upcoming Grade 1/2 stakes
    with high/wind/precip summary tiles. Deep-links into per-race
    detail pages with hourly + HRRR toggle.
    """
    slate, meta = get_horse_slate(allow_build=True)
    return render_template(
        "horse/slate.html",
        slate=slate,
        meta=meta,
        canonical_path="/horse",
    )


@app.route("/horse/<race_id>")
def horse_race(race_id):
    """Per-race detail: hourly forecast around post time + HRRR + freeze."""
    race_seed = get_horse_stakes_race(race_id)
    if not race_seed:
        abort(404)
    try:
        race = build_horse_stakes_day(race_seed)
    except Exception as e:
        print(f"[horse.race] build failed for {race_id}: {e}", flush=True)
        race = {**race_seed, "track_meta": None, "day_summary": None,
                "day_hourly": [], "day_hrrr": [], "post_time_period": None,
                "forecast_source": "unavailable", "build_err": str(e),
                "race_date": None}
    return render_template(
        "horse/race.html",
        race=race,
        canonical_path=f"/horse/{race_id}",
    )


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# EOF-CANARY 2026-07-15-indexnow-full-push

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
