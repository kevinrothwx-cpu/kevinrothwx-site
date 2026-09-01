# MSW Forecast API — Data Contract v1

**Status:** Draft for review by MSW + OVERcast
**Purpose:** Define the exact schema, units, and conventions for the JSON API that OVERcast consumes from MySportsWeather. Pinning these values up front prevents silent-wrongness bugs (like the past wind-direction convention mismatch).

**Scope:** NFL and CFB forecast fields only. OVERcast's impact analytics are OVERcast's own layer on top and out of scope for this contract.

## Base

- **Base URL:** `https://mysportsweather.com/api/v1/`
- **Auth:** All requests require `X-API-Key: <key>` header. Kevin issues per-consumer keys so they can be rotated/revoked without affecting others.
- **Rate limit:** 60 requests per minute per API key. Excess returns `429 Too Many Requests` with a `Retry-After` seconds header.
- **Response format:** JSON, UTF-8. `Content-Type: application/json`.
- **Versioning:** `/api/v1/` path prefix. Breaking shape changes require `/api/v2/`. Additive optional fields allowed within v1. Deprecations announced with 60-day migration window.

## Endpoints

### `GET /nfl/slate`

Returns the current NFL slate (games in the next 8 days).

**Response body:**
```json
{
  "games": [Game, ...],
  "meta": Meta
}
```

### `GET /nfl/game/{event_id}`

Returns one NFL game by ESPN event ID.

**Response body:**
```json
{
  "game": Game,
  "meta": Meta
}
```

**404** if event_id is not on the current slate.

### `GET /cfb/slate` and `GET /cfb/game/{event_id}`

Same shape as NFL. `game.sport = "cfb"`.

## Object schemas

### `Game`

```json
{
  "event_id": "401547416",
  "sport": "nfl",
  "season_type": 2,
  "season_type_label": "Regular Season",
  "week": 1,
  "home": Team,
  "away": Team,
  "venue": Venue,
  "kickoff_utc": "2026-09-08T20:20:00Z",
  "kickoff_local_str": "4:20 PM ET",
  "status": "pre",
  "slug": "kc-at-lar",
  "forecast_at_kickoff": Forecast,
  "hourly": [Forecast, ...],
  "hrrr_hourly": [Forecast, ...],
  "weather_source": "nws",
  "weather_error": null,
  "is_frozen": false,
  "frozen_at_utc": null,
  "writeup": Writeup
}
```

**Field notes:**

- `event_id`: ESPN's event ID, stable identifier. Use as your primary key.
- `sport`: `"nfl"` or `"cfb"`.
- `season_type`: 1 = preseason, 2 = regular season, 3 = postseason. Pro Bowl (4) is filtered out.
- `week`: integer, may be `null` for postseason or exhibition games.
- `kickoff_utc`: ISO 8601 with `Z` suffix. All timestamps UTC.
- `kickoff_local_str`: Display-only convenience string in venue-local time with timezone abbreviation. **Do not parse this — use `kickoff_utc` for time math.**
- `status`: ESPN's status.state — `"pre"`, `"in"`, `"post"`.
- `slug`: URL-safe game slug used in MSW's own URLs. Provided for cross-linking, not required for logic.
- `forecast_at_kickoff`: `Forecast` object or `null`. `null` when the venue is a fixed dome (`weather_source: "indoor-skip"`) or all upstream fetches failed (`weather_source: "all-failed"`).
- `hourly`: Array of `Forecast` objects covering 1 hour before kickoff through 4 hours after. Empty array if forecast unavailable.
- `hrrr_hourly`: Array of `Forecast` objects, HRRR high-res overlay. Same time window as `hourly`. Empty array for non-CONUS venues or when HRRR fetch failed. **Same schema as `hourly` — the field name distinguishes source.**
- `weather_source`: enum indicating which upstream provider filled this forecast. See "weather_source values" section below.
- `weather_error`: `null` on success, string diagnostic when a data-source path failed.
- `is_frozen`: `true` when the kickoff snapshot has been locked (kickoff is within the freeze window: 1 hour before through 6 hours after). While `is_frozen: true`, `forecast_at_kickoff` values do not change until the release window closes.
- `frozen_at_utc`: ISO 8601 timestamp when the snapshot was taken. `null` while not frozen.
- `writeup`: Optional `Writeup` object with Kevin's colored meteorologist note. `null` when no writeup is attached.
- `odds`: Optional `Odds` object with the game's over/under total. `null` when no book posted a total for this game — see `Odds` below for how to tell that apart from a pipeline failure.

