# Mobile pass — 2026-09-02 — change log and revert guide

Snapshot taken so any of this can be backed out individually without
unpicking the rest. Every item below is independent; reverting one does not
require reverting another.

**Scope rule for this pass:** visual changes are mobile-only, inside
`@media (max-width: 600px)`. Two items deliberately go wider and are
flagged as such.

Measurements were taken on the live site at a real 375×812 viewport before
changing anything, so the "before" column is observed, not estimated.

---

## 1. Sport nav — core four now fit

**Problem.** `.sport-nav__inner` measured **747px wide in a 375px
viewport**. It has `overflow-x: auto` so it scrolled, but with no fade or
scrollbar, so on a phone only MLB / NFL / PGA / NCAAF were reachable and
NASCAR / MLS / Tennis were invisible rather than merely off-screen.

**Decision.** Kevin: the core four matter more than the tail, so do NOT
shrink them to make room. All sports kept — the mobile menu does not list
MLS or Tennis, so hiding them here would make those sections unreachable on
a phone entirely.

| | Before | After |
|---|---|---|
| `.sport-nav__inner` padding | `0 1.5rem` | `0 0.85rem` |
| `.sport-nav__item` padding | `1rem 1.25rem` | `0.85rem 0.62rem` |
| `.sport-nav__item` font | `0.85rem` | `0.8rem` |
| `.sport-nav__count` font | `0.7rem` | `0.64rem` |
| right-edge fade | none | `mask-image` linear-gradient |

Core four now measure ~179px of a 360px viewport, so they clear even a
small phone with room to spare.

**File:** `static/css/style.css`, block titled
`Mobile sport-nav: guarantee the core four fit`
**Revert:** delete that block.

---

## 2. CFB slate card type sizes

**Problem.** Two cards per row at 375px gives each card ~184px, which had
forced the type down to unreadable sizes. Kickoff time is primary
information and was the worst offender.

| Element | Before | After |
|---|---|---|
| `.cheat-card__time` (kickoff) | **9.6px** | `0.76rem` (~12.2px) |
| `.cheat-card__location` (venue) | **8.96px** | `0.7rem` (~11.2px) |
| `.wx-stat__secondary` (wind/precip) | **9.92px** | `0.8rem` (~12.8px) |
| `.cheat-card__odds-total` | 10.88px | `0.86rem` |
| `.cheat-card__odds` | — | `0.76rem` |
| `.cheat-card__badge` | — | `0.62rem` |
| `.cheat-card--cfb` padding | `0.7rem 0.85rem 0.8rem` | `0.6rem 0.7rem 0.7rem` |

Padding was trimmed to buy back the height the larger type costs, so rows
did not get taller overall. 2-up layout was KEPT per Kevin.

**File:** `static/css/style.css`, block `Mobile: CFB card type sizes`
**Revert:** delete that block.

---

## 3. Hourly table now fits without scrolling

**Problem.** `.hourly` had 327px available at 375px but 353px of content,
so the last column clipped and you had to scroll a table you could almost
see all of.

**Arithmetic.** The label column (`WIND DIR`, nowrap) took ~70px and each
hour column had `min-width: 56px`. Six hour columns = 406px.

| | Before | After |
|---|---|---|
| `.hourly__table` font | `0.85rem` | `0.78rem` |
| label col font / padding | `0.7rem` / `0.45rem 0.85rem` | `0.62rem` / `0.4rem 0.45rem` |
| `.hourly__hour-col` min-width | `56px` | `42px` |
| `.hourly__hour-col` padding | `0.5rem 0.5rem 0.4rem` | `0.45rem 0.18rem 0.35rem` |
| `.hourly__cell` padding | `0.4rem 0.5rem` | `0.36rem 0.18rem` |
| sky icon | 32px | 24px |

Result: 4 cols → 220px, 5 → 262px, **6 → 304px (fits)**, 7 → 346px
(scrolls), 8 → 388px (scrolls).

`overflow-x: auto` was deliberately KEPT. Seven or more columns cannot fit
at any reasonable width, so longer windows still scroll rather than clip.
Kevin's instruction was "no scroll if it can be done stylishly" — this
removes it for the common case and degrades gracefully past that.

**File:** `static/css/style.css`, block
`Mobile: fit the hourly table without a scrollbar`
**Revert:** delete that block. Scroll returns for 5+ columns.

---

## 4. Venue link block removed from the CFB slate

**NOT mobile-only — removed at all widths, per Kevin's explicit request.**

