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

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

# Templates get the precip color/icon helpers as filters
app.jinja_env.filters["precip_color"] = precip_color
app.jinja_env.filters["precip_icon"]  = precip_icon

EASTERN_TZ = ZoneInfo("America/New_York")

# Start the slate warmer thread on import (gunicorn imports app:app once per worker)
start_warmer()


@app.context_processor
def inject_globals():
    """Make a few values available in every template."""
    return {
        "current_year": datetime.utcnow().year,
        "site_url": "https://kevinrothwx.com",
    }


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


@app.route("/mlb")
def mlb_root():
    """Redirect /mlb to today's slate."""
    return redirect(url_for("mlb_slate", date_str=_eastern_today()), code=302)


@app.route("/mlb/today")
def mlb_today():
    """Permalink alias for today's slate."""
    return redirect(url_for("mlb_slate", date_str=_eastern_today()), code=302)


@app.route("/mlb/tomorrow")
def mlb_tomorrow():
    """Permalink alias for tomorrow's slate."""
    return redirect(url_for("mlb_slate", date_str=_eastern_tomorrow()), code=302)


@app.route("/mlb/<date_str>")
def mlb_slate(date_str):
    """Slate page for a specific date."""
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
    )


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
        if game_pk:
            save_writeup(game_pk, text)
            flash("Write-up saved.", "success")
        return redirect(url_for("admin_mlb", date=date_str))

    slate, _ = get_slate(date_str)
    if slate is None:
        slate = []
    attach_writeups_to_slate(slate)

    return render_template("mlb/admin.html", slate=slate, date_str=date_str)


# ===== SEO files =====

@app.route("/sitemap.xml")
def sitemap():
    """
    Sitemap includes the evergreen pages plus today's slate and per-game pages
    (and tomorrow's, so Google can pre-crawl). Older archives are discoverable
    by internal link only, to keep the sitemap small.
    """
    static_urls = [
        ("/", "1.0", "daily"),
        ("/about", "0.9", "monthly"),
        ("/press", "0.8", "monthly"),
        ("/overcast", "0.9", "monthly"),
        ("/mlb/today", "0.95", "hourly"),
        ("/mlb/tomorrow", "0.9", "hourly"),
        ("/mlb-weather", "0.8", "monthly"),
        ("/nfl-weather", "0.8", "monthly"),
        ("/pga-weather", "0.8", "monthly"),
        ("/contact", "0.5", "yearly"),
    ]

    dynamic_urls = []
    for d in (_eastern_today(), _eastern_tomorrow()):
        slate, _ = get_slate(d, allow_build=False)
        if not slate:
            continue
        dynamic_urls.append((f"/mlb/{d}", "0.85", "hourly"))
        for g in slate:
            dynamic_urls.append((f"/mlb/{d}/{g['slug']}", "0.7", "hourly"))

    all_urls = static_urls + dynamic_urls
    today_str = datetime.now(EASTERN_TZ).strftime("%Y-%m-%d")
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, priority, changefreq in all_urls:
        xml.append("  <url>")
        xml.append(f"    <loc>{SITE_URL}{path}</loc>")
        xml.append(f"    <lastmod>{today_str}</lastmod>")
        xml.append(f"    <changefreq>{changefreq}</changefreq>")
        xml.append(f"    <priority>{priority}</priority>")
        xml.append("  </url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /admin/\n"
        "\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    return Response(body, mimetype="text/plain")


# ===== Error handlers =====

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
