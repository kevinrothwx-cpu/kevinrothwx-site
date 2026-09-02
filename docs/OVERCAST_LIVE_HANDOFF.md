# OVERcast Live — weather data handoff

**For:** whoever is building OVERcast Live
**From:** MSW / mysportsweather.com
**Date:** 2026-09-01

---

## TL;DR

Live needs **current observed conditions** during a game. Get them from
**Synoptic Data**, in **one batched request per poll cycle**, using the
stadium→station map generated from MSW's venue tables.

**Do not call NWS. Do not call MSW.** Both are explained below, and the
first one is not a style preference — it can take mysportsweather.com
down.

Two files in the MSW repo are yours to take:

| File | What it is |
|---|---|
| `tools/build_station_map.py` | Generates the stadium→station map. Run once. |
| `tools/synoptic_live_client.py` | Reference client. Copy into Live. |

---

## 1. The constraint that drives everything

Render's outbound IP addresses are **shared across every service in a
region, and across other Render customers in that region**. There is no
per-service isolation without paying for dedicated outbound IPs.

MSW depends on three weather upstreams:

- `api.weather.gov` (NWS — the primary forecast source)
- `api.weatherapi.com` (fallback + international venues)
- `open-meteo.com` (NBM model overlay)

If Live over-fetches **any of those three**, the shared address can get
throttled and **MSW starts failing**. That is the path from "low-priority
side project" to "the revenue site is down." NWS's own documentation notes
that proxies are far more likely to hit their limit than direct clients —
and a shared egress pool behaves exactly like a proxy.

Splitting Live into a separate Render service does **not** fix this. Same
IP pool either way.

**The fix is to use an upstream MSW does not touch.** Synoptic Data
qualifies. Live's request budget then has no relationship to MSW's.

> **Do not add an NWS fallback "for resilience."** It reintroduces the exact
> coupling this design exists to remove, and it will fire precisely when
> things are already going wrong. If Synoptic is down, serve stale data or
> serve nothing.

---

## 2. Why Synoptic, and what you get

- **Real observations**, not forecasts — METAR plus mesonet networks.
- **NOAA high-frequency METAR updates about every 5 minutes** at airport
  stations (`hfmetars` is on by default), so "it just started raining" is
  detectable on a useful timescale.
- **Present weather** (`weather_condition`: rain / snow / thunderstorm)
  rather than only an accumulation counter, which lags.
- **Batched**: the Latest service takes a comma-separated station list and
  allows up to 75,000 stations per call.

Free tier is **5,000 requests/month**. With batching, a full CFB Saturday
polled every 5 minutes for 12 hours is **144 requests**. Add NFL Sunday and
weeknights and you land near **1,400/month**. Comfortable.

Without batching — one request per stadium — the same Saturday is ~12,500
requests and you blow the monthly tier in a single afternoon. **The
batching is the design.**

---

## 3. Build the station map

```bash
export SYNOPTIC_TOKEN=...        # https://synopticdata.com/pricing/free-trial/
python3 tools/build_station_map.py
```

Writes `data/venue_station_map.json` and a `_report.txt` of anything worth
a human glance.

- Covers **204 venues**: 134 CFB home, 20 CFB neutral, 30 NFL, 10 NFL
  international, 33 MLB parks (deduped where a venue serves several sports —
  Yankee Stadium is MLB and a CFB bowl site, SoFi is NFL and the LA Bowl).
- Costs **197 API calls, once**. Responses cache to disk, so re-runs are free.
- Domes are included but flagged `needs_obs: false`. There is no weather
  indoors; the row exists so a lookup returns "indoor" rather than missing.
- Each venue gets a **primary plus up to 2 fallbacks**, so a station going
  quiet doesn't blank the game.

**Read the report before trusting the map.** It flags:

- `FAR STATION` — nearest station >15 mi. Real for rural venues; decide
  whether that's good enough to show.
- `NO PRESENT-WX` — station reports accumulation but not rain/snow type,
  so precip detection is weaker there.
- `MLB MISMATCH` — the nearest station disagrees with the `asos_station`
  already hand-entered in `mlb/park_metadata.py`. That file has entries
  marked "verified by Kevin" and others marked "assumed"; a mismatch on an
  assumed one probably means the generator is right, and on a verified one
  probably means it's wrong. **Check, don't auto-apply.**

---

## 4. Use the client