**Problem.** 134 links at 12.5px font / ~15px row height. Bad tap targets
and a very long scroll on a phone.

**Decision.** Kevin: "I'd rather just have the pages in case someone
googles it, but not show those pages on the CFB page at all."

The **pages are unaffected** — still live, still in `sitemap.xml`, still
pushed via IndexNow. Only the on-page link block is gone.

**Risk being accepted.** Those pages were orphans before today (nothing
linked to them), which is the likely reason Search Console showed 45
indexed against ~500 live. Removing the links restores that orphan status
for CFB stadiums specifically. **If they stall in "Discovered — currently
not indexed", the fix is a small curated set of links (a handful of notable
venues), not dumping all 134 back onto the slate.**

**File:** `templates/ncaaf/slate.html` — a comment block sits where the
include used to be.
**Revert:** replace that comment with:
```jinja
{% set landing_sport = "ncaaf" %}
{% include "_landing_index.html" with context %}
```
The block and `landing_index.py` are both still present and still used by
MLB, NFL, PGA, NASCAR, MLS, Prem and IPL slates.

---

## 5. Footer height

**Problem.** 579px tall at 375px — nearly a full screen of chrome under
every page. The height came from desktop spacing that mobile inherited:
the three-column layout does not even apply below 640px.

| | Before | After |
|---|---|---|
| `.site-footer` margin-top | `6rem` | `2.5rem` |
| `.site-footer__inner` padding | `3rem 1.5rem 2rem` | `1.6rem 1.25rem 1.1rem` |
| `.site-footer__inner` gap | `2rem` | `1.15rem` |
| `.site-footer__inner` font | `0.9rem` | `0.86rem` |
| `h4` margin-bottom | `0.75rem` | `0.45rem` |
| `li` margin-bottom | `0.4rem` | **`0.5rem` (increased)** |
| `.site-footer__copy` padding | `1rem 1.5rem` | `0.8rem 1.25rem` |

`li` spacing was deliberately **increased** — those are tap targets and
were too tight to hit reliably.

**File:** `static/css/style.css`, block `Mobile: shorter footer`
**Revert:** delete that block.

---

## 6. CFB Saturday grid shift

**NOT mobile-only — the base rule changed too. Kevin approved.**

**Problem.** Saturday's card rows sat wider and off-centre versus every
other day. Measured: every other day computed
`grid-template-columns: 190.8px 190.8px`; **Saturday computed
`209.012px 202.663px`** — unequal, and wider.

**Cause.** A bare `1fr` will not shrink a column below its content's
min-content width. The two widest Saturday cards are the **dome games** —
`UT R @ UTSA` at 209px min-content and `NEW @ SYR` at 203px, matching
Saturday's two column widths exactly. A dome card packs kickoff time + a
`DOME` badge + the city on one `white-space: nowrap` line. Saturday is the
only day on the slate with a dome game, which is why only Saturday shifted.

| | Before | After |
|---|---|---|
| base `.cheat-row` | `repeat(auto-fill, minmax(220px, 1fr))` | unchanged, plus `.cheat-row > * { min-width: 0; }` |
| mobile override | `1fr 1fr !important` | `minmax(0, 1fr) minmax(0, 1fr) !important` |

Desktop was included because the same bug exists there, just diluted
across more columns so it is less visible.

**File:** `templates/ncaaf/slate.html` (inline `<style>` block)
**Revert:** restore `1fr 1fr !important` in the mobile override and delete
the `.cheat-row > * { min-width: 0; }` line.

---

## 7. Game detail page header — mobile redesign

**Mobile only.** Desktop keeps the existing kicker / big title / meta line,
which Kevin is happy with.

**Problem.** On phones the meta line ran venue + city + kickoff + roof
together as one sentence, header height jumped depending on whether team
names wrapped to two lines or one, and the logos got shoved around when
they did.