### `Forecast`

Represents the weather for one hour or the point-in-time snapshot at kickoff.

```json
{
  "start_time_utc": "2026-09-08T20:00:00Z",
  "temp_f": 68,
  "feels_like_f": 66,
  "wind_speed_mph": 12,
  "wind_deg": 220,
  "gust_mph": 18,
  "precip_pct": 20,
  "precip_type": "none",
  "short_forecast": "Partly Cloudy",
  "humidity_pct": 55,
  "dew_point_f": 52,
  "is_kickoff_hour": true
}
```

**Field notes:**

- `start_time_utc`: ISO 8601 UTC. The hour this forecast represents (top-of-hour).
- `temp_f`: Fahrenheit. **Rounded to integer at API boundary. Do not re-round.**
- `feels_like_f`: Fahrenheit. `null` if not provided by upstream.
- `wind_speed_mph`: Miles per hour. Integer.
- `wind_deg`: **Direction wind is COMING FROM. Meteorological convention. Integer 0-359.** `0` = wind from North (blowing south). `90` = wind from East. `180` = wind from South. `270` = wind from West. **To display an arrow showing the direction wind is BLOWING TOWARD, use `(wind_deg + 180) % 360`.** This is the exact field that has bitten us before — treat it as the highest-risk field in the contract.
- `gust_mph`: Miles per hour, or `null` when upstream provides no gust value. **`null` means "no data," not "zero gusts."** OVERcast's impact engine should distinguish these cases.
- `precip_pct`: Integer 0-100. Probability of measurable precipitation during this hour.
- `precip_type`: One of `"none" | "rain" | "snow" | "mix" | "freezing"`. Structured category derived by MSW from upstream `short_forecast` text + temperature so consumers do not have to re-parse the text. Rules: `"none"` when `precip_pct < 10`. `"freezing"` when short_forecast mentions freezing rain, freezing drizzle, or sleet/ice pellets. `"mix"` when both rain and snow keywords appear or the text says "wintry mix" or "rain/snow." `"snow"` when only snow keywords appear. `"rain"` when only rain/shower/drizzle/thunderstorm keywords appear. If short_forecast is vague but precip_pct is elevated, temperature-based fallback: ≤28°F → snow, 28-33°F → mix, else rain.
- `short_forecast`: Upstream provider's short text description ("Partly Cloudy", "Thunderstorms Likely"). May be present even when other fields are unavailable. Human-readable only — do not parse for logic (use `precip_type` for the structured category instead).
- `humidity_pct`: Integer 0-100 or `null`.
- `dew_point_f`: Fahrenheit or `null`.
- `is_kickoff_hour`: Only meaningful in the `hourly` array. `true` on the entry whose hour contains `kickoff_utc`. `false` on all others. Use to highlight the kickoff-hour column in a display.

### `Team`

```json
{
  "team_id": 12,
  "name": "Kansas City Chiefs",
  "short": "Chiefs",
  "abbrev": "KC",
  "conf": "AFC",
  "logo_url": "https://a.espncdn.com/i/teamlogos/nfl/500/12.png"
}
```

- `team_id`: ESPN team ID.
- `conf`: For NFL, `"AFC"` or `"NFC"`. For CFB, one of `"SEC" | "B1G" | "ACC" | "B12" | "AAC" | "MWC" | "SBC" | "CUSA" | "MAC" | "IND"`.

### `Venue`

```json
{
  "name": "Arrowhead Stadium",
  "city": "Kansas City, MO",
  "lat": 39.0489,
  "lon": -94.4839,
  "timezone": "America/Chicago",
  "roof_type": "open",
  "capacity": 76416,
  "nws_unsupported": false,
  "country": "US",
  "field_bearing_degrees": 135
}
```

