"""mls/ — Major League Soccer weather forecasts.

29-team coverage for the 2026 season (San Diego FC joined 2025 as the
30th franchise but plays at the same site as the others). Three Canadian
venues (Toronto, Montreal, Vancouver) flag nws_unsupported and route
through WeatherAPI directly.

Module structure mirrors cfb/ exactly:
    venues.py         — stadium lat/lon/timezone/roof data
    schedule.py       — ESPN scoreboard fetcher + parser
    slate.py          — weather attachment, NWS primary + WeatherAPI fallback
    cache.py          — 25-min warmer + self-healing stale rebuild + cleanup
    forecast_freeze.py — per-match snapshot at kickoff
    storage.py        — writeups, disk-backed
    analysis.py       — rule-based pure-weather summary (no soccer-impact)
"""
