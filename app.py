"""
kevinrothwx.com — Flask app for Kevin Roth's personal authority hub.
Phase 1: marketing, bio, press, evergreen sport-weather explainers.
Phase 2 (now): automated MLB weather slate + per-game pages.
Phase 3 (later): admin UI for manual write-ups (storage hook is ready).
"""

import os
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
SPORT_PATH_PREFIXES = ("/mlb", "/cws", "/worldcup", "/golf", "/nascar", "/nfl", "/ncaaf")
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

    # NFL / NCAAF — no badge during off-season (cleaner header).
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
    return render_template("mlb_weather.html")


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




# ===== NFL + NCAAF stubs (live forecasts coming when season starts) =====

NFL_KICKOFF_2026   = datetime(2026, 9, 10).date()   # Thursday night opener
NCAAF_KICKOFF_2026 = datetime(2026, 8, 29).date()    # Week 1 Saturday


@app.route("/nfl")
def nfl_root():
    today = datetime.now(EASTERN_TZ).date()
    days_until = max(0, (NFL_KICKOFF_2026 - today).days)
    return render_template("nfl/coming-soon.html",
                           sport_name="NFL", days_until=days_until,
                           kickoff_date=NFL_KICKOFF_2026.strftime("%B %-d"))


@app.route("/ncaaf")
def ncaaf_root():
    today = datetime.now(EASTERN_TZ).date()
    days_until = max(0, (NCAAF_KICKOFF_2026 - today).days)
    return render_template("ncaaf/coming-soon.html",
                           sport_name="NCAAF", days_until=days_until,
                           kickoff_date=NCAAF_KICKOFF_2026.strftime("%B %-d"))


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
KEVINROTHWX_STATIC_URLS = [
    ("/", "1.0", "weekly"),
    ("/about", "0.9", "monthly"),
    ("/press", "0.8", "monthly"),
    ("/overcast", "0.9", "monthly"),
    ("/contact", "0.5", "yearly"),
]

# Product-site sitemap (mysportsweather.com)
MYSPORTSWEATHER_STATIC_URLS = [
    ("/", "1.0", "daily"),
    ("/mlb", "0.95", "hourly"),
    ("/mlb/tomorrow", "0.9", "hourly"),
    ("/worldcup", "0.9", "hourly"),
    ("/cws", "0.85", "hourly"),
    ("/golf", "0.85", "daily"),
    ("/nascar", "0.85", "daily"),
    ("/mlb-weather", "0.8", "monthly"),
    ("/nfl-weather", "0.8", "monthly"),
    ("/pga-weather", "0.8", "monthly"),
    ("/overcast", "0.9", "monthly"),
    ("/about", "0.7", "monthly"),
    ("/contact", "0.5", "yearly"),
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
        all_urls = static_urls + dynamic_urls
    else:
        # Personal site — no sport pages, no dynamic.
        all_urls = list(KEVINROTHWX_STATIC_URLS)

    today_str = datetime.now(EASTERN_TZ).strftime("%Y-%m-%d")
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, priority, changefreq in all_urls:
        xml.append("  <url>")
        xml.append(f"    <loc>{base_url}{path}</loc>")
        xml.append(f"    <lastmod>{today_str}</lastmod>")
        xml.append(f"    <changefreq>{changefreq}</changefreq>")
        xml.append(f"    <priority>{priority}</priority>")
        xml.append("  </url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    brand = get_site_brand(request.host)
    base_url = brand["site_url"]
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /admin/\n"
        "\n"
        f"Sitemap: {base_url}/sitemap.xml\n"
    )
    return Response(body, mimetype="text/plain")


# ===== Error handlers =====

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
