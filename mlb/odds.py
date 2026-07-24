"""
mlb.odds — The Odds API client for MLB game totals (O/U).

Configuration:
    - Source: api.the-odds-api.com, sport `baseball_mlb`
    - Market: `totals` only (never spreads, never moneylines)
    - Region: `us` (US-licensed books only — see book-choice note below)
    - Book priority: DraftKings → FanDuel → BetMGM → Caesars → first
      available. NEVER averages across books — that produces non-real
      lines like 7.75 that cause false pushes.
    - Timing: pulls the current pre-game line at fetch time. Once a game
      starts, the line freezes (handled in mlb/slate.py via the existing
      forecast_freeze pattern).

Book-choice note (decided 2026-07-24):
    OVERcast uses Pinnacle-first (eu region), falling back to DraftKings.
    MSW deliberately DIVERGES from OVERcast on this: MSW uses DraftKings
    primary (us region only). Rationale:
      - Pinnacle isn't legal in the US, so those numbers are "reference
        only" for MSW's audience (casual sports fans / weather-focused).
      - DK is what MSW users can actually bet at, so the number they see
        on MSW matches what they'd see in their DK app.
      - Future plan: hyperlink the O/U value on the site to a DK affiliate
        link so users can click through and place a bet directly. Having
        the displayed line match DK's line is a prerequisite.
    Trade-off: MSW's totals will sometimes differ from OVERcast's by
    ~0.5 for the same game (DK vs. Pinnacle). Accepted.

Credit budget:
    One fetch = 1 credit (1 market × 1 region × 1 request).
    Warmer runs every 25 min → 57.6 credits/day → ~1,730 credits/month.
    Well under the 20K/month plan Kevin has.

API key comes from the ODDS_API_KEY environment variable. If unset, the
module logs and returns an empty list — the slate build still works,
odds just don't show. Never hard-fails.
"""

from __future__ import annotations

import os
import re
import requests
from datetime import datetime, timezone
from typing import Optional


ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"

# Book priority for MSW — DraftKings first. Pinnacle is deliberately NOT
# in this list even though OVERcast uses it, because Pinnacle isn't in
# The Odds API's `us` region response and MSW's audience needs a US-legal
# book they can actually bet at. See module docstring for the full
# rationale. Do NOT re-add pinnacle unless you also change region=us to
# region=us,eu (which doubles credit cost per fetch).
BOOK_PRIORITY = ["draftkings", "fanduel", "betmgm", "williamhill_us"]
# Note: "williamhill_us" is Caesars' API name on The Odds API.

# Short display names keyed by the API's book keys.
BOOK_DISPLAY_NAMES = {
    "pinnacle":       "Pinnacle",
    "draftkings":     "DraftKings",
    "fanduel":        "FanDuel",
    "betmgm":         "BetMGM",
    "williamhill_us": "Caesars",
}

REQUEST_TIMEOUT_SEC = 12


def _normalize_team_name(name: str) -> str:
    """Lowercase and strip punctuation so MLB Stats API team names ("New York
    Yankees") match The Odds API team names ("New York Yankees"). Both APIs
    use full names, but defensive normalization helps against surprises."""
    if not name:
        return ""
    n = name.lower().strip()
    n = re.sub(r"[^\w\s]", "", n)     # drop punctuation
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _pick_book(bookmakers: list[dict]) -> Optional[dict]:
    """Given a game's list of bookmakers from the API, return the one that
    comes first in BOOK_PRIORITY. Returns None if none of the priority
    books have a totals market."""
    by_key = {bk.get("key"): bk for bk in bookmakers if bk.get("key")}
    for pref in BOOK_PRIORITY:
        if pref in by_key:
            return by_key[pref]
    # Priority fallback exhausted — take the first available book.
    for bk in bookmakers:
        if bk.get("key"):
            return bk
    return None


def _extract_total_from_book(book: dict) -> Optional[float]:
    """Book's markets list should include a `totals` market. Extract the
    Over outcome's `point` (the total number). Returns None if the book
    doesn't have a totals market."""
    for market in book.get("markets", []):
        if market.get("key") != "totals":
            continue
        for outcome in market.get("outcomes", []):
            if outcome.get("name") == "Over":
                return outcome.get("point")
    return None


def fetch_mlb_totals() -> list[dict]:
    """Fetch current MLB totals from The Odds API. Returns a list of
    dicts, one per game, in this shape:

        {
          "commence_time_utc": datetime,
          "home_team":          "New York Yankees",
          "away_team":          "Boston Red Sox",
          "home_team_norm":     "new york yankees",
          "away_team_norm":     "boston red sox",
          "total":              8.5,
          "book_key":           "draftkings",
          "book_display":       "DraftKings",
        }

    Returns [] on any failure (missing API key, network error, unexpected
    payload). Never raises — odds are additive, not critical."""
    api_key = os.environ.get("ODDS_API_KEY", "").strip()
    if not api_key:
        print("[mlb.odds] ODDS_API_KEY not set; skipping odds fetch", flush=True)
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
        print(f"[mlb.odds] fetch failed: {type(e).__name__}: {e}", flush=True)
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
            print(f"[mlb.odds] parse failed for one game: {type(e).__name__}: {e}", flush=True)
            continue

    print(f"[mlb.odds] fetched totals for {len(out)} games", flush=True)
    return out


def match_odds_to_game(
    odds_list: list[dict],
    away_team: str,
    home_team: str,
    game_start_utc: datetime,
    tolerance_hours: float = 3.0,
) -> Optional[dict]:
    """Find the odds entry that matches a given MLB game.

    Match criteria:
        1. Normalized home team name matches
        2. Normalized away team name matches
        3. commence_time is within `tolerance_hours` of game_start_utc
           (handles doubleheaders where two games have the same teams
            on the same day but different start times)
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
        delta_sec = abs((o["commence_time_utc"] - game_start_utc).total_seconds())
        if delta_sec > tolerance_sec:
            continue
        if best_delta_sec is None or delta_sec < best_delta_sec:
            best_match = o
            best_delta_sec = delta_sec
    return best_match