- `roof_type`: One of `"open" | "retractable" | "fixed_dome" | "fixed_canopy"`. For fixed_dome venues, `forecast_at_kickoff` is always `null` and `weather_source: "indoor-skip"`.
- `field_bearing_degrees`: Integer 0-359, or `null`. The compass bearing the field runs, endzone to endzone. `0` = a north/south field, `90` = east/west. Either endzone is a valid reference, so `0` and `180` describe the same field — normalize with `% 180` if you need a canonical axis.

  Field-relative wind, given `wind_deg` (which is the direction wind comes FROM):

  ```
  wind_to  = (wind_deg + 180) % 360
  relative = (wind_to - field_bearing_degrees + 90) % 360
  ```

  `relative` near 0 or 180 is a crosswind; near 90 or 270 the wind runs along the field axis (the kicking-relevant case).

  **`null` means UNKNOWN, not "no wind" — do not coerce it to 0.** Two distinct cases, distinguishable via `roof_type`:
  - `roof_type: "fixed_dome"` — null is correct and permanent. There is no wind.
  - Any other `roof_type` — genuinely unmeasured. Skip the wind-relative feature for this game rather than defaulting it.

  Coverage as of 2026-09-01: all 134 CFB home venues are populated (minus 3 fixed domes). 13 neutral-site venues — AT&T, Mercedes-Benz, State Farm, Chase Field, SoFi, Croke Park, Aviva, Wembley, Allianz, Azteca, Fenway, Wrigley, Levi's — are still null. That set includes the Chick-fil-A Kickoff and Red River sites, so the null path is live traffic, not a rare edge case.
- `nws_unsupported`: `true` for international NFL venues (Tottenham, Estadio Azteca, etc.) that route through WeatherAPI directly. HRRR is also skipped for these.
- `country`: `"US"` or ISO 3166-1 alpha-2 code for international venues.

### `Odds`

```json
{
  "total_current": 44.5,
  "total_opening": 47.0,
  "delta": -2.5,
  "book": "DraftKings",
  "book_key": "draftkings",
  "frozen": true
}
```

- `total_current`: The total MSW is currently displaying. Before kickoff this is the live number; after kickoff it is the frozen closing line (see `frozen`).
- `total_opening`: The first total MSW ever recorded for this game. Immutable once written — it is never overwritten, so it is a true opener rather than "the oldest number still in cache."
- `delta`: `total_current - total_opening`, rounded to 2 decimals. `null` when no opening was captured (game first seen after it started).
- `book`, `book_key`: Which sportsbook the number came from. MSW picks one book per game by priority, so `book` can differ between games in the same slate and can change between polls if a book drops the market.
- `frozen`: `true` once kickoff has passed. **This matters.** The Odds API serves LIVE in-game totals after kickoff, and MSW only polls every 25 minutes, so that live number is stale garbage between cycles. MSW snapshots the last pre-kickoff total and serves that for the rest of the game. So `total_current` where `frozen: true` is a genuine closing line suitable for CLV work — not a mid-game number.

  One exception: if MSW first saw the game *after* it had already started, no snapshot exists and `total_current` falls back to the live total. Detect via `frozen: true` with `total_opening: null`.

**`odds: null` is normal.** Books do not price every game — low-major CFB especially. Do not treat null as a failure; check `meta.odds` instead.

### `Meta`

```json
{
  "built_at_utc": "2026-09-08T15:30:12Z",
  "next_refresh_at_utc": "2026-09-08T15:55:12Z",
  "etag": "sha256:9f2a...",
  "api_version": "v1",
  "odds": {
    "ok": true,
    "error": null,
    "updated_utc": "2026-09-08T15:30:09Z",
    "game_count": 61
  }
}
```

- `built_at_utc`: When MSW's underlying warmer last successfully refreshed this data.
- `next_refresh_at_utc`: When MSW's next warmer cycle is scheduled. Clients should time their next poll for shortly after this timestamp.
- `etag`: SHA-256 hash of the response content. Send back on subsequent requests as `If-None-Match: <etag>`. MSW returns `304 Not Modified` with empty body if unchanged.
- `api_version`: Always `"v1"` in this contract.
- `odds`: Odds-pipeline health for this sport. Present on slate and game endpoints. This is how you tell "no book priced that game" (`Game.odds: null` while `ok: true`) from "MSW's odds fetch is broken" (`ok: false`) — only the second is a reason to fall back to your own odds source.
  - `ok`: `true` fetch succeeded, `false` it failed, `null` this MSW instance has not attempted a fetch yet (freshly booted, serving a warm-boot slate). Treat `null` as unknown, not down.
  - `error`: `null` on success, else a short diagnostic string (e.g. `"HTTPError: 429"`).
  - `updated_utc`: When the last odds fetch attempt completed. Distinct from `built_at_utc`, though usually within seconds of it.
  - `game_count`: How many games came back priced from that fetch, across the whole sport — not the count in this response.
  - **NFL caveat:** an empty upstream payload reports `ok: true, game_count: 0`. NFL odds share a schedule fetch that swallows its own errors, so a real outage is indistinguishable from the legitimately empty offseason. Sustained `game_count: 0` during the season is the signal worth alerting on, not `ok: false`.

