"""nfl/ — National Football League weather forecasts.

32-team coverage. Mirrors cfb/ pattern for data layer and ncaaf/
templates for visual treatment. Per Kevin's design call: NCAAF
cheat-card design (since it's already approved), MLB-style overall
page layout (similar team count, similar slate density).

Module structure:
    venues.py          — 32 stadiums with roof types
    schedule.py        — ESPN football/nfl scoreboard fetcher
    storage.py         — color-tagged writeups + delete_orphaned
    forecast_freeze.py — kickoff snapshot lock
    analysis.py        — pure weather facts (no football-impact)
    slate.py           — NWS primary + WeatherAPI fallback
    cache.py           — 25-min warmer + 30-min stale self-heal + freeze

Domes (no toggle, no forecast — game played indoors):
    NO (Caesars Superdome), DET (Ford Field),
    MIN (US Bank Stadium), LV (Allegiant Stadium)

Retractable (toggle Closed/Open, defaults Closed like MLB):
    ARI, ATL, DAL, HOU, IND

Fixed-canopy (open sides, weather still matters):
    LAR + LAC (SoFi Stadium — shared)
"""
