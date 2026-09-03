# Session notes — kevinrothwx-site / mysportsweather.com

Read this after CLAUDE.md at the start of any new session. CLAUDE.md is workflow rules. This is the project's state, strategy, and decisions.

## Two domains, one Flask app

The same `app.py` serves both hostnames via `get_site_brand(host)`:

- **kevinrothwx.com** — Kevin Roth's personal authority hub. Bio, press, about, /overcast product page. NOT a sports forecast site.
- **mysportsweather.com** — The product site. All sport pages live here. Daily-updating forecasts, schema.org, SEO target.

A `before_request` middleware 301-redirects sport sections from kevinrothwx.com → mysportsweather.com so old links keep working.

## Brand stance (locked)

These are not preferences, they are decisions that govern code we write:

1. **"Built by a meteorologist, not AI"** is the central brand position. Every visible page must hold this line.
2. **No generative AI in user-facing text.** All "analysis" / "summary" content comes from deterministic rule-based templating (see `cfb/analysis.py`, `tennis/daily_summary.py`). When the auto-generator output looks weak, we'd rather show a short factual sentence than a long inferred one.
3. **No football/sport-outcome speculation in auto-content.** That's PropFinder/OVERcast territory and gambling-adjacent. Auto-text stays inside weather facts only. A CFB summary may say "Temperature 28°F at kickoff with sustained 19 mph wind from the west-northwest. Snow showers likely, 65% chance" but never "wind affects deep passing routes" or "expect run-heavy gameplan."
4. **Tennis exception:** court-coverage context IS in scope. Saying "matches on the 2 roofed courts will continue uninterrupted; outer courts may be delayed" is the meteorologist edge for tennis, defensible as weather-operational not game-outcome.
5. **Don't claim authorship Kevin didn't write.** Auto-generated content gets neutral framing ("Weather summary" / unlabeled prose), never "Kevin's notes" or "Kevin's analysis" unless it was actually written via the writeup admin.
6. **NWS is the credibility anchor.** Even when WeatherAPI is the better technical choice (international, missing US coverage), NWS-primary stays the default for US sports. Stability matters more than freshness — borderline wind directions oscillating between W and NW between page loads erodes trust.
7. **No specific investment advice or sportsbook recommendations.** The site is weather; OVERcast is the betting product. Keep them functionally separated.
8. **Facts only in evergreen content.** Kevin's July 2026 warning: "If you can source it, great. If you can't, bail on it." Applies to every landing page. No specific climatology numbers, distances to water bodies, dew-point ranges, etc. unless anchored to a citable source. Verifiable facts (roof type from venue module, city, geographic setting, historical widely-known things like Coors elevation) are fine.

## Strategic direction

