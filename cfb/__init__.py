"""cfb (NCAAF) Weather Module

Free site coverage for all 134 FBS games. Pattern matches CWS/golf/tennis:
- venues.py: 134 team→stadium lookup (lat/lon, tz, conf, color)
- schedule.py: ESPN scoreboard fetcher with multi-day window + rankings
- slate.py: build the slate, attach weather to each game
- cache.py: in-process cache + warmer thread with self-healing

Premium product (OVERcast CFB) lives in a separate repo; this module
serves the FREE site at mysportsweather.com/ncaaf only.

Architectural notes (per design lockdown in v14 mockup):
- Multi-day support (Thu/Fri/Sat/Sun) with date-section grouping
- Three-column stat card: TEMP / WIND / POP with attached secondaries
- Phosphor Regular weather icons via Iconify CDN
- Football field with rotated wind arrow on every card
- Location (city, ST) top-right on every card
- No precip labels (false-confidence problem at PoP thresholds)
- Auto-generated meteorologist headlines at top (just weather facts)
- Click anywhere on a card → per-game detail page with hourly + HRRR
"""