**Layout chosen** (option 1 of 3 mocked, with Kevin's modifications): one
team per line, logo locked to its own team name, a stylised `@` after the
away team on that same line, then kickoff / total / venue as a labelled
three-cell row.

**Structural change (affects desktop markup, not desktop appearance).**
Each team is now wrapped in `.matchup-team`, which MLB already did but NFL
and CFB did not. That wrapper is `display: inline-flex; white-space:
nowrap`, so a logo can never be orphaned onto a different line from its own
team name. The `at`/`@` moved INSIDE the away team's wrapper so it stays on
that line when mobile stacks. Desktop renders identically — it is all
inline-flex in one wrapping row either way.

| | Before | After (mobile) |
|---|---|---|
| `.game-page__title` | `clamp(1.85rem, 3.5vw + 0.5rem, 3rem)`, row, wrap | `1.32rem`, column, one team per line |
| separator | text `at` | `@`, serif, `1.15em`, muted |
| `.matchup-logo` | `1.4em` | `1.25em` |
| meta line | venue + city + kickoff + roof, one sentence | venue + city only |
| kickoff / total / venue | inside the meta sentence | labelled 3-cell row |

**Team names now SHRINK rather than wrap** on mobile (1.32rem is below the
desktop clamp floor of 1.85rem). That is what removes the ragged two-line
headers, but it means a very long pairing gets small rather than wrapping.
Worth checking on a real phone.

**Side effect worth knowing:** totals now render on NFL and CFB **detail**
pages for the first time. `game.odds` was already in that context (the NFL
route does `out = dict(g)`, so it survives the wc-shape aliasing) but was
never displayed. Slate cards already showed totals; detail pages did not.
Shows a real number when a book posted one, `—` otherwise, so the cell
holds its place instead of the row reflowing between two and three cells.

**Files:**
- `templates/_game_facts.html` (new — shared, data-driven fact row)
- `templates/mlb/game.html`, `templates/nfl/game.html`,
  `templates/ncaaf/game.html` (team wrappers, split meta, `gp_facts`)
- `static/css/style.css`, block `Game-page header: mobile layout`

**Revert:** delete the CSS block (that alone restores the old mobile
header, since `.matchup-at__sym` and `.gp-facts` are `display: none` by
default outside the media query). To fully back out, also remove the
`gp_facts` / `_game_facts.html` include from the three templates and
unsplit the meta spans.

---

## 8. "Example" stamp on the OVERcast promo

**Mobile only.**

**Problem.** The caption under the screenshot is easy to scroll past on a
phone, and the numbers in the shot are real, so a reader could reasonably
take them for today's game.

**Rejected:** a diagonal semi-transparent watermark across the image. It
would be ugly and would obscure the numbers that make the screenshot worth
showing in the first place.

**Chosen:** a small dark pill reading `EXAMPLE` pinned to the top-left of
the screenshot, via `.oc-tease__shot::after`. The caption underneath is
KEPT — belt and braces, not a replacement.

**File:** `static/css/style.css`, block
`Mobile: "Example" stamp on the OVERcast screenshot`
**Revert:** delete that block. The caption remains either way.

---

## 9. CFB hourly highlighted 4 hours instead of 3

**NOT mobile-only — this is a server-side data bug, not styling.**

**Cause.** NFL correctly separates two constants:
`HOURS_GAME_WINDOW = 4` (how much forecast to show) and
`HOURS_HIGHLIGHTED = 3` (how many hours get shaded). CFB had only
`HOURS_GAME_WINDOW` and used it for **both**, so it shaded four hours.
MLB uses `HOURS_GAME = 3` and was already correct.

**Fix.** Added `HOURS_HIGHLIGHTED = 3` to `cfb/slate.py` and pointed
`is_game_hour` at it.

Verified: kickoff, +1h, +2h shaded; −1h, +3h, +4h not.

**File:** `cfb/slate.py` (~line 44 and the `is_game_hour` assignment)
**Revert:** point `is_game_hour` back at `HOURS_GAME_WINDOW`.

---

## Files touched in this pass

```
cfb/slate.py                      #9
templates/_game_facts.html        #7  (new file)
templates/mlb/game.html           #7
templates/nfl/game.html           #7
templates/ncaaf/game.html         #7
templates/ncaaf/slate.html        #4, #6
static/css/style.css              #1, #2, #3, #5, #7, #8
```

`static/css/style.css` after this pass: **1676 lines, 97,538 bytes, 14
`@media (max-width: 600px)` blocks.** If a future session finds fewer lines
than that with these block titles missing, suspect the OneDrive truncation
problem described in `CLAUDE.md` rather than an intentional revert.

## Not changed, despite appearances

- NFL and MLB **slate** preview cards. Only CFB slate cards got type
  changes (#2).
- Desktop game detail headers.
- Any forecast logic, freeze logic, or odds capture.
- The venue landing pages themselves (only the link block on the CFB slate
  was removed).

## Investigated and dismissed

A mid-scroll screenshot of a CFB game page came back almost entirely blank
and looked like a large empty region. Content distribution was measured
across the full document height in viewport-sized bands and is even
throughout — it was a screenshot capture artifact, not a layout bug. Do not
chase it.
