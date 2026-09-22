# OVERcast Live (NFL) — live observations from NWS

**For:** OVERcast Live AI
**From:** MSW / mysportsweather.com
**Date:** 2026-09-01

You already built this for MLB. This is the same thing for NFL, plus the
guardrails that keep it from taking down mysportsweather.com.

---

## 1. Read this part even if you skip the rest

**MSW and OVERcast Live share an outbound IP.**

Render's egress IPs are shared across every service in a region — and
across other Render customers. There is no per-service isolation. NWS
rate-limits by address, and their docs note that proxies (which a shared
egress pool resembles) hit limits far sooner than direct clients.

So: **if Live over-fetches NWS, mysportsweather.com gets throttled and
starts failing.** Not Live — MSW. The revenue site.

MSW already runs ~210 NWS requests/hour on a CFB Saturday. Live's traffic
lands on top of that, on the same address.

Everything in §3 exists for this reason. None of it is optional.

---

## 2. What to build

Latest observed conditions for each NFL game, refreshed **4×/hour**,
during a window of **kickoff −30 min through final +30 min**.

Observations, not forecasts. The point is that when it starts raining,
Live sees "rain" — not a forecast that predicted it.

### Endpoints

```
# One-time per stadium, cache permanently:
GET https://api.weather.gov/points/{lat},{lon}/stations
    → observationStations[]  (ordered nearest-first)

# Every poll, one call per station:
GET https://api.weather.gov/stations/{stationId}/observations/latest
```

### Required header

NWS blocks requests without a proper User-Agent. Use a **distinct** one so
Kevin can tell Live's traffic from MSW's in a throttle event:

```python
HEADERS = {
    "User-Agent": "overcast-live/1.0 nfl (kevinrothwx@gmail.com)",
    "Accept": "application/geo+json",
}
```

Do **not** reuse MSW's UA (`kevinrothwx-site/1.0 ncaaf`). If both services
log identically, a throttle event is undiagnosable.

---

## 3. The guardrails

### 3.1 Stagger — the most important one

One pull = one station. There is no batch endpoint. So 16 concurrent NFL
games = 16 requests per cycle.

The danger is not the total (~290 requests across an NFL Sunday, which is
nothing). It is the **shape**. If every game polls at :00/:15/:30/:45 you
fire 9–16 simultaneous requests four times an hour, and that burst is what
trips a rate limiter.

Give each game a fixed offset derived from its ID:

```python
offset_sec = hash(str(game_id)) % 900        # 0–899, stable per game
# poll when: (epoch_seconds % 900) == offset_sec, within the game window
```

Same 4 pulls/hour, spread evenly across each quarter-hour instead of
stacked. Use a **stable** hash (`zlib.crc32`, not Python's `hash()`, which
is randomized per process) so a restart doesn't re-cluster everything.

### 3.2 Concurrency cap

Never more than **5 requests in flight**, ever, regardless of game count.
A semaphore, not a convention.

### 3.3 Pace between calls

200ms minimum between consecutive calls (max 5/sec — the published NWS
recommendation). MSW uses exactly this.

### 3.4 Back off on 429 and 5xx

On 429 or 503: stop, wait, retry with exponential backoff and jitter,
cap around 10 minutes. **Serve the last good observation while backing
off.** Do not retry tightly — that is the failure that takes MSW with it.

```python
delay = min(max(prev_delay * 2, 30), 600) + random.uniform(0, 5)
```

### 3.5 Never fetch outside the game window

No games in progress = zero requests. This is most of the safety: NFL is
~6 hours on Sunday, not 24/7.

### 3.6 Kill switch

An env var Live checks every cycle — `LIVE_OBS_ENABLED=0` stops all NWS
fetching without a redeploy. If MSW starts throwing NWS errors, Kevin needs
to stop Live in seconds, not wait on a build.

### 3.7 Cache the station map forever

Stadium coordinates never change. Resolve `/points/{lat},{lon}/stations`
once per stadium, persist it, never call it again. Store 2–3 stations per
stadium so a quiet station fails over without a second round trip.

---

## 4. Volume, so you can sanity-check

| | Games | Window | Pulls/game | Total |
|---|---|---|---|---|
| NFL Sunday | 16 | 4.5 hr | 18 | **~290** |
| NFL full week | ~16 | — | — | **~310** |

~290 requests spread across 6 hours is ~48/hour, under 1/minute. That is
genuinely small. If your implementation produces materially more than
this, something is wrong — most likely polling outside the game window or
not caching the station map.

---

## 5. Parsing

`observations/latest` returns `properties` with:

- `temperature.value` — **Celsius**, convert
- `windSpeed.value` — **km/h**, convert
- `windDirection.value` — degrees, direction wind comes FROM
- `textDescription` — present weather, e.g. `"Light Rain"`
- `timestamp` — ISO 8601

Two things that matter:

**Reject stale observations.** Anything older than ~45 minutes should be
treated as no data. A "Clear" reading from an hour ago during a downpour
reads as current truth and is worse than showing nothing.

**Any field can be null.** NWS observations frequently have null wind or
null temperature on individual cycles. Fall back to the next station
rather than rendering a blank.

For "is it raining," prefer `textDescription` over precipitation
accumulation — accumulation lags and reads 0.00 during light rain that
just started.

---

## 6. Say what it actually is

The station is typically **an airport a few miles from the stadium**, not
a sensor on the field. Surface it:

> Rain — KPHL, 7.2 mi away, observed 8 min ago

A scattered thunderstorm can soak the airport and miss the stadium. That
is exactly the situation this product is for, so don't paper over it.

Domes: no observation. Show "indoor," never stale outdoor conditions.

---

## 7. Checklist

- [ ] Distinct User-Agent with contact email — not MSW's
- [ ] Station map resolved once and cached permanently
- [ ] Per-game stagger via stable hash (crc32, not `hash()`)
- [ ] Concurrency capped at 5, enforced by semaphore
- [ ] 200ms minimum between calls
- [ ] Exponential backoff with jitter on 429/503, serving stale meanwhile
- [ ] Zero requests when no game is in its window
- [ ] `LIVE_OBS_ENABLED` kill switch checked every cycle
- [ ] Observations older than 45 min treated as missing
- [ ] Null-safe parsing with station failover
- [ ] UI shows station name, distance, observation age

---

## 8. What Kevin needs from you

Confirm in writing before this goes live:

1. **Requests per NFL Sunday, measured** — not estimated. Should be ~290.
2. **A log line per cycle** showing request count and any 429s, so a
   problem is visible before MSW starts failing.
3. **Kill switch tested** — flip it, confirm NWS traffic stops.

If MSW starts returning NWS errors after this ships, Live is the first
suspect, and #3 is how you clear it fast.
