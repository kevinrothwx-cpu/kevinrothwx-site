"""
kevinrothwx.com — Flask app for Kevin Roth's personal authority hub.
Phase 1: marketing, bio, press, evergreen sport-weather explainers.
Phase 2 (later): forecast admin UI with color tagging.
"""

from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, abort, Response
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")


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


# ----- Routes -----

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
        # Recommended: hook up to Resend / SendGrid / SES via env-var API key.
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


# ----- SEO files -----

@app.route("/sitemap.xml")
def sitemap():
    urls = [
        ("/", "1.0", "weekly"),
        ("/about", "0.9", "monthly"),
        ("/press", "0.8", "monthly"),
        ("/overcast", "0.9", "monthly"),
        ("/mlb-weather", "0.8", "monthly"),
        ("/nfl-weather", "0.8", "monthly"),
        ("/pga-weather", "0.8", "monthly"),
        ("/contact", "0.5", "yearly"),
    ]
    today = datetime.utcnow().strftime("%Y-%m-%d")
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, priority, changefreq in urls:
        xml.append("  <url>")
        xml.append(f"    <loc>{SITE_URL}{path}</loc>")
        xml.append(f"    <lastmod>{today}</lastmod>")
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


# ----- Error handlers -----

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
