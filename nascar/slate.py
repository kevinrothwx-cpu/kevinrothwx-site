"""
nascar.slate — build the race day view (hourly forecast around green flag).

Each race entry includes:
  - track metadata
  - green flag time (UTC + track-local + Eastern)
  - hourly forecast for ±2 hours around green flag
  - summary forecast at green flag
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from .tracks import lookup_track
from .schedule import get_nascar_scoreboard, parse_nascar_event, race_slug

from mlb.nws import (
    get_nws_hourly_url, get_nws_periods,
    find_period_for_time, extract_forecast,
    attach_nws_gusts,
)
from mlb.weatherapi import fetch_weatherapi_hourly, find_weatherapi_period
from hrrr import get_hrrr_periods


EASTERN_TZ = ZoneInfo("America/New_York")

HOURS_BEFORE = 2   # pre-race buildup
HOURS_RACE   = 3   # most Cup races are ~3 hours
HOURS_AFTER  = 1


def _forecast_for_track(track, target_utc):
    if track.get("nws_unsupported"):
        try:
            periods = fetch_weatherapi_hourly(track["lat"], track["lon"])
            chosen = find_weatherapi_period(periods, target_utc)
            return chosen, periods, "weatherapi", None
        except Exception as e:
            return None, None, "weatherapi", str(e)
    try:
        url = get_nws_hourly_url(track["lat"], track["lon"])
        raw = get_nws_periods(url)
        chosen_raw = find_period_for_time(raw, target_utc)
        chosen = extract_forecast(chosen_raw)
        normalized = [extract_forecast(p) for p in raw]
        # Merge in gusts from NWS gridpoint windGust series.
        attach_nws_gusts(normalized, track["lat"], track["lon"])
        # Also try to attach a gust to the chosen-period summary so the
        # green-flag forecast block can show gust if templates want it.
        if normalized:
            for p in normalized:
                if p.get("start_time") == chosen.get("start_time"):
                    chosen["gust"] = p.get("gust")
                    break
        return chosen, normalized, "nws", None
    except Exception as e:
        return None, None, "nws", str(e)


def _hourly_window(periods, green_flag_utc):
    if not periods:
        return []
    fp = green_flag_utc.replace(minute=0, second=0, microsecond=0)
    start = fp - timedelta(hours=HOURS_BEFORE)
    end   = fp + timedelta(hours=HOURS_RACE + HOURS_AFTER)
    out = []
    for p in periods:
        st = datetime.fromisoformat(p["start_time"])
        if st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        st_utc = st.astimezone(timezone.utc)
        if start <= st_utc < end:
            st_eastern = st_utc.astimezone(EASTERN_TZ)
            p2 = dict(p)
            p2["hour_eastern"] = st_eastern.strftime("%-I %p").lstrip("0")
            p2["hour_eastern_dt"] = st_eastern
            p2["is_race_hour"] = fp <= st_utc < fp + timedelta(hours=HOURS_RACE)
            out.append(p2)
    return out


def build_race(event):
    """Build a fully-loaded race dict ready for the template."""
    track = lookup_track(event["track"])
    forecast = None
    hourly = []
    source = None
    err = None
    gf_utc = gf_local = gf_eastern = None

    try:
        gf_utc = datetime.fromisoformat(event["green_flag_utc"].replace("Z", "+00:00"))
    except Exception:
        pass

    hrrr_hourly = []
    if track and gf_utc:
        forecast, periods, source, err = _forecast_for_track(track, gf_utc)
        hourly = _hourly_window(periods or [], gf_utc)
        tz = ZoneInfo(track["timezone"])
        gf_local = gf_utc.astimezone(tz)
        gf_eastern = gf_utc.astimezone(EASTERN_TZ)

        # HRRR (CONUS only, ~48 h horizon). Bounding-box check inside
        # get_hrrr_periods decides coverage — independent of NWS. Silent
        # on failure; toggle just won't render.
        try:
            hrrr_periods = get_hrrr_periods(track["lat"], track["lon"])
            if hrrr_periods:
                hrrr_hourly = _hourly_window(hrrr_periods, gf_utc)
        except Exception as e:
            print(f"[nascar.slate] HRRR fetch error for {track.get('name','?')}: {e}", flush=True)

    return {
        **event,
        "track_meta":  track,
        "green_flag_utc_dt": gf_utc,
        "green_flag_local":  gf_local,
        "green_flag_eastern": gf_eastern,
        "green_flag_eastern_str": gf_eastern.strftime("%-I:%M %p ET").lstrip("0") if gf_eastern else "",
        "green_flag_eastern_date_str": gf_eastern.strftime("%a, %b %-d") if gf_eastern else "",
        "forecast":    forecast,
        "hourly":      hourly,
        "hrrr_hourly": hrrr_hourly,
        "slug":        race_slug(event["short_name"] or event["name"]),
        "weather_source": source,
        "weather_error":  err,
    }


def build_nascar_slate():
    """Build current/upcoming NASCAR Cup races.

    Filters completed/past races so /nascar always shows the next upcoming
    race, never lingers on last Sunday's. Mirrors the PGA filter pattern.
    """
    raw = get_nascar_scoreboard()
    out = []
    for event in raw:
        parsed = parse_nascar_event(event)
        if not parsed:
            continue

        # Drop ESPN-flagged completed races. ESPN's status name varies —
        # STATUS_FINAL, STATUS_COMPLETED, STATUS_POST_GAME, etc.
        status = (parsed.get("status") or "").upper()
        DONE_KEYWORDS = ("FINAL", "POST", "COMPLETED", "ENDED")
        if any(kw in status for kw in DONE_KEYWORDS):
            print(f"[nascar.slate] filtered {parsed.get('name')!r} on status={status}", flush=True)
            continue

        # Drop races whose green flag was more than 12 hours ago. A 4-hour
        # race that started Sunday at 3 PM ET (19:00 UTC) is over by 23:00 UTC
        # Sunday. By Monday 7 AM UTC (12h later), the race is well past and
        # next Sunday's race should take its place.
        gf_iso = parsed.get("green_flag_utc") or ""
        if gf_iso:
            try:
                gf = datetime.fromisoformat(gf_iso.replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - gf).total_seconds() / 3600
                if age_hours > 12:
                    print(f"[nascar.slate] filtered {parsed.get('name')!r} (green flag {age_hours:.1f}h ago)", flush=True)
                    continue
            except (ValueError, TypeError) as e:
                print(f"[nascar.slate] WARN green_flag_utc parse failed for {parsed.get('name')!r}: {gf_iso!r} ({e})", flush=True)

        out.append(build_race(parsed))
    out.sort(key=lambda r: r.get("green_flag_utc", ""))
    return out
