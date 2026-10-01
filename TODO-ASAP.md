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

- [ ] **Partner weather API (built and tested 2026-09-30, for ETR).** New,
      separate feed at `/api/partner/v1/nfl/slate` and `/cfb/slate`: weather
      only (no odds, no write-ups), own keys, reads the cache only. Files:
      `partner_api.py` (new), `app.py` (11-line guarded registration),
      `docs/PARTNER_API_v1.md` (send this to ETR). To turn on: Render →
      Environment → add `MSW_PARTNER_KEYS` = `etr:<40+ random letters/numbers>`.
      Send ETR that secret (the part after `etr:`) plus the doc.
      International games included (WeatherAPI data, no gusts).

- [ ] **PGA fix (built 2026-10-01).** ESPN took over Bank of Utah with no course →
      forecast vanished, and the event_id change deleted Kevin's note. Fix fills the
      course from the fallback schedule and keeps a stable event_id. File:
      `golf/schedule.py`. **Push first, then re-add the note.**

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

**Indexing report (Kevin, 2026-09-30):** 404s 52 (finished game pages, fixed by the
redirect above), Discovered-not-indexed 437 (≈ all ~390 evergreen pages + game
pages), Crawled-not-indexed 47, redirect 2, canonical 1. Plan: hide (noindex +
drop from sitemap) every evergreen page with zero impressions in 3 months; keep
any with impressions. Needs: Performance → Pages tab (3 mo, by impressions) and
the example URLs under "Discovered – currently not indexed." Section 1 builds
are low risk and ready to go on Kevin's word.



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

Pitch only PEOPLE WHO WRITE ARTICLES. They already cite AccuWeather or
Weather.com; the ask is to cite a better source. Their win: a quotable
meteorologist, a faster stadium-level source (every game, hourly, one page),
and a Thursday note on which games weather will matter. Lead with the quote
and the note, not the link. Pitch Wed/Thu. Never offer money for a link.

National outlets only (Kevin, 2026-09-30: no team-specific sites).

| # | Outlet | Credits now | Who | Status (2026-09-30) | Next step |
|---|---|---|---|---|---|
| 1 | The Big Lead (weekly NFL weather report) | Weather.com | Second editor said yes; Matt Reed (contact form) | **Yes, unconfirmed** | Confirm credit wording + link to `/nfl`; send Thursday note |
| 2 | Sportsbook Review (weekly NFL Weather Report) | NFLWeather.com | New editor contact; Liam Fox | Reaching out | Pitch the new contact |
| 3 | Sporting News (reprinted on Yahoo) | AccuWeather | Mike Moraitis; Billy Heyen | Pitched | Nudge Oct 6-7 |
| 4 | Sports Illustrated | AccuWeather / nothing | Group email to SI | Pitched | Wait. No team-site follow-ups |
| 5 | The Fantasy Footballers (weekly weather column) | Nothing | DM to a higher-up; Zach Langlois | Pitched | Nudge Oct 6-7 |
| 6 | CBS Sports | Nothing | Writer of last week's weather story (X) | Pitched | Nudge Oct 6-7 |
| 7 | DraftKings Network (weekly "NFL Week N Weather Forecast", also daily MLB weather) | Nothing (AI-written, human-edited) | Site X @DKNetwork; masthead page | Next | Check Underdog exclusivity first. Angle: a named meteorologist makes an unsourced AI piece credible |

**Round 3: national outlets (researched 2026-09-30).** Checked on the page by
Claude. Some pieces are from the 2024 or 2025 season: confirm the writer is
still active before pitching. Winter-only pieces: pitch in November, before the
snow and cold games.

