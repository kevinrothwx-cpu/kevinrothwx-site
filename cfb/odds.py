"""
cfb.odds — The Odds API client for CFB game totals (O/U).

Mirrors mlb/odds.py exactly, adapted for college football. See that module
for the full rationale on book choice, region, and credit budget. Summary:

    - Source: api.the-odds-api.com, sport `americanfootball_ncaaf`
    - Market: `totals` only (never spreads, never moneylines)
    - Region: `us` (US-licensed books only)
    - Book priority: DraftKings → FanDuel → BetMGM → Caesars → first
      available. NEVER averages across books.
    - Timing: pulls current pre-game line at fetch time. Once a game
      starts, the line freezes (handled in cfb/slate.py via forecast_freeze).

Credit budget:
    One fetch = 1 credit (1 market × 1 region × 1 request). CFB has ~130
    games per week during the season. Warmer runs every 25 min → 57.6
    credits/day → ~1,730 credits/month. Same budget as MLB. Combined
    MLB + CFB usage: ~3,460 credits/month, well under Kevin's 20K plan.

API key comes from the ODDS_API_KEY environment variable (same key used
by mlb.odds). If unset, this module logs and returns an empty list —
the slate still builds without odds. Never hard-fails.
"""

from __future__ import annotations

import os
import re
import requests
from datetime import datetime, timezone
from typing import Optional


ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf/odds"

# Same book priority as MLB. Pinnacle deliberately excluded (not in US region).
BOOK_PRIORITY = ["draftkings", "fanduel", "betmgm", "williamhill_us"]

BOOK_DISPLAY_NAMES = {
    "pinnacle":       "Pinnacle",
    "draftkings":     "DraftKings",
    "fanduel":        "FanDuel",
    "betmgm":         "BetMGM",
    "williamhill_us": "Caesars",
}

REQUEST_TIMEOUT_SEC = 12


def _normalize_team_name(name: str) -> str:
    """Lowercase and strip punctuation so ESPN team names match The Odds
    API team names. Both APIs use full names; defensive normalization
    handles edge cases like "Texas A&M" vs "Texas A&amp;M"."""
    if not name:
        return ""
    n = name.lower().strip()
    n = re.sub(r"[^\w\s]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _pick_book(bookmakers: list[dict]) -> Optional[dict]:
    """Return the bookmaker matching BOOK_PRIORITY, first-match. Falls back
    to whichever book is first in the response if none match."""
    by_key = {bk.get("key"): bk for bk in bookmakers if bk.get("key")}
    for pref in BOOK_PRIORITY:
        if pref in by_key:
            return by_key[pref]
    for bk in bookmakers:
        if bk.get("key"):
            return bk
    return None


def _extract_total_from_book(book: dict) -> Optional[float]:
    """Extract the totals market's Over.point from a bookmaker payload."""
    for market in book.get("markets", []):
        if market.get("key") != "totals":
            continue
        for outcome in market.get("outcomes", []):
            if outcome.get("name") == "Over":
                return outcome.get("point")
    return None


def fetch_cfb_totals() -> list[dict]:
    """Fetch current CFB totals from The Odds API. Returns a list of
    dicts (one per game) with commence_time, home/away team names +
    normalized versions, total, and book info. Returns [] on any
    failure — never raises. Odds are additive, not critical."""
    api_key = os.environ.get("ODDS_API_KEY", "").strip()
    if not api_key:
        print("[cfb.odds] ODDS_API_KEY not set; skipping odds fetch", flush=True)
        return []

    try:
        resp = requests.get(
            ODDS_API_URL,
            params={
                "apiKey":     api_key,
                "regions":    "us",
                "markets":    "totals",
                "oddsFormat": "american",
                "dateFormat": "iso",
            },
            timeout=REQUEST_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        raw_games = resp.json()
    except Exception as e:
        print(f"[cfb.odds] fetch failed: {type(e).__name__}: {e}", flush=True)
        return []

    out = []
    for g in raw_games:
        try:
            commence_iso = g.get("commence_time", "")
            home = g.get("home_team", "")
            away = g.get("away_team", "")
            bookmakers = g.get("bookmakers", [])
            if not (commence_iso and home and away and bookmakers):
                continue

            book = _pick_book(bookmakers)
            if not book:
                continue
            total = _extract_total_from_book(book)
            if total is None:
                continue

            commence_dt = datetime.fromisoformat(commence_iso.replace("Z", "+00:00"))
            if commence_dt.tzinfo is None:
                commence_dt = commence_dt.replace(tzinfo=timezone.utc)

            book_key = book.get("key", "")
            out.append({
                "commence_time_utc": commence_dt,
                "home_team":         home,
                "away_team":         away,
                "home_team_norm":    _normalize_team_name(home),
                "away_team_norm":    _normalize_team_name(away),
                "total":             float(total),
                "book_key":          book_key,
                "book_display":      BOOK_DISPLAY_NAMES.get(book_key, book_key.title()),
            })
        except Exception as e:
            print(f"[cfb.odds] parse failed for one game: {type(e).__name__}: {e}", flush=True)
            continue

    print(f"[cfb.odds] fetched totals for {len(out)} games", flush=True)
    return out


def match_odds_to_game(
    odds_list: list[dict],
    away_team: str,
    home_team: str,
    kickoff_utc: datetime,
    tolerance_hours: float = 6.0,
) -> Optional[dict]:
    """Find the odds entry matching a given CFB game.

    Match criteria:
        1. Normalized home team name matches
        2. Normalized away team name matches
        3. commence_time within tolerance_hours of kickoff (default 6h to
           handle CFB kickoff-time uncertainty — early-week the Odds API
           often uses a placeholder time that shifts as TV windows firm up).
    """
    home_norm = _normalize_team_name(home_team)
    away_norm = _normalize_team_name(away_team)
    tolerance_sec = tolerance_hours * 3600

    best_match = None
    best_delta_sec = None
    for o in odds_list:
        if o["home_team_norm"] != home_norm:
            continue
        if o["away_team_norm"] != away_norm:
            continue
        delta_sec = abs((o["commence_time_utc"] - kickoff_utc).total_seconds())
        if delta_sec > tolerance_sec:
            continue
        if best_delta_sec is None or delta_sec < best_delta_sec:
            best_match = o
            best_delta_sec = delta_sec
    return best_match
