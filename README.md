# kevinrothwx.com

Personal authority hub for Kevin Roth, sports meteorologist. Flask app, server-rendered, deployed on Render.

Phase 1: marketing, bio, press, evergreen sport-weather explainers.
Phase 2 (later): forecast admin UI with color tagging per game.

---

## Deployment to Render — step by step

You already know this flow from OVERcast. Same idea here.

### 1. Create a new GitHub repository

- Name it whatever you want (suggest: `kevinrothwx-site`)
- Make it private if you prefer; Render works with both
- Copy the URL — you'll need it in step 2

### 2. Push this code to your new repo

From your local machine (or however you do it for OVERcast):

```bash
cd kevinrothwx-site
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <your-new-repo-url>
git push -u origin main
```

### 3. Create a new Render Web Service

1. Go to https://dashboard.render.com/
2. Click **New +** → **Web Service**
3. Connect to your GitHub repo (`kevinrothwx-site`)
4. Configure:
   - **Name:** kevinrothwx (or whatever)
   - **Region:** same as OVERcast (Oregon is fine)
   - **Branch:** main
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Plan:** Free or Starter — your call
5. Add environment variables (under Environment):
   - `SECRET_KEY` — any long random string (use a password manager to generate)
   - `CONTACT_EMAIL` — your email address (optional; not actively used yet — see Email TODO below)
6. Click **Create Web Service**

Render will pull the repo, build it, and deploy. First build takes a few minutes.

### 4. Add the custom domain

1. In Render, go to your service → **Settings** → **Custom Domains**
2. Click **Add Custom Domain**
3. Enter `kevinrothwx.com` and `www.kevinrothwx.com`
4. Render will give you DNS records to add
5. Go to wherever you bought `kevinrothwx.com` (the domain registrar)
6. Add the DNS records Render gave you (usually an `A` record for the root and a `CNAME` for `www`)
7. Wait ~10–30 minutes for DNS to propagate
8. Render automatically provisions HTTPS

That's it. The site is live.

---

## Local development (optional)

If you ever want to run the site locally to preview changes:

```bash
python -m venv .venv
source .venv/bin/activate     # macOS/Linux
# or:
.venv\Scripts\activate         # Windows

pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000 in a browser.

---

## File map

```
kevinrothwx-site/
├── app.py                 # Flask app — routes, schema injection, sitemap, robots
├── requirements.txt       # Python dependencies
├── Procfile              # Tells Render to run gunicorn
├── runtime.txt           # Python version pin
├── .gitignore
├── README.md             # This file
├── templates/            # Jinja2 HTML templates
│   ├── base.html         # Global layout, schema, header/footer
│   ├── index.html        # Home
│   ├── about.html        # About + full Person JSON-LD (the AEO money page)
│   ├── press.html        # Press citations
│   ├── overcast.html     # OVERcast marketing
│   ├── mlb_weather.html  # MLB evergreen
│   ├── nfl_weather.html  # NFL evergreen
│   ├── pga_weather.html  # PGA evergreen
│   ├── contact.html      # Contact form
│   ├── contact_thanks.html
│   ├── admin.html        # Phase 2 stub
│   └── 404.html
└── static/
    ├── css/style.css     # Tiny custom CSS; Tailwind via CDN handles the rest
    ├── js/               # (empty — minimal JS lives inline)
    └── img/              # Drop kevin-roth-headshot.jpg here (1200x1200 recommended)
```

---

## TODOs (things to do after first deploy)

### 1. Add the headshot

Drop the JPEG into `static/img/kevin-roth-headshot.jpg`. About page references it. Recommended size: 1200×1200 square, optimized to <250 KB.

### 2. Add a social-share image

Create `static/img/og-default.jpg` (1200×630 recommended). This is what shows up when someone shares any page on X, LinkedIn, etc. Can be the headshot plus a name banner, or just the wordmark on a clean background.

### 3. Wire up the contact form email

Right now the contact form prints submissions to the Render log. To actually receive emails, add a service like Resend, SendGrid, or AWS SES. Look for the `# TODO: actually send the email.` comment in `app.py`.

Easiest setup: sign up for Resend (resend.com, free tier covers normal volume), get an API key, add `RESEND_API_KEY` to Render env vars, install `resend` (add to requirements.txt), and update the route to call `resend.Emails.send(...)`.

### 4. Submit the sitemap to Google Search Console

Once the site is live at `kevinrothwx.com`:

1. Go to https://search.google.com/search-console
2. Add `kevinrothwx.com` as a property
3. Verify ownership (DNS or HTML file)
4. Submit `https://kevinrothwx.com/sitemap.xml` under Sitemaps

This tells Google about every page on the site and starts the indexing clock.

### 5. Test the schema

After deploy, paste your URLs into https://validator.schema.org/ to confirm the JSON-LD parses cleanly. Especially the About page.

### 6. Test the Wikidata linkage

Once Google indexes the site (2–6 weeks), the Wikidata Q-number in your `sameAs` array should start showing up in search results for "Kevin Roth meteorologist." Watch for the Knowledge Panel to appear.

---

## Notes on architecture choices

- **Tailwind via CDN, not a build step.** Trade-off: slightly larger CSS payload on first paint (~50KB gzipped), but no Node.js build pipeline to maintain. Right call for a small marketing site.
- **Server-rendered Jinja templates, not React/Next.js.** Trade-off: no client-side interactivity, but full HTML on first paint = best possible SEO/AEO. The whole point of this site is to be machine-readable.
- **No database in Phase 1.** Content is hardcoded in templates. Adds zero infrastructure complexity. Phase 2 will add SQLite or Postgres for the forecast admin UI.
- **Schema.org JSON-LD embedded per page.** The About page carries the canonical Person entity; every other page references it via `@id`.