- **mysportsweather.com is an SEO funnel into OVERcast.** Direct monetization of the site is not the focus. SEO traffic that converts to OVERcast users is.
- **AI discoverability is co-equal with traditional SEO.** AI Overview / ChatGPT search / Perplexity / Claude all extract structured facts. Every detail page gets schema.org SportsEvent + additionalProperty.
- **Evergreen landing-page SEO surge (July 2026):** built 222 new per-entity landing pages in a single session — stadium, team, track, and course pages across every sport. Each includes BreadcrumbList + Article schema, links back to the live sport hub, and (for MLB) surfaces today/tomorrow's game forecast inline instead of just a link. Design goal: rank for "Yankees weather" / "Wrigley Field weather" long-tail queries and funnel searchers straight to the live forecast.
- **International expansion is parked, not killed.** US validation comes first. Revisit Q1 2027 with 6+ months of Search Console data. Suggested order when we do: DP World Tour → Premier League → cricket → F1. Cricket is the biggest single unclaimed global opportunity (no dedicated meteorologist competitor; Metcheck is the only player and they're a 1999-built site).
- **Sport priority queue:** All in-season sports launched. Remaining: NFL live-slate build for Sept 10, ongoing CFB polish, MLS active.
- **OVERcast and mysportsweather share an outbound IP.** Anything that affects NWS rate limits on one affects the other. Hence `cfb/nws_client.py` has distinct User-Agent, sequential pacing, and a circuit breaker — same pattern should apply to any future high-volume sport.

## Technical patterns (locked)

Every new sport module follows these patterns. Don't reinvent.

### Module structure (mirror MLB / CFB)

```
sport/
  __init__.py
  venues.py          # hard-coded stadium/venue data with lat/lon/timezone
  schedule.py        # ESPN scoreboard fetcher + normalizer + per-event parse
  schedule_fallback.py  # hand-curated season when ESPN flakes
  slate.py           # weather attachment, NWS primary + WeatherAPI fallback
  cache.py           # 25-min warmer + self-healing stale rebuild + cleanup
  forecast_freeze.py # snapshot pattern at event start
  storage.py         # writeups, disk-backed via persistence.py
  analysis.py        # rule-based templated weather summary (no AI, no game-impact)
  stadium_content.py # (NEW) per-venue evergreen SEO content for landing pages
  team_content.py    # (NEW, MLB + NFL) per-team evergreen SEO content
templates/sport/
  slate.html         # the hub page
  game.html          # per-event detail page with schema.org
  stadium.html       # (NEW, MLB + NFL) evergreen per-venue guide
  team.html          # (NEW, MLB) evergreen per-team guide
```

For NASCAR, PGA, CFB — the landing pages use the shared `templates/_shared/landing.html` template instead of a bespoke per-sport template. Content still lives in each sport's `*_content.py` module.

### Warmer + cache pattern

- 25-min refresh cycle (`REFRESH_SECONDS = 25 * 60`).
- 30-min stale threshold (`STALE_CACHE_THRESHOLD_SEC = 30 * 60`). On read, if cache older than this AND `allow_build=True`, force synchronous rebuild. This is the self-heal for the "warmer thread silently died" failure mode we keep hitting.
- After rebuild, run `_cleanup_after_rebuild()`:
  - `delete_orphaned_writeups(live_event_ids)` — drops writeups for events no longer in slate
  - `forecast_freeze.clear_old(cutoff)` — drops freeze entries older than retention (7d nascar, 14d golf)
  - Safe-guarded: if slate is empty (ESPN flake), skip cleanup so transient outage can't wipe Kevin's notes

### Forecast freeze pattern

NWS rolls past hours off as time passes. Without freezing, an in-progress game's hourly table shrinks because NWS no longer serves the early hours. The freeze captures the snapshot at/before event start and serves it indefinitely.

- Module-level `forecast_freeze.py` with `has(id)`, `get(id)`, `freeze(id, ...)`, `clear_old(cutoff)`.
- Storage: disk-backed JSON via `persistence.py`.
- Decision logic in `slate.py` `build_event(event)`:
  - If event hasn't started → fetch fresh, snapshot it.
  - If event has started AND we have a snapshot → serve the snapshot.
  - If event has started AND we have no snapshot → fetch fresh (degraded but better than nothing).
- Golf is per-(tournament, round_date) composite key; everything else is per-event.

### NWS resilience (the cfb/nws_client.py pattern)

For any sport that might hit NWS hard (large Saturday slates):

- Distinct `User-Agent` per sport so NWS can attribute throttle events
- Sequential pacing with `INTER_CALL_DELAY_SEC = 0.20` (5 req/sec max, well under NWS recommendation)
- Circuit breaker: if NWS returns 429/503, trip for 10 min, all calls short-circuit to None
- Permanent in-memory `_gridpoint_cache` (stadium coordinates never change)
- Every call reports outcome to `nws_health.record()` for rolling-1h counter
- WeatherAPI fallback when NWS fails — site never breaks

### Alert pipeline

- `alerts.py` — Gmail SMTP via `GMAIL_USER` + `GMAIL_APP_PASSWORD` env vars; cooldown of 1h per condition; no-ops if env vars missing
- `nws_health.py` — rolling 1h NWS-outcome counter; fires alert at ≥5 rate-limit events in 5min window
- `/admin/nws-health` dashboard shows current state

### Discoverability (deployed)

- **IndexNow:** verification file at `/586e4a915efddc888238515477087ac3.txt`; `indexnow.py` module; `/admin/indexnow` admin push
- **llms.txt** at `/llms.txt` — site overview for AI crawlers
- **robots.txt** has explicit allowlists for GPTBot, ClaudeBot, PerplexityBot, Bingbot, etc.
- **Google Search Console** — Domain property verified for both kevinrothwx.com and mysportsweather.com
- **Bing Webmaster Tools** — imported from GSC; ChatGPT search reads Bing's index
- **schema.org** — every game/match/landing page has `SportsEvent` OR `Article` + `BreadcrumbList` + `additionalProperty` for weather metrics
- **Sitemap** — per-URL lastmod (added July 2026). Static pages carry publication-date lastmod; sport hubs and dynamic per-date URLs carry today. Format is 4-tuple `(path, priority, changefreq, lastmod)` with lastmod=None meaning today.

## SEO landing page architecture (July 2026 build)

222 new evergreen URLs live across all sports. Every page has BreadcrumbList + Article schema, canonical URL, byline linking to /about, facts strip pulled from the sport's venue module, and CTA back to the live sport hub.

### URL patterns

| Pattern | Sport | Count | Content module |
|---|---|---|---|
| `/mlb/stadium/<slug>` | MLB | 30 | `mlb/stadium_content.py` |
| `/mlb/team/<slug>` | MLB | 30 | `mlb/team_content.py` |
| `/nfl/stadium/<slug>` | NFL | 30 | `nfl/stadium_content.py` |
| `/nfl/team/<slug>` | NFL | 32 | `nfl/team_content.py` |
| `/nascar/track/<slug>` | NASCAR | 27 | `nascar/track_content.py` |
| `/golf/course/<slug>` | PGA | 48 | `golf/course_content.py` |
| `/ncaaf/stadium/<slug>` | CFB | 25 (top P5) | `cfb/stadium_content.py` |

### Discovery

- **`/mlb-weather` hub indexes all 30 MLB stadium pages** in a "Stadium guides" section for crawl-graph density.
- **MLB team pages cross-link to division rivals** (both team pages and stadium pages) via the `DIVISIONS` map in `mlb/team_content.py`.
- **Every landing page CTA points back to the sport's live forecast hub** — SEO funnel: search intent → landing page → live hub → OVERcast.
- **MLB team + stadium pages show today/tomorrow's game forecast inline** (`templates/mlb/_next_game_card.html`). Landed searcher gets the actual forecast, not just a link. Helpers: `_find_next_mlb_game_for_team()`, `_find_next_mlb_game_at_park()`. NFL stadium pages have the same wiring (`_find_next_nfl_game_at_venue()`) — active during football season.

### Shared template

`templates/_shared/landing.html` is the generic landing template used by NFL teams, NASCAR tracks, PGA courses, and NCAAF stadiums. Takes `kicker`, `back_url`, `back_label`, `title`, `facts` (list of tuples), `sections` (list of tuples), `cta_url`, `cta_label`, `breadcrumb_hub_url`, `breadcrumb_hub_label`, `breadcrumb_entity`, `canonical_path`.

MLB stadium and MLB team pages use bespoke templates (`templates/mlb/stadium.html`, `templates/mlb/team.html`) because they include the inline live-game card and the division-rivals section, which the generic template doesn't support.

### Content constraints

Kevin's warning after the initial MLB stadium content: "make sure you are not making anything up, facts only." Applied thereafter:

- Facts anchored in the venue module (roof type, city, capacity, lat/lon, CF bearing for MLB) only.
- General regional climate reputation OK (e.g. "Green Bay late-season plays cold with plains wind").
- Widely-known widely-cited facts OK (Coors elevation, Fenway Monster dimensions, retractable roof usage from Kevin's uploaded OVERcast analysis).
- No specific airport-average temperature numbers, distance-to-water claims, dew-point range claims, etc.
- No em-dashes, no clear AI sentence structure, human voice, DFS/bettor audience.

The 60 MLB pages (stadiums + teams) have some earlier-drafted numeric climate claims. If you touch that content, prefer soft geographic language over specific numbers.

## Homepage layout (July 2026 redesign)

- **Two-column hero row** (`.home-hero__row`). Left column: kicker + title + lead. Right column: compact World Cup card. Sport-card grid follows immediately below the hero, up above the fold on typical desktop viewports.
- **`.home-featured--compact` modifier** — tighter padding, smaller title, `display: flex; flex-direction: column` with `margin-top: auto` on the CTA so the two hero columns line up.
- Grid ratio: `minmax(0, 1.35fr) minmax(280px, 1fr)` at ≥900px. Stacks on mobile.
- **Soccer ball icon** in the WC card top row, right-aligned via `margin-left: auto` at 36×36.
- **Sport-card head layout** — `.home-sport-card__head`, `.home-sport-card__icon`, `.home-sport-card__heading` all had NO CSS pre-July 2026. Icons were rendering at intrinsic 24×24. Added: 40×40 icons, flex row with 0.9rem gap, `align-items: flex-start`. Also fixed the missing `<span class="home-product__name">Follow Kevin on X</span>` on the third product link, and a missing closing `</div>` on that same block that was silently breaking the styled-box CSS on the live site (nobody noticed until the section moved into view for a critical check).

## Sport-by-sport state

| Sport | Live? | Landing pages? | Source | Patterns active | Notes |
|---|---|---|---|---|---|
| MLB | yes | 30 stadium + 30 team | NWS + Open-Meteo (Toronto) | freeze (first-pitch), writeups, wind-vs-CF, next-game inline on landing pages | task #79 pending: add WeatherAPI fallback layer |
| World Cup | yes (2026) | via WC card on homepage | WeatherAPI (international) | writeups | task #81 pending: freeze at kickoff |
| PGA | yes | 48 course landing pages | NWS + WeatherAPI fallback + HRRR | freeze (per round), writeups, auto-advance, orphan cleanup | round-based composite freeze key |
| NASCAR | yes | 27 track landing pages | NWS + WeatherAPI fallback + HRRR | freeze (green flag), writeups, auto-advance, self-heal, orphan cleanup | distinct UA for OVERcast IP differentiation pattern not applied here yet |
| CWS | recurring (Jun 13-23) | no | NWS | freeze, writeups | post-season specific |
| CFB | built, launches Aug 29 | 25 top P5 stadium landing pages | NWS primary via `cfb/nws_client` + WeatherAPI fallback + HRRR | freeze, schema.org, analysis paragraph, per-game detail page | distinct UA "kevinrothwx-site/1.0 ncaaf", pacing, circuit breaker |
| NFL | slate coming Sept 10 | 30 stadium + 32 team | n/a (offseason) | landing pages have next-game wiring ready for season | |
| Tennis | yes (Wimbledon live) | no landing pages | WeatherAPI (international) | per-day detail pages, ESPN match schedule, analysis paragraph | ATP/WTA endpoints return overlapping events — dedup by competition.id |
| MLS | yes | no landing pages | ESPN + NWS | per-match detail, freeze | active season |

## ACTIVE list — Sept 2026 (use these numbers when talking to Kevin)

The task tool's list was wiped mid-session on 2026-09-02. THIS FILE is the
source of truth now. Keep it current; do not rely on the task tool.

Ordered by priority.

| # | Task | Owner |
|---|------|-------|
| 1 | Apply for DK + FD affiliates / prediction markets | Kevin |
| 2 | Full mobile formatting pass across all sports | Claude |
| 3 | NFL per-game detail pages: polish or redirect | Claude |
| 4 | Structured data on slate hub pages (/ncaaf, /nfl, /mlb) | Claude |
| 5 | /college-football-weather evergreen guide | Claude |
| 6 | Send OVERcast Live the NWS handoff doc | Kevin |
| 7 | Verify indexation in Search Console (check ~Sept 5 and ~Sept 16) | Kevin |
| 8 | Hyperlink O/U totals to sportsbook (blocked on #1) | Claude |
| 9 | GA4 event tracking on outbound + CTA clicks | Claude |
| 10 | Evaluate whether NBM is additive vs NWS | Claude |
| 11 | Editorial workflow smoke test across all sports | Claude |
| 12 | Copy cleanup: stale admin text + NASCAR meta tags | Claude |
| 13 | Automate the Postgres backup export | Claude |
| 14 | Regenerate sitemap when a write-up is published | Claude |
| 15 | Review the 19 "Not found (404)" URLs in Search Console | Kevin |

**#1 is calendar-driven.** Affiliate approval takes 2-4 weeks, so every
week of delay eats the NFL window. NOTE: DK and FD launched CFTC-regulated
prediction markets that are separate standalone apps, so an existing
sportsbook user does NOT have a Predicts account — that materially improves
the conversion case vs the sportsbook affiliate programs. Sports contracts
are only live in ~17-18 states though; confirm TX and CA before building a
plan around the geographic argument.

**Realistic expectation on #1:** affiliate revenue on this traffic is likely
a few hundred a month, not PropFinder-replacement money. OVERcast
subscriptions are the thing that closes that gap.

## COMPLETED 2026-09-02 (long session)

- **Postgres/SEO indexation crisis found and fixed.** GSC showed 45 indexed
  pages against ~500 live. Sitemap had been submitted 2026-06-17 and NEVER
  re-read — 10 weeks, status "Success" the whole time. Manual resubmit took
  discovered pages 55 -> 528. NOTE: on a domain property the sitemap must be
  submitted as a FULL URL; a relative path returns "invalid".
- **CFB game URLs were in neither sitemap nor IndexNow.** MLB/NFL/Prem/MLS
  all emitted per-game URLs; CFB emitted none. ~87 pages/week invisible.
- **~350 evergreen landing pages were orphans** — sport hubs and homepage
  linked to zero of them. Built landing_index.py + _landing_index.html.
- **Sitemap split** into an index + evergreen/games children.
- **CFB stadium pages 25 -> 134**, generated from verified field bearings
  rather than written copy (see cfb/stadium_facts.py for the reasoning and
  the no-climatology rule).
- **OVERcast promo** replacing the PropFinder CTA row.
- **Odds archive** now archives instead of deleting at 168h.
- **Homepage title/description** rewritten for football head terms.

## Older backlog (pre-Sept, still open)

1. **WeatherAPI fallback for MLB/NASCAR/CWS** (#79) — resilience, ~45min
2. **World Cup freeze at kickoff** (#81) — apply existing pattern, ~30min
3. **G5 venues completion in cfb/venues.py** (#143) — not blocking
4. **Schema.org SportsEvent on CWS + NASCAR detail pages** (#97) — BreadcrumbList is done; SportsEvent still needed on NASCAR race.html and CWS game.html for AI extractability parity
5. **OVERcast product screenshots on /overcast** (#72) — landing-page polish
6. **Pull at-first-pitch values from OVERcast directly** (#85) — match the canonical source
7. **Redis migration** (#91) — only when scaling beyond single Gunicorn worker
8. **Phase 2 PGA course maps** (#31) — original ambition, not blocking

Completed in July 2026 session (batches 1-7 + homepage redesign):
- Batch 1: MLB stadium landing pages (was #94, done)
- Batch 2: MLB team landing pages
- Batches 3-4: NFL stadium + team landing pages
- Batch 5: NASCAR track landing pages
- Batch 6: PGA course landing pages
- Batch 7: NCAAF top-25 stadium landing pages
- Live game forecast inline on MLB team + stadium pages + NFL stadium pages
- SEO Tier 1: 404 noindex, title audit, BreadcrumbList on all sport detail pages, Person schema
- 3 MLB weather deep-dive articles (wind-rules, retractable-roofs, stadium-rankings)
- Sitemap per-URL lastmod
- Golf off-by-one date fix
- MLS off-season copy + sport-nav reposition
- Homepage two-column hero with compact WC card + soccer ball icon
- Sport-card head CSS gaps filled (icons were rendering 24×24)

## OneDrive truncation playbook (CRITICAL)

This has dominated recent sessions and got even worse in the July 2026 session. Every long file eventually truncates. Templates truncate. app.py truncates repeatedly. **style.css also truncates** — added to the vulnerability list this session. **SESSION_NOTES.md truncates too** — the notes update itself needed recovery.

**Symptom types**:
- **Simple truncation**: AST/Jinja parse reports broken at a high line number near the end; tail shows a partial line ending mid-token.
- **Null-byte padding**: bash reports "source code string cannot contain null bytes"; file size is nominal but the last few dozen bytes are `\x00`. Discovered mid-July session. Recovery: `open(path, 'rb').read().rstrip(b'\x00')` and write back.
- **Duplicate lines from heredoc recovery**: On a re-recovery, the head+heredoc can duplicate a line that spans both the truncation boundary and the heredoc start. Manifests as valid-parsing but visually broken output (e.g. "Verification file" appearing twice on the admin IndexNow page).

**Recovery sequence**:
1. Read tool → get the correct cloud version.
2. `head -N file > /tmp/...` where N is the last known-good line on disk.
3. `mv` the head-truncated file into place.
4. `cat >> file <<'EOF'` to append the correct tail via heredoc (bypasses Edit-tool race).
5. `sleep 5` (let OneDrive sync settle).
6. AST/Jinja parse + tail integrity check.
7. Check for null bytes: `python3 -c "print(open(path, 'rb').read().count(b'\x00'))"`.

**Mandatory verification after ANY batch of code edits**:
- Full Python AST sweep across the repo
- Full Jinja template sweep
- Tail integrity (every touched file ends with expected closing statement)
- Null-byte scan on any file that got Edit'd
- Behavioral test: boot Flask test_client and hit affected routes
- For pre-push: `git show HEAD:file | python3 -c "ast.parse(...)"` — this is what caught the storage.py corruption that broke the Render deploy on commit `0bf2a7e`

**Batch strategy that worked in July 2026**: when adding many new features that all touch app.py, do NOT edit app.py once per feature. Build ALL the content modules and templates first, then do a single app.py edit at the end with all imports + all routes + all sitemap entries. This limits the number of truncation cascades. Recovery still needed, but 1 recovery vs 5.

**What we learned the hard way**:
- Local Read tool reads from OneDrive cloud (often clean) while bash reads from disk (often truncated). The two views can diverge by dozens of lines.
- GitHub Desktop reads from disk. So when Kevin pushes, he can push the truncated version even when Read tool showed it clean to us.
- Sometimes the on-disk file has duplicate lines from heredoc append after an earlier failed write.
- Do NOT run `git` from bash on this repo. It leaves `.git/index.lock` files that block Kevin's GitHub Desktop commits. CLAUDE.md explicitly says this. Honor it.
- **CSS truncation is silent in production for a while** because browsers cache the last-known-good stylesheet. The July 2026 style.css tail truncation (lost `.home-product__link` etc.) had likely been on the live site for an unknown period but nobody saw it because the CSS was cached in Kevin's browser.

## Deploy flow

- Kevin pushes via GitHub Desktop on Windows.
- Render auto-deploys on git push to main.
- Render service: `kevinrothwx-site`, Python 3, Starter tier ($7/mo), 1 GB persistent disk at `/var/data`.
- Procfile: `web: gunicorn -w 1 --threads 4 app:app` (single worker, threads for concurrency — task #90 fixed multi-worker cache divergence, task #17 on 2026-07-21 re-fixed it after Render dashboard override was silently reintroducing 2 workers; --threads 4 added so one slow uncached slate build doesn't block other users).
- Render Start Command MUST match Procfile (`gunicorn -w 1 --threads 4 app:app`). If the dashboard field is set, it overrides the Procfile silently. Verify via `/admin/cache-health` — PID should stay constant across refreshes.
- Render's edge cache can serve stale `/robots.txt` and similar text responses for hours after deploy. Append `?nocache=1` to bypass when debugging.
- Persistent state files (`data/writeups_*.json`, `data/*_forecast_freeze.json`) live at `/var/data` in production, `./data` locally. Should NOT be committed to git — that was an accident on commit `0bf2a7e`. TODO: add `data/*.json` to `.gitignore`.

## Visual / brand identity

- Header font: serif (Georgia / Times New Roman)
- Body: system sans
- Accent navy `#1e3a8a` (= `--storm` ish)
- Sport color highlights on homepage cards:
  - MLB: `#1e3a8a` (navy)
  - World Cup: `#15803d` (green)
  - PGA: `#166534` (deeper green)
  - NASCAR: `#b91c1c` (red)
  - CWS: `#ca8a04` (yellow)
  - NFL/NCAAF: `var(--ash)` (neutral, dormant)
  - Tennis: `#7c3aed` (purple)
  - MLS: `#00538f` (blue)
- Favicon: `static/img/favicon.svg` — bolt on transparent background (NO tile), brand navy fill
- Per-sport "cheat-sheet" card: 3-column grid (temp / wind / precip), serif numbers, sans labels
- Homepage sport-card icon size: 40×40, at flex-start alignment to the kicker+title stack (see July 2026 fix)

## Design + UX decisions (locked, July 22-23 2026 sessions)

Kevin's explicit request: **"I don't want any drifting back to where we were after the design fixes we've made across mobile and computer."** Every item below was a deliberate decision. Do not undo any of them without Kevin's explicit sign-off.

### Per-game block layout

- **Odds display goes in the header, top-right, stacked below "First pitch · X"** on the slate per-game block, and left-aligned right under the venue meta on the game detail page. NEVER put a bordered odds box above the hourly forecast — that placement was tried and Kevin rejected it. Macro: `game_odds_inline(game, align)` in `templates/mlb/_macros.html`.
- **Odds display content is 3 items only: O/U current, Opened value, ± delta with arrow.** NO book name, NO status text ("locked at first pitch"), NO reason text of any kind. Kevin's exact words: "Just 3 things."
- **Cheat card top row includes a subtle `O/U X.X`** appended to the existing time+badge line. Class `.cheat-card__total`. Never restructure the cheat card itself — Kevin explicitly noted the card design must not be downgraded, only added to.
- **Per-game header uses `align-items: flex-start`** so first-pitch time + odds sit at the top-right (not center-right).
- **Body grid uses `align-items: stretch`** so the quad summary box's bottom aligns with the hourly's dewpoint row.
- **HRRR sits in body grid row 2, column 2 (desktop)** via `.mlb-game-block__hrrr` class. This prevents the quad box from stretching when HRRR is toggled open (a regression that was fixed). NEVER move HRRR back inside `.mlb-game-block__hourly`.
- **CSS cascade note:** the mobile HRRR override (`grid-column: 1`) MUST be defined AFTER the desktop `.mlb-game-block__hrrr { grid-column: 2 }` rule in style.css. Same specificity → later wins. Do not move the mobile media query up to be with the body mobile override.
- **"Full forecast for this game →" deep-links removed** from all sport slate templates (mlb, nfl, cws, mls, prem). Per-game pages still exist and are in sitemap.xml for SEO discovery. Homepage `_next_game_card.html` still has one editorial link. Do NOT re-add to slate templates unless per-game pages gain unique content.

### Mobile grid pattern

- **Use `minmax(0, 1fr)` on grid columns** and `min-width: 0` on grid items so they can shrink. Without this, wide hourly tables force horizontal page scroll on mobile. `.mlb-game-block__body > * { min-width: 0 }` is the safety net.
- **Matchup headers wrap each team in `<span class="matchup-team">`** so the logo+name stay together when the header wraps on narrow viewports. `.matchup-team { display: inline-flex; white-space: nowrap }`. Never revert to plain inline layout — the header breaks on mobile ("Away Name at [home logo]" splits across lines).

### Homepage

- **Homepage `<title>` is capped at ~57 chars:** `"Free MLB, PGA, NASCAR Weather Forecasts | MySportsWeather"`. Don't expand back to the 68-char version listing every sport — Bing WMT flagged it as too long.
- **All homepage sport-card `<img>` tags have descriptive alt text** ("MLB baseball weather", "PGA Tour golf weather", etc.). Empty `alt=""` was flagged as an SEO error. Don't strip alt text.
- **Wednesday PGA prime slot**: on Wednesdays only, a compact PGA tournament preview card renders BESIDE the hero (two-column via `.home-hero__row`) — same slot the retired World Cup card used. Driven by `is_wednesday_eastern` from `inject_globals` context processor. On other days the hero title spans full width.
- **Sport nav order (left group, then right group with `margin-left: auto` on NFL):** MLB · PGA · NASCAR · (CWS if in window) · (Tennis if in window) · MLS · **[gap]** · NFL · NCAAF. MLS was moved from the right group to the left group at Kevin's request. Don't move MLS back.

### SEO hygiene

- **Schema.org URLs on sport weather hubs point to mysportsweather.com**, never kevinrothwx.com. Sport paths on kevinrothwx.com 301-redirect to mysportsweather.com, so kevinrothwx.com URLs in schema fragment backlink authority.
- **All sport weather hubs have `<link rel="canonical">`** — mlb_weather.html, nfl_weather.html, pga_weather.html. Don't remove.
- **Sport weather hubs cross-link** ("Related weather guides" section) between mlb-weather, nfl-weather, and pga-weather. Builds topical cluster for Google.
- **NFL and PGA weather hubs' CTAs point to `/nfl` and `/golf`** respectively (not to Twitter). Twitter follow is preserved as a SECONDARY button next to the primary slate CTA. Do not remove the Twitter link — 89K follower audience matters.
- **`/worldcup*` URLs return 410 Gone** (via a catch-all Flask route), not 404. Speeds search-engine removal from indexes. Route lives in app.py.

### Infrastructure

- **Disk-backed MLB slate cache at `/var/data/mlb_slate_cache/*.pkl`.** All gunicorn workers share via disk, killing the multi-worker cache-staleness bug. Kill switch: env var `MLB_DISK_CACHE_DISABLED=1`. Never disable this without a specific reason.
- **`ODDS_API_KEY` env var in Render** — fetches MLB totals from The Odds API. Book priority: **DraftKings → FanDuel → BetMGM → Caesars → first available**. Region: `us` only. Never averages across books. Deliberately DIFFERENT from OVERcast (which uses Pinnacle via eu region) — decision made 2026-07-24: Pinnacle isn't US-legal so those numbers are "reference only" for MSW's casual/weather-focused audience; DK matches what MSW users see in their own sportsbook app. Also enables future affiliate hyperlink to DK for click-to-bet. Trade-off accepted: MSW totals may differ from OVERcast by ~0.5 on any given game. See `mlb/odds.py` docstring for full rationale.
- **Opening line snapshots at `/var/data/mlb_odds_openings.json`** — first-seen total per game_pk, immutable. Used to compute the ± delta in odds display. Never re-record.
- **500 errorhandler serves `templates/maintenance.html`** (with 503 status) for any uncaught Flask exception. Don't remove.
- **mysportsweather.com is behind Cloudflare**, apex + www proxied. SSL mode: Full. Route `*mysportsweather.com/*` attached to `mysportsweather-maintenance` Cloudflare Worker (worker code stored at repo root `cloudflare-worker.js`). Worker is meant to intercept 5xx origin responses and serve maintenance page; NOT currently working (under investigation — see `/__cf-test-502` diagnostic endpoint for repeatable testing).
- **kevinrothwx.com is NOT behind Cloudflare** — deliberate choice, Kevin's personal site, low traffic.
- **`/admin/cache-health` diagnostic page** — shows worker PID, MLB disk cache freshness, per-game details, and a "Rebuild MLB slate cache now" button. Auth via basic auth (same as other /admin routes).

## Things NOT to touch

- `app.kevinrothwx.com` and anything in OVERcast — separate Render service, separate codebase.
- MLB forecast freeze when game is already in progress — frozen snapshots are immutable.
- The `_check_admin_auth` flow — env-var-based, simple, works. Don't migrate to OAuth without reason.

## Recurring user instructions (Kevin)

- Brand voice preferences and honesty norms are in his user-preferences. Honor them.
- Brand consistency check ALWAYS catches when auto-generated content drifts into game-outcome speculation.
- Push batching: prefer fewer pushes, more files per push. Each push = ~2 min Render outage during deploy.
- When showing live data, always verify via web_fetch against the actual deployed site — don't infer from local code.
- When unsure between code paths, ask. Honest preference for "do it right" over "do it fast."
- Facts only, source or bail. Kevin has explicitly said mid-session "make sure you are not making anything up" — take that seriously in evergreen content.

---

Last updated: 2026-07-02 during the SEO-landing-page-surge session. Status: 222 evergreen landing pages live across every sport, homepage redesigned to two-column hero with compact WC card, style.css tail truncation recovered, mandatory sweep clean.

Also updated: 2026-07-22 & 2026-07-23 (major sessions). Highlights: MLB odds integration (mirrors OVERcast book priority), disk-backed slate cache eliminating multi-worker staleness, Cloudflare + Worker setup for mysportsweather.com (Worker interception still under investigation), press release distributed via EIN Presswire, 410 handler for retired /worldcup URLs, schema.org URLs fixed to mysportsweather.com on all sport weather hubs, comprehensive design/UX pass on per-game blocks with locked decisions documented in "Design + UX decisions (locked, July 22-23 2026 sessions)" section above — read it before touching any layout.
