"""
game_precip — rain chance across the GAME, not just the kickoff hour.

WHY THIS EXISTS (2026-09-18)
    Every sport's slate builder sets game["forecast"] to a single hourly
    period, the one containing kickoff. Every card, icon and colour then
    reads precip_pct off that one hour.

    Kevin caught what that does. Browns at Buccaneers, 1:00 PM kickoff:

        hour      12 PM   1 PM   2 PM   3 PM   4 PM
        precip      8%     8%    76%    76%    76%
        game hours         ^^^^^^^^^^^^^^^^

    The card read "8% RAIN" with a sun icon, for a game with a 76% chance
    of storms through the second half. Technically true about 1:00 PM,
    useless to anyone deciding whether weather matters.

WHAT THIS DOES
    Takes the MAXIMUM precip across the hours already flagged is_game_hour
    by each sport's _hourly_window(), and writes it to forecast.precip_pct.
    The kickoff-hour value is preserved as precip_pct_kickoff.

    Overwriting precip_pct rather than adding a new field is deliberate:
    ten sports' templates already read precip_pct for the number, the
    colour class and the weather icon. Changing the value in one place
    fixes all three everywhere, and the icon stops disagreeing with the
    hourly table underneath it.

    Max, not average: a 76% chance for three of four quarters is a rain
    game. Averaging it to 40% would understate it in exactly the cases
    that matter.
"""

from __future__ import annotations

from typing import Optional

# Which key each sport's _hourly_window() uses to flag the in-game hours.
# Every sport says is_game_hour except NASCAR, which says is_race_hour. Check
# both rather than renaming NASCAR's, because its templates read is_race_hour
# in five places. A sport whose flag is missing from this tuple gets no
# change at all, silently, so add the name here when adding a sport.
GAME_HOUR_KEYS = ("is_game_hour", "is_race_hour")


def apply_game_window_precip(forecast: Optional[dict],
                             hourly: Optional[list]) -> Optional[dict]:
    """Return a NEW forecast dict with precip_pct set to the game-window max.

    Never mutates the input. That matters for MLB, CWS and NASCAR, where the
    forecast passed in can be a snapshot owned by forecast_freeze — frozen
    snapshots are immutable by house rule, and this runs on every slate
    build, so mutating in place would rewrite the freeze store.

    Never raises: a missing forecast, empty hourly, or hours with no precip
    data all return the forecast unchanged, which is the pre-2026-09-18
    behaviour."""
    if not forecast or not hourly:
        return forecast
    try:
        vals = [h.get("precip_pct") for h in hourly
                if any(h.get(k) for k in GAME_HOUR_KEYS)]
        vals = [v for v in vals if isinstance(v, (int, float))]
        if not vals:
            return forecast
        kickoff_val = forecast.get("precip_pct")
        game_max = max(vals)
        out = dict(forecast)
        if isinstance(kickoff_val, (int, float)):
            out["precip_pct_kickoff"] = kickoff_val
        out["precip_pct"] = game_max
        out["precip_pct_is_game_max"] = (
            isinstance(kickoff_val, (int, float)) and game_max > kickoff_val
        )
        return out
    except Exception:
        return forecast