```python
from synoptic_live_client import (
    SynopticLiveClient, load_station_map, all_station_ids, conditions_for_venue)

smap   = load_station_map("data/venue_station_map.json")
stids  = all_station_ids(smap)          # ~200 ids
client = SynopticLiveClient(min_seconds_between_calls=60)

conds  = client.get_conditions(stids)   # ONE request, all venues
wx     = conditions_for_venue("Bryant-Denny Stadium|Tuscaloosa, AL", smap, conds)
```

Properties already built in — please keep them:

- **One request per cycle regardless of caller count.** A lock serializes
  concurrent game threads so N threads produce 1 upstream call, not N.
- **Cache respected.** Calling once per game per second still yields at
  most one request per minute.
- **Backoff on failure**, 30s → 600s with jitter. Serves stale cache while
  backing off rather than retrying into a service that just said slow down.
- **Stale observations dropped** past 45 minutes. A "clear" reading from an
  hour ago during a downpour is worse than no reading.
- **Never raises.** Failures set `.last_error` and return last-good cache.
  Surface `client.status()` in Live's admin.

### Returned shape

```json
{
  "stid": "KTCL",
  "station_name": "Tuscaloosa Regional Airport",
  "observed_at_utc": "2026-09-05T23:53:00Z",
  "obs_age_min": 4.2,
  "temp_f": 71.0,
  "wind_mph": 12.0,
  "gust_mph": 21.0,
  "wind_dir_deg": 270.0,
  "humidity_pct": 88.0,
  "weather_text": "light rain",
  "precip_accum_1h_in": 0.04,
  "is_precipitating": true,
  "station_distance_mi": 6.2,
  "used_fallback": false,
  "source": "synoptic",
  "is_observation": true
}
```

`conditions_for_venue()` returns `None` for domes and when every mapped
station is stale or missing. **When it returns None, say "no current
observation."** Do not silently substitute a forecast — the entire reason
this exists is that a forecast is not an observation.

---

## 5. Say what this actually is

The nearest station is typically **an airport a few miles from the
stadium**, not a sensor on the field. NWS observations have the same
limitation, so this isn't a downgrade — but the UI should carry the
provenance:

> Conditions at KTCL (6.2 mi away), observed 4 minutes ago

not

> Conditions at Bryant-Denny Stadium

That distinction matters most in exactly the situation the product is for:
a scattered thunderstorm can be soaking the airport and missing the stadium,
or the reverse.

---

## 6. If you need weather from MSW anyway

MSW's API (`docs/FORECAST_API_CONTRACT_v1.md`) serves **forecasts**, not
observations, including an `hourly` array covering kickoff −1h through +4h.
That is the game window, and it needs an API key.

It is a reasonable belt-and-suspenders source for *forecast* context
alongside live obs. It is **not** a substitute for observations, and MSW
has no plans to add an observation fetcher — doing so would increase MSW's
own NWS footprint, which is the thing we're protecting.

If Live does call MSW, it gets its own key with a **lower** rate limit than
OVERcast's, so a runaway loop in a low-priority service can't degrade the
site. Note that MSW's per-key limiter is currently in-memory per worker and
has never been exercised by a real client — worth load-testing before
relying on it as a safety net.

---

## 7. Checklist

- [ ] Synoptic token; confirm the tier includes **mesonet networks**, not
      airport-only — density is most of the value in metro areas
- [ ] Run `build_station_map.py`, read the report, resolve flagged rows
- [ ] Copy `synoptic_live_client.py` into Live
- [ ] Verify in logs that a poll cycle produces **exactly one** upstream request
- [ ] Confirm no code path reaches `weather.gov`, `weatherapi.com`, or `open-meteo`
- [ ] Surface `client.status()` somewhere you'll actually look
- [ ] UI shows station name, distance, and observation age
- [ ] Domes render "indoor", not stale outdoor conditions

---

## Open questions for Kevin

1. **Poll interval?** 5 min matches METAR cadence and costs ~1,400/mo.
   Faster buys nothing — the upstream data doesn't update faster.
2. **Does the partner need true stadium-sited observation**, or is
   nearest-station acceptable? Worth settling before it's promised.
3. **MLB Live already fetches NWS directly** and is on the shared IP pool
   today. It should move to this client or at minimum get a concurrency cap
   and 429 backoff. CFB Saturday is the burst that would expose it.