### `Writeup`

```json
{
  "text": "Cold front sweeping through around kickoff, expect gusty 30+ winds...",
  "color": "orange",
  "updated_at_utc": "2026-09-07T14:20:00Z"
}
```

- `color`: `null` or one of `"green" | "yellow" | "orange" | "red"` — Kevin's severity coding.

## `weather_source` values

Describes the upstream provider path that filled the forecast:

- `"nws"` — NWS gridpoint hourly forecast (US venues, primary path).
- `"weatherapi-fallback"` — WeatherAPI.com used because NWS failed or was circuit-broken (US venues).
- `"weatherapi-international"` — WeatherAPI.com used directly because venue is outside NWS coverage (international games).
- `"indoor-skip"` — Fixed dome venue; no upstream fetch attempted. `forecast_at_kickoff` is `null`.
- `"no-venue-data"` — Venue lat/lon unavailable. Rare, should not happen once venue coverage is complete.
- `"all-failed"` — All upstream providers returned errors. `forecast_at_kickoff` is `null`.

## Polling recommendation

- **Base cadence:** every 5 minutes as a safety net.
- **Smart cadence:** after receiving a response, schedule the next poll for `max(now + 60s, meta.next_refresh_at_utc + 30s)`. The 30s buffer guarantees MSW's warmer has completed its next cycle before you fetch.
- **Send ETag on subsequent polls:** `If-None-Match: <etag from previous response>`. MSW returns `304 Not Modified` when unchanged — cheap, no forecast payload to parse.
- **Kickoff freeze:** once a game shows `is_frozen: true`, drop that game to a low-poll cadence (every 30 min) since the values are locked. Snap back to standard cadence when `is_frozen` returns to `false` (past the release window, though this is rare — games are usually finalized by then).

## Fallback contract when MSW is unreachable

OVERcast must NOT fall back to a direct NWS or WeatherAPI or HRRR call. That reintroduces the exact mismatch this API exists to eliminate.

Instead, OVERcast should:

1. Serve the last successfully received MSW response.
2. Label it with an "as of HH:MM UTC" stamp in the UI so the user knows the data is stale.
3. Continue polling MSW at the standard cadence — retry, not backoff hard, so recovery is fast when MSW returns.

If MSW is up but its own upstream fetches failed (`weather_source: "all-failed"`), MSW returns 200 with `forecast_at_kickoff: null`. OVERcast should treat this as "no forecast available yet" and continue displaying its last-cached forecast for that game, with the "as of HH:MM" label.

## Conventions summary (highest-risk fields locked)

- **Wind direction (`wind_deg`)** — direction wind is COMING FROM. Meteorological. `0` = from North. Arrow display: `(wind_deg + 180) % 360`.
- **All timestamps** — ISO 8601 UTC with `Z` suffix. Never local timezones in payload except display-only `kickoff_local_str`.
- **Temperature** — Fahrenheit.
- **Wind speed / gusts** — miles per hour.
- **Precip probability, humidity** — integer 0-100.
- **Missing data** — `null`, not zero. `null` means "no data reported," not "zero."
- **Rounding** — MSW rounds to integers at API boundary. Consumers should not re-round.

## Change log

- 2026-07-04 — Initial draft.
- 2026-07-04 — Added `precip_type` enum to Forecast per OVERcast AI feedback. MSW derives the category once so consumers don't re-parse `short_forecast` text.
- 2026-07-04 — Contract signed off by MSW + OVERcast. API implementation in progress.
- 2026-09-01 — Added `Game.odds` (O/U total, opener, delta, book, kickoff freeze) and `Meta.odds` (pipeline health). Additive only — existing fields unchanged, so v1 consumers need no changes to keep working. Lets OVERcast drop its own Odds API calls.
- 2026-09-01 — Added `Venue.field_bearing_degrees` for field-relative wind. All CFB home venues populated; 13 neutral-site venues still `null`. Additive only.


{# EOF-CANARY 2026-07-04-api-contract-draft #}
