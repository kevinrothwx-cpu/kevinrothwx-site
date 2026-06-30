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

## Strategic direction

- **mysportsweather.com is an SEO funnel into OVERcast.** Direct monetization of the site is not the focus. SEO traffic that converts to OVERcast users is.
- **AI discoverability is co-equal with traditional SEO.** AI Overview / ChatGPT search / Perplexity / Claude all extract structured facts. Every detail page gets schema.org SportsEvent + additionalProperty.
- **International expansion is parked, not killed.** US validation comes first. Revisit Q1 2027 with 6+ months of Search Console data. Suggested order when we do: DP World Tour → Premier League → cricket → F1. Cricket is the biggest single unclaimed global opportunity (no dedicated meteorologist competitor; Metcheck is the only player and they're a 1999-built site).
- **Sport priority queue:** Tennis (done, Wimbledon live) → CFB (built, Aug 29 launch) → NFL (coming-soon only, Sept 10) → MLS (July 16, NEXT TO BUILD).
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
templates/sport/
  slate.html         # the hub page
  game.html          # per-event detail page with schema.org
```

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
- **schema.org** — every game/match detail page has `SportsEvent` + `additionalProperty` for weather metrics

## Sport-by-sport state

| Sport | Live? | Source | Patterns active | Notes |
|---|---|---|---|---|
| MLB | yes | NWS + Open-Meteo (Toronto) | freeze (first-pitch), writeups, wind-vs-CF | task #79 pending: add WeatherAPI fallback layer |
| World Cup | yes (2026) | WeatherAPI (international) | writeups | task #81 pending: freeze at kickoff |
| PGA | yes | NWS + WeatherAPI fallback + HRRR | freeze (per round), writeups, auto-advance, orphan cleanup | round-based composite freeze key |
| NASCAR | yes | NWS + WeatherAPI fallback + HRRR | freeze (green flag), writeups, auto-advance, self-heal, orphan cleanup | distinct UA for OVERcast IP differentiation pattern not applied here yet |
| CWS | recurring (Jun 13-23) | NWS | freeze, writeups | post-season specific |
| CFB | built, launches Aug 29 | NWS primary via `cfb/nws_client` + WeatherAPI fallback + HRRR | freeze, schema.org, analysis paragraph, per-game detail page | distinct UA "kevinrothwx-site/1.0 ncaaf", pacing, circuit breaker |
| NFL | coming-soon only, launches Sept 10 | n/a | n/a | only the coming-soon page exists |
| Tennis | yes (Wimbledon live) | WeatherAPI (international) | per-day detail pages, ESPN match schedule, analysis paragraph | ATP/WTA endpoints return overlapping events — dedup by competition.id |
| MLS | NOT BUILT, returns July 16 | TBD | TBD | NEXT TO BUILD |

## Outstanding pending items (future sessions)

In rough priority order:

1. **MLS module** (#105/106/107) — July 16 deadline
2. **WeatherAPI fallback for MLB/NASCAR/CWS** (#79) — resilience, ~45min
3. **World Cup freeze at kickoff** (#81) — apply existing pattern, ~30min
4. **G5 venues completion in cfb/venues.py** (#143) — not blocking
5. **Schema.org on CWS + NASCAR detail pages** (#97) — SEO win
6. **MLB stadium landing pages** (#94) — `/mlb/stadium/<slug>` SEO win
7. **OVERcast product screenshots on /overcast** (#72) — landing-page polish
8. **Pull at-first-pitch values from OVERcast directly** (#85) — match the canonical source
9. **Redis migration** (#91) — only when scaling beyond single Gunicorn worker
10. **Phase 2 PGA course maps** (#31) — original ambition, not blocking

## OneDrive truncation playbook (CRITICAL)

This has dominated recent sessions. CLAUDE.md has the rules; this is the playbook.

**Symptom**: Edit/Write tool says success, AST/Jinja parse reports broken at a high line number near the end of the file, tail shows a partial line.

**Recovery sequence**:
1. `head -N file > /tmp/...` where N is the last known-good line
2. `cat /tmp/... > file` to truncate
3. `cat >> file <<'EOF'` to append the rest via heredoc (bypasses Edit-tool race)
4. `sleep 5` (let OneDrive sync settle)
5. AST/Jinja parse to confirm

**Mandatory verification after ANY batch of code edits**:
- Full Python AST sweep across the repo
- Full Jinja template sweep
- Tail integrity (every touched file ends with expected closing statement)
- Behavioral test: boot Flask test_client and hit affected routes
- For pre-push: `git show HEAD:file | python3 -c "ast.parse(...)"` — this is what caught the storage.py corruption that broke the Render deploy on commit `0bf2a7e`

**What we learned the hard way**:
- Local Read tool reads from OneDrive cloud (often clean) while bash reads from disk (often truncated). The two views can diverge by several lines.
- GitHub Desktop reads from disk. So when Kevin pushes, he can push the truncated version even when Read tool showed it clean to us.
- Sometimes the on-disk file has duplicate lines from heredoc append after an earlier failed write (the `if removed: _persist() return removed` showing up twice was the storage.py break).
- Do NOT run `git` from bash on this repo. It leaves `.git/index.lock` files that block Kevin's GitHub Desktop commits. CLAUDE.md explicitly says this. Honor it.

## Deploy flow

- Kevin pushes via GitHub Desktop on Windows.
- Render auto-deploys on git push to main.
- Render service: `kevinrothwx-site`, Python 3, Starter tier ($7/mo), 1 GB persistent disk at `/var/data`.
- Procfile: `web: gunicorn -w 1 app:app` (single worker — task #90 fixed multi-worker cache divergence).
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
- Favicon: `static/img/favicon.svg` — bolt on transparent background (NO tile), brand navy fill
- Per-sport "cheat-sheet" card: 3-column grid (temp / wind / precip), serif numbers, sans labels

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

---

Last updated: 2026-06-29 during the tennis-launch / NASCAR-PGA-fix / Tier 1+2+3 session. Status: tennis polish v3 verified clean, MLS module about to begin.