| # | Outlet | Their piece | Credits now | Who / public contact | Notes |
|---|---|---|---|---|---|
| 8 | BettingPros | Weekly "NFL Week N Weather Report & Predictions" (2023-2025) | AccuWeather ("All forecasts courtesy of AccuWeather.com") | Joe Williams. X @WinWithJoe | **Dropped (Kevin, 9/30): nothing recent** |
| 9 | Sports Betting Dime | NFL late-season weather + totals series; weekly CFB weather report | NFL: nothing / The Weather Network. CFB: NWS, timeanddate | Sascha Paruk, Managing Editor. X @SBD_Sascha. CFB: Chris Amberley X @SBD_Chris | **Pitched 9/30 (an SBD contact who follows Kevin); Paruk if no reply.** ~1M visits/mo, owned by Sportradar since late 2024. Paruk also owns their MLB weather page (forecast graphic empty). Pitch editorial (quote + credit), NOT the API. API only as a paid license if they ask |
| 10 | USA TODAY Sports (national desk, runs on Yahoo) | "NFL Week N weather updates" on storm and winter weeks | National Weather Service | Joe Rivera, breaking-news editor. X @JoeRiveraSays (not confirmed on article) | **Pitched (email) 9/30.** Nudge Oct 6-7 |
| 11 | NBC Sports (runs on Yahoo) | Weekly CFB best bets; Week 4 built around the nor'easter | Nothing | Vaughn Dalzell. X @VmoneySports | **Not yet.** CFB angle for `/ncaaf` |
| 12 | Establish The Run | Weekly "The Rundown" | NFLweather.com (competitor) | Staff byline. X @EstablishTheRun | **Pitched 9/30.** Partner API ready if they say yes (see section 0) |
| 13 | The Spun + Athlon Sports + Men's Journal (one owner) | Frequent one-off weather stories, NFL and CFB | Secondhand: NWS, local TV, reporter tweets, NFLweather.com | The Spun: Tzvi Machlin X @TzviLovesSports. Men's Journal: Jonathan Giles X @jgileswrites. Athlon: Ayomide Adeduyite X @ayoadeduyite | **Not yet.** Six writers, one company. Widely syndicated on Yahoo and Yardbarker |
| 14 | VSiN | Nor'easter piece (Sept 24) | Nothing | Adam Burke, Managing Editor. X @VSiNLive | **Not yet.** Also radio/TV: pitch as an on-air guest too |
| 15 | Newsweek Sports | "Weather warning before X game" pieces | The Weather Channel, NWS, or reporter tweets | Sports desk (Andrew McCarty, Jordan Sigler) | Pitch the desk |
| 16 | Fantasy Life | Weekly cheat sheet with a weather section | Weather Underground | Chris Allen. X @chrisallenffwx | He's a fantasy weather analyst, not a meteorologist: pitch as a quote, not a replacement |
| 17 | Yahoo Sports (originals) | Winter weather roundup (Dec 2025); Hayden Winks covers weather in "The Blueprint" | Weather.com (Cwik); Winks not verified | Chris Cwik. X @Chris_Cwik | Pitch in November |
| 18 | Boyd's Bets | Evergreen "NFL weather handicapping" guide | Sends readers to RotoGrinders, RotoWire, Covers | Jimmy Boyd. X @boydsbets | Ask to be added to their resource list. Low effort |
| 19 | EssentiallySports | Templated per-game weather series (2024-25); CFB weather roundups | NFLweather.com; James Spann | Ashutosh Kadam. X @ashutoshk2024 | Check if the series is still running |
| 20 | FanSided (national) | Playoff weather reports | AccuWeather + NWS | Wynston Wilcox | Seasonal: pitch before the playoffs |
| 21 | On3 (national) | College Football Playoff weather pieces | The Weather Channel | Alex Byington. X @_AlexByington | Seasonal: pitch in December |
| 22 | OutKick (Fox) | "NFL weather report" tag, playoff snow games | Fox Weather meteorologist | Mark Harris. Email on author box, X @itismarkharris | Lower odds: Fox has its own meteorologists |
| 23 | FanDuel Research | Weekly "Fantasy Football Weather Report" (2024) | Weather Underground | Jim Sannes. X @JimSannes | Dormant since 2024: offer to help restart it |
| 24 | PlayerProfiler | Weekly "NFL Weather Report" (2024) | Nothing | Matt Babich. X @babich_matt10 | Dormant since 2024 |
| 25 | BetMGM | Per-game weather pages, late season | AccuWeather | House byline. X @BetMGM | Template pages. Check Underdog exclusivity first |

FYI: RotoGrinders hasn't published an NFL weather article since Kevin's own
Conference Championships piece (Jan 23, 2026). Underdog Network has no weather
content.

Follow-ups: one short nudge 5-7 days after the pitch, tied to that week's
weather game, then stop. When a credit runs: check the link goes to `/nfl`,
thank them on X, and watch GA Traffic acquisition → Referral for their domain.

Dropped:
- Automated weather tools that compete with `/nfl` (no win for them):
  RotoWire, Covers, Pro Football Network, Action Network, OddsTrader.
- Fantasy Alarm: has its own weather page.
- Sharp Football Analysis: partnered with a similar weather site.
- Bleacher Report: its Weather.com links carry a BR tracking tag (likely a deal).
- Local TV: own meteorologists.
- Covers editorial weather articles (Covers has its own weather tool).
- College Football Network (same company as Pro Football Network).
- Old or dead: 4for4 (2021), Rotoworld (2019), WagerTalk (2022), Pickswise.
- Team-specific sites (Kevin's call): SI team follow-ups, Rochester Democrat
  and Chronicle, Arrowhead Pride, NorthJersey.com, Giants Wire, Heavy
  (heavy.com; its NFL coverage is organized by team).

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
