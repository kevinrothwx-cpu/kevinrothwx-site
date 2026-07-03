"""horse/ — US thoroughbred stakes-day weather forecasts.

Scope is hand-curated: we cover marquee Grade 1 / Grade 2 stakes days
at the major US tracks. Not a live per-race feed — thoroughbred racing
doesn't have a clean live scoreboard API the way ESPN does for MLB/NFL.

Structure mirrors the other sport modules (mls/, cfb/, nfl/):
    venues.py           — track lat/lon/timezone/turf info
    schedule.py         — hand-curated marquee stakes calendar
    slate.py            — WeatherAPI primary + HRRR toggle
    cache.py            — 25-min warmer + self-healing stale rebuild
    forecast_freeze.py  — race-day snapshot (post-race review)

WeatherAPI is primary here (rather than NWS) because Kevin wants the
forecast delivered by post-time, and NWS 12h grids don't line up well
with mid-afternoon stakes races the way WeatherAPI's clean hourly does.
NWS is still available as a manual fallback if WeatherAPI misfires.
"""
