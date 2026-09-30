# MySportsWeather — things to do ASAP

Last updated: 2026-09-30

**SEO is the #1 priority.** Google takes roughly 4-8 weeks to reflect changes,
and the most valuable weather traffic of the year is December and January
(snow games, cold playoffs, wind). Anything live by **mid-October** ranks in
time for that. Anything done in December ranks for the offseason.

The order: fix what Google can't see → tune what it already shows → build links.

---

## 0. Push right away

- [ ] **Calm-wind fix (7 files, built and tested 2026-09-28, not yet pushed).**
      Fills hours NWS rounds to "0 mph" with the real light wind, e.g. Rutgers
      "0 mph N" → "1 mph NNE". Files: `wind_gusts.py`, `mlb/nws.py`,
      `mlb/slate.py`, `cfb/nws_client.py`, `cfb/slate.py`, `nfl/slate.py`,
      `nascar/slate.py`.

- [ ] **Opening-line fix (4 files, built and tested 2026-09-30).** Openers
      were replaced ~24h before kickoff, so on game day OVERcast's "opener"
      was within a point of the current line. Push before Saturday morning
      to save Week 4 (tonight also saves Thursday's). Files:
      `nfl/odds_storage.py`, `cfb/odds_storage.py`, `nfl/slate.py`, `cfb/slate.py`.
      After it's live, OVERcast can go back to showing openers.

## 1. SEO — Claude builds (approved 2026-09-24, not yet built)

About a day of work, low risk.

- [ ] Drop "| Kevin Roth" from game page titles; lead with how people search
      ("Ravens vs Cowboys Weather: Rio Forecast, Sep 27").
- [ ] Remove the misleading "free, in stock" `Offer` from game-page schema
      (keep the `SportsEvent`).
- [ ] Add `max-image-preview:large` so Google Discover can show large images.
- [ ] Add a small **"Link to this game"** at the bottom of each NFL game block.
      Gives Google a path to all 16 orphaned game pages without changing how
      the page scrolls. (Kevin: no card clicks to game pages — intentional.)
- [ ] Redirect finished game pages to `/nfl` instead of letting them 404.
      (Not "archived" pages — avoids piling up ~1,000 dead pages a season.)

## 2. SEO — Kevin: data that decides what's next

- [ ] **Search Console → Performance → Queries**, last 3 months, sorted by
      Impressions, with **Average position** turned on. Screenshot.
      → Shows which searches we're sitting at positions ~5-15 on.
- [ ] **Search Console → Indexing → Pages → "Why pages aren't indexed."** Screenshot.
      → "Discovered, not indexed" = linking problem. "Crawled, not indexed" = quality problem.
- [ ] **Request Indexing** for `/nfl`, `/ncaaf`, `/mlb` (URL Inspection bar →
      paste URL → Request Indexing). Daily limit ~10, so only the hubs.

## 3. SEO — after the screenshots

- [ ] Tune titles and on-page copy for the "striking distance" queries (positions ~5-15).
      Baseline: 225K impressions, avg position 7.2, 2.1% CTR (28 days to 2026-09-28).
- [ ] **Live team pages**, NFL (32) first, then CFB (138, don't exist yet): each
      shows the upcoming game's forecast, with a big "See every game's forecast →"
      link to the main sport page at the top. `/nfl` stays the flagship; team
      pages are the front door for people searching "Bills weather."
- [ ] Decide the ~460 evergreen venue/team pages: if Google is ignoring them,
      hide them all in one change (no cherry-picking among equally thin pages).
- [ ] Optional: a share image for `/nfl` (e.g. "This week: 3 games with 20+ mph winds").

## 4. SEO — backlinks (Kevin, ongoing)

- [ ] Every podcast, radio or TV appearance: ask for a link to
      `mysportsweather.com/nfl` in the show notes or on the station's site.
- [ ] One genuine data piece, written by Kevin (no AI in his voice): e.g. how
      wind actually moves NFL totals, using OVERcast's historical data.
- [ ] Link X posts to `/nfl`, not the homepage.
- Note: partner links (Underdog etc.) carry `rel="sponsored"` — no ranking credit.

### Source-replacement outreach (researched 2026-09-30)

Outlets already publishing NFL weather and crediting someone else. Ask: use
MSW, credit + link it. Offer a meteorologist quote on big weather games. Pitch
Wed/Thu, before their Fri/Sat weather piece. Never offer money for a link.

Ranked best first. Ranking: weekly piece > one-off, credits a big brand or
nothing > credits a specialist, reachable writer > contact form.

| # | Sent | Outlet | Their piece | Credits now | Writer / public contact |
|---|---|---|---|---|---|
| 1 | [ ] | Sportsbook Review | Weekly "NFL Weather Report Week N" | NFLWeather.com (competitor) | Liam Fox, Publishing Editor. sportsbookreview.com/writers/liamfox, site contact page |
| 2 | [ ] | The Big Lead | Weekly "NFL weather report Week N" | Weather.com | Matt Reed. Contact form only. **Warm:** TBL quoted Kevin (as RotoGrinders) Dec 27, 2025, Bills-Eagles |
| 3 | [ ] | Sporting News (reprinted on Yahoo) | NFL weather roundups | AccuWeather | Mike Moraitis; also Billy Heyen. Moraitis writes for Bears On SI too |
| 4 | [ ] | Fantasy Alarm | Weekly "NFL Week N Weather Report" | Nothing | Jon Impemba, content manager. X @jimpemba777 |
| 5 | [ ] | The Fantasy Footballers | Weekly "Weather Conditions" (since 2025) | Nothing | Zach Langlois. Site contact page |
| 6 | [ ] | Packers On SI | Lambeau weather stories | AccuWeather | Bill Huber, publisher. Email + X @BillHuberNFL in his bio |
| 7 | [ ] | Sharp Football Analysis | Daily "NFL Weather Today" page | weatherqb.com + weather.football | Staff. Contact page |
| 8 | [ ] | Broncos On SI | Game weather stories | Nothing / Denver7 | Chad Jensen, publisher. X @ChadNJensen |
| 9 | [ ] | Cowboys On SI | Road/neutral game weather (Rio) | AccuWeather | Josh Sanchez, Managing Editor. Email on author box, X @jnsanchez |
| 10 | [ ] | CBS Sports | Weekly + playoff NFL weather | Nothing | Chinmay Vaidya |
| 11 | [ ] | RotoWire | Live NFL weather tool | Forecast.io (dead since 2023) + weather.com | Editorial team. Contact page |
| 12 | [ ] | Rochester Democrat and Chronicle (reprinted on Yahoo) | Every Bills game | NWS + AccuWeather | Steve Howe, weather reporter; also Kerria Weaver |
| 13 | [ ] | Arrowhead Pride (SB Nation) | Weekly how-to-watch, weather line | Nothing | Ron Kopp Jr. Site X @arrowheadpride |
| 14 | [ ] | Bears On SI | Soldier Field weather | Nothing | Andrew Hughes. X @ARJHughes |
| 15 | [ ] | Heavy (team pages) | Quick weather posts | AccuWeather / nothing | Pitch the NFL editor once to cover all team pages |
| 16 | [ ] | Seahawks On SI | Game weather | AccuWeather | Richie Whitt. X @richiewhitt |
| 17 | [ ] | NorthJersey.com (reprinted on Yahoo) | Giants/Jets storm games | Weather.com | Dave Rivera |
| 18 | [ ] | Giants Wire (USA Today) | Storm games | AccuWeather | Dan Benton |
| 19 | [ ] | Chargers On SI | Weekly game info (road games only) | Nothing | Brennan Isham |
| 20 | [ ] | DraftKings Network | AI-written weekly forecast | Nothing | Site X @DKNetwork. Check against any Underdog exclusivity first |
| 21 | [ ] | Pro Football Network | Weekly weather report | Own tool | Jason Katz. X @jasonkatz13. Low odds |
| 22 | [ ] | Covers | NFL weather tool | Visual Crossing (paid data) | Product team. Only fits an API deal |

Skip: Bleacher Report (its weather.com links carry a BR tracking tag, likely a
deal), local TV (own meteorologists), OddsTrader / Action Network (in-house tools).

---

## Other open items

**Underdog / partnership**
- [ ] Pull for the pitch (GA, Sept 14-28): Traffic acquisition table (how much is
      Cross-network), `outbound_click` count, US states (share in CA/TX/FL).
- [ ] If a deal signs: `rel="sponsored"` on partner links + a visible "Partner"
      label, built before launch. Use only the partner's exact offer copy
      (Underdog's is a 50% deposit match up to $1,000, $10 min — not "$1,000 for $5").

**Data quality**
- [ ] Investigate the Cross-network traffic (11K sessions on 2026-09-20, no ads
      running). Possible bots — affects pitch numbers and ad-network eligibility.
- [ ] Star `outbound_click` as a key event in GA (Admin → Events).

**Site**
- [ ] `/overcast` page: CFB section (Kevin asked to be reminded).
- [ ] NFL stadium bearing audit for the other 31 stadiums + capacity tripwire.
- [ ] Feels-like temps (heat index, wind chill).
- [ ] MLS nav badge counts today's games, not this week's.
- [ ] Optional: why the MLB warmer stalled on 2026-09-26 (self-heal now covers it;
      `/admin/cache-health` shows slate age).

**Capacity — revisit only if one of these trips**
- Peak CPU regularly above ~60%, memory above ~80%, or p90 response time above
  ~200ms during a peak → then build page caching or upgrade the Render instance.
  (Sept 20 record day: CPU ~20%, memory ~60%, p90 ~20ms.)
