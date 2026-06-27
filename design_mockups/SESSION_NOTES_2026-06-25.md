# Session Notes, June 25, 2026

Picking up tomorrow. Read this first.

## What we pushed today (live on the site after deploy)

1. **HRRR paid → free Open-Meteo fallback** (`hrrr.py`)
   - If paid endpoint returns any non-200, automatically retries the free endpoint
   - New log line: `[hrrr] fetched N periods for X,Y via paid endpoint` (or `via free endpoint`)
   - Defense against the recurring stuck-HRRR symptom

2. **Self-healing stale-cache rebuild** (`golf/cache.py`)
   - If the cached PGA slate is older than 30 min, the next request forces a synchronous rebuild
   - Watchdog against warmer-thread-silently-dying failure mode
   - New log line: `[golf.cache] cache is XX.Xmin old (>30min), forcing synchronous rebuild`, appearance of this in Render logs = warmer is stalling
   - Scoped to PGA only per Kevin; mirror to other sports later if needed

3. **Homepage World Cup card text** (`templates/index.html`)
   - Was: "6 matches this week" (misleading, actually counts today only)
   - Now: "6 matches today" with singular ("1 match today") handling

4. **PGA past-round filter** (`app.py`)
   - When a tournament day passes in course-local time, that round's hourly forecast disappears
   - Friday morning → leads with Round 2 (Round 1 dropped)
   - Saturday 12:01 AM → leads with Round 3, etc.
   - Filter runs at request time (not cache build) so cutoff is exact at midnight
   - Manual writeup (Kevin's note) is untouched

## What we built today but did NOT push yet

### Tennis module (`tennis/`, 5 files, 529 lines)

Files: `__init__.py`, `venues.py`, `schedule.py`, `slate.py`, `cache.py`

- 4 hard-coded Slam venues with lat/lon, timezone, roof info
- 2026 Slam date windows hard-coded
- `active_slam()` / `next_slam()` / `is_any_slam_active()` helpers
- WeatherAPI for international venues (AO, RG, Wimbledon), NWS + HRRR for US Open
- Cache with self-healing stale-rebuild (same pattern as golf)
- Warmer idles between Slams to save API calls
- **Not wired into app.py yet**, `start_tennis_warmer()` not being called

**Wimbledon starts June 29 (4 days from now).** If we want the tennis page live by then, the routes + templates need to ship this week.

### CFB design mockup (`design_mockups/cfb_slate_mockup.html`)

Iterated v1 → v6 today. Current state: v6. Open this file to see where we are.

## Strategic decisions made today (lock these in)

### Sport scope and sequencing

| Sport | Status | Target date |
|---|---|---|
| CWS | **REMOVED from homepage** | done |
| Tennis Slams | Module built, routes pending | by Wimbledon (Jun 29) |
| MLS | Not started, full plan agreed | by July 16 (Leagues Cup break ends) |
| CFB | Design in flight, build pending | by Aug 22 (Week 0) |
| NFL | Same architecture as CFB | by Sep 11 (Week 1) |
| College baseball | Long-term ambition | Next spring earliest |

### CFB-specific architecture

- **Build ALL 134 FBS at once** (not phased Power 4 first, Kevin's call)
- **Free site** (this repo): SEO play, auto-generated, no Kevin commentary required (TV job conflicts with CFB Saturdays)
- **Premium product** (separate OVERcast CFB at $99/season): lives in OVERcast repo, NOT this repo. Win probabilities, total adjustments, ATS impact, kicker FG by venue. Must launch by season start, Kevin will personally make sure it's ready.
- **ONE premium CTA placement** on the free site, banner-style, mid-Saturday section, not on every card

### Design rules going forward (apply to all sports)

- **Never mention wet-bulb**, too jargony
- **No em-dashes anywhere on the site**, use commas, periods, or hyphens
- **No AI assumptions about gameplay**, only weather facts ("Snow expected", not "expect run-heavy game")
- **No sort options**, always sorted by kickoff time
- **Drop weather-impact pills**, let color tier do the work (cold = blue temp, hot = red temp, severe wind = red text, etc.)
- **Keep structural badges**, Roof, Dome, Neutral (facts you can't infer from weather data)
- **Keep "Rain to Snow" transition badge**, precip-transition info icon alone can't convey
- **Build wet-bulb-aware precip-type detection as global improvement**, apply retroactively to MLB, PGA, NASCAR, World Cup, CWS, Tennis. Categories: rain / snow / mix / freezing_rain / thunderstorm / none. Detail page can show ambiguity context to user without using the term "wet-bulb."

## CFB mockup design status

### Locked-in patterns, don't revisit unless reason emerges

- Multi-day support with date sections (Thu / Fri / Sat / Sun headers)
- Side-by-side Weather Story + Game of the Day at top of page
- Filter chips: All FBS (default) / Top 25 / Power 4
- Cheat-sheet card grid, `auto-fill, minmax(218px, 1fr)`
- Click anywhere on card → detail page
- Card structure: top rule (time + optional badge), teams row (with rank superscript), conditional venue subtitle, weather row
- Wind shown as small inline arrow + mph paired with the wind number (not on a separate field diagram)
- Football field with wind arrow → detail page ONLY (not on cheat cards)
- HRRR toggle → detail page ONLY (not on slate, saves API calls)
- Neutral site: "vs" instead of "@", venue subtitle line under teams
- Auto-generated meteorologist callout in Weather Story + Game of the Day (just weather facts)

### Still open, pick up here tomorrow

Kevin's most recent reaction: *"Still not there, but we're getting closer."*

**Kevin's end-of-day v7 thoughts (this is the actual direction to head)**

The MLB-pattern match was the wrong call. The cards still feel off because:

1. **Time-of-game header takes too much vertical real estate.** Nearly as much space as the weather info itself. Tighten this dramatically so the weather row gets the breathing room.

2. **The data pairings are spatially wrong.** Gusts pop up but they're far from wind. Feels-like pops up but it's far from temp. Need to ATTACH related metrics:
   - Feels-like attaches to TEMP
   - Gusts attaches to WIND
   - Precip type attaches to PoP

3. **Three metrics deserve equal visual weight, not just TEMP.** Wind is a big number. PoP is a big number. Temp is a big number. The MLB-pattern only makes TEMP big and demotes wind/precip to a small middle column, which is wrong for CFB.

4. **The weather icon "is ugly and feels lower than the temp."** The icon was vertically centered against the multi-line middle column, which puts it visually below the temp's baseline. Need to either align it to the data line or rethink its role entirely.

5. **The spacing is just off.** There's a better way to use the card real estate.

**v7 layout is also the NFL pattern.** Whatever we land on for CFB cards becomes the NFL card pattern too (NFL ships ~Sep 11, same architecture). Worth getting this right since it covers two sports, not one. NFL has way fewer games per slate (max 16/Sunday vs 50+/CFB Saturday) so the layout needs to look good at low density too, not just dense grids.

**Proposed v7 direction (think about this overnight, validate tomorrow)**

Three-column equal-weight stat block instead of MLB-pattern. Each column is a "metric module" with primary number big and secondary data attached underneath:

```
+----------------------------------+
| 12:00 PM ET           [badge]    |  <- TINY rule
| LOGO MICH^6 @ NW LOGO            |  <- teams unchanged
|----------------------------------|
|  32°    25 mph N    [icon] 70%   |  <- big primary numbers (~1.6rem each)
|  Feels  Gusts 45     Snow        |  <- attached secondaries (~0.75rem)
|  19°                             |
+----------------------------------+
```

Three equal columns, each with:
- Big primary number (temp / wind speed / precip%)
- Small secondary attached underneath (feels-like / gusts / precip type)
- Weather icon paired with PoP column (since icon literally IS the precip-type symbol)

Trade-offs to consider:
- Width per column drops from "1fr middle column" to "1/3 of card width" each. May be tight at 218px min card width. Test at minimum size.
- The icon attached to PoP column makes more semantic sense than floating on the right
- Tighter time header should give the wx row enough breathing room

Things to also consider in v7:
- Time-of-game header height: probably needs to shrink to ~24px total (from current ~36px)
- Should we drop the border between top rule and teams? Might save vertical
- Icon size: probably 22-26px (slightly smaller than primary number, paired close to PoP)
- The icons themselves may need revisiting ("ugly" per Kevin), worth A/B-ing a different icon set

### Mockup iteration history (so we don't go in circles)

- **v1**: emoji icons, weather pills, sort dropdown, "Game of the Week" hero (manually picked), too elaborate
- **v2**: real site CSS, weather pills, football field icon on cards, em-dashes, Kevin: "looks cheap vs MLB"
- **v3**: compact above-fold, weather icon moved down, blue backdrop, wet-bulb added, Kevin: top blocks too small, hate wet-bulb
- **v4**: premium feel restored, field/temp swapped, weather condition badges dropped, only structural badges kept
- **v5**: MLB-pattern match, temp left, wind+precip middle, icon right. No football field on cards. No blue backdrop.
- **v5.1**: reserved space for extras line (uniform card heights)
- **v6 (current)**: extras inline with precip ("Snow 70% · Feels 19°"), only short useful extras, verbose ones removed

### Things Kevin liked (preserve in v7+)

- Weather Story auto-callout at top
- Game of the Day side-by-side block
- Real meteorologist-edge content (feels-like, gusts, smart precip type)
- Multi-day date sections

### Things Kevin pushed back on (do NOT bring back)

- Football field on cheat cards (visual weight too much)
- Blue backdrop on sections (unnecessary visual layer)
- Wet-bulb mentions (jargon)
- Em-dashes (style rule for the site)
- AI gameplay assumptions ("expect defensive struggle" etc.)
- Sort dropdown (always by time)
- Weather-condition badges (Snow / Rain / Heat / Wind), too noisy
- Two-row card layout with floating icon in top-right corner
- Three-line middle column (broke MLB visual balance)
- MLB-pattern match for CFB (only makes TEMP big, demotes wind/precip too much)

## Operational reminders

### Files to push (queue for GitHub Desktop when Kevin's ready)

- `tennis/__init__.py` (new)
- `tennis/venues.py` (new)
- `tennis/schedule.py` (new)
- `tennis/slate.py` (new)
- `tennis/cache.py` (new)
- `design_mockups/cfb_slate_mockup.html` (mockup only, not production code, but useful to keep in repo for reference)
- `design_mockups/SESSION_NOTES_2026-06-25.md` (this file)

Note: the tennis module is inert until wired into app.py. Pushing it doesn't change the live site.

### Open task list (pending, in rough priority order)

- #110 Tennis routes + templates (urgent if we want Wimbledon coverage)
- #111 Replace CWS card with Tennis on homepage
- #105 Build MLS module (July 16 target)
- #106 MLS routes + templates
- #107 Swap MLS into homepage card
- CFB design lock-in + build (~7-9 sessions, target Aug 22)
- NFL build (2-3 sessions after CFB foundation, target Sep 11)
- #79 WeatherAPI fallback for MLB / NASCAR / CWS
- #81 World Cup hourly freeze at kickoff
- #72 OVERcast screenshots on /overcast
- #85 Pull at-first-pitch from OVERcast directly
- #97 Schema.org markup for CWS + NASCAR detail pages
- #94 MLB stadium landing pages
- #91 Redis migration (only matters when scaling to multi-worker)
- #31 PGA course maps Phase 2

## Where to start tomorrow


## Where to start tomorrow

1. **Open** `design_mockups/cfb_slate_mockup.html` and look at v6 fresh
2. **Build v7** with the three-column stat-block layout per Kevin's notes above
3. **Iterate** until Kevin says "that's it"
4. **Then** decide: ship Tennis routes/templates this week for Wimbledon? Or jump to MLS build for July 16?

The CFB design needs to lock down before we touch real CFB code, but it doesn't block Tennis or MLS work, those can proceed in parallel.
