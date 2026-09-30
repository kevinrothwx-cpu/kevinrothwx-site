# MySportsWeather Partner API (v1)

Hourly, stadium-level game forecasts for the NFL and college football, from
MySportsWeather.com (Kevin Roth, sports meteorologist).

## Access

- Base URL: `https://mysportsweather.com/api/partner/v1`
- Send your key in a header on every request: `X-API-Key: <your key>`
- Call it from your server, not from browser JavaScript. A key in page
  JavaScript is visible to anyone.

## Endpoints

| Method | Path | What it returns |
|---|---|---|
| GET | `/nfl/slate` | Every game on this week's NFL slate |
| GET | `/cfb/slate` | Every FBS game on this week's college slate |
| GET | `/health` | Quick status check. No key needed |

## Refresh and limits

- Forecasts rebuild about every 25 minutes. `meta.next_refresh_at_utc` says
  when the next rebuild is due. Polling every 15 to 30 minutes is plenty.
- 30 requests per minute per key.
- Every response has an `ETag`. Send it back as `If-None-Match` and you get a
  fast `304 Not Modified` when nothing has changed.

## Attribution (required)

Wherever the data appears, show **"Weather by MySportsWeather.com"** linked to
the URL in `attribution.url`:

- NFL: `https://mysportsweather.com/nfl`
- College football: `https://mysportsweather.com/ncaaf`

## Example response (`/nfl/slate`, trimmed to two games)

```json
{
  "attribution": {
    "text": "Weather by MySportsWeather.com",
    "url": "https://mysportsweather.com/nfl",
    "required": true
  },
  "games": [
    {
      "event_id": "example-event-id",
      "sport": "nfl",
      "week": null,
      "away": { "name": "New England Patriots", "abbrev": "NE" },
      "home": { "name": "Buffalo Bills", "abbrev": "BUF" },
      "kickoff_utc": "2026-10-04T17:00:00Z",
      "venue": {
        "name": "Highmark Stadium",
        "city": "Orchard Park, NY",
        "country": "US",
        "lat": 42.77,
        "lon": -78.79,
        "timezone": "America/New_York",
        "roof_type": "open"
      },
      "forecast_status": "ok",
      "kickoff_forecast": {
        "time_utc": "2026-10-04T17:00:00Z",
        "temp_f": 66,
        "wind_mph": 6,
        "wind_dir": "SW",
        "wind_deg": 225,
        "gust_mph": 10,
        "precip_pct": 33,
        "precip_type": "rain",
        "conditions": "Chance Showers And Thunderstorms"
      },
      "game_max_precip_pct": 33,
      "hourly": [
        {
          "time_utc": "2026-10-04T17:00:00Z",
          "temp_f": 66,
          "wind_mph": 6,
          "wind_dir": "SW",
          "wind_deg": 225,
          "gust_mph": 10,
          "precip_pct": 33,
          "precip_type": "rain",
          "conditions": "Chance Showers And Thunderstorms",
          "in_game": true
        }
      ]
    },
    {
      "event_id": "example-event-id-2",
      "sport": "nfl",
      "week": null,
      "away": { "name": "Miami Dolphins", "abbrev": "MIA" },
      "home": { "name": "Minnesota Vikings", "abbrev": "MIN" },
      "kickoff_utc": "2026-10-04T20:05:00Z",
      "venue": {
        "name": "U.S. Bank Stadium",
        "city": "Minneapolis, MN",
        "country": "US",
        "lat": 44.97,
        "lon": -93.26,
        "timezone": "America/Chicago",
        "roof_type": "fixed_dome"
      },
      "forecast_status": "indoor",
      "kickoff_forecast": null,
      "game_max_precip_pct": null,
      "hourly": []
    }
  ],
  "meta": {
    "built_at_utc": "2026-09-30T19:43:34Z",
    "next_refresh_at_utc": "2026-09-30T20:08:34Z",
    "etag": "sha256:...",
    "api_version": "partner-v1"
  }
}
```

## Field notes

- **`forecast_status`**
  - `ok`: forecast included.
  - `indoor`: fixed dome. No forecast, because weather has no effect.
  - `unavailable`: no forecast right now (too far out, or a temporary data
    problem). Try again on the next refresh.
- **`kickoff_forecast`**: the kickoff hour. Its `precip_pct` is the chance of
  rain at kickoff.
- **`game_max_precip_pct`**: the highest rain chance during the game hours.
  Often higher than the kickoff number when rain moves in mid-game.
- **`hourly`**: one hour before kickoff through four hours after. `in_game`
  marks the hours the game is being played.
- **Wind**: `wind_mph` is sustained wind, `gust_mph` is gusts (can be null,
  and is always null for games outside the US).
  `wind_dir` is the compass direction the wind blows *from* (16 points,
  e.g. `SW`); `wind_deg` is the same in degrees. Both are null when the wind
  is calm and has no direction.
- **`precip_type`**: `none`, `rain`, `snow`, `mix` or `freezing`.
- **`roof_type`**: `open`, `retractable`, `fixed_canopy` or `fixed_dome`. For
  `retractable`, the forecast is the outdoor weather; the roof may be closed.
- **Units and times**: °F, mph, percent. All times are UTC, ISO 8601.
- **`week`**: college football only. Null for the NFL.
- **Slate window**: games appear about a week ahead and drop off the day after
  they are played. Forecasts lock in shortly before kickoff.
- Field order in responses is not significant.

## Errors

| Status | Meaning |
|---|---|
| 401 | Missing or wrong `X-API-Key` |
| 429 | Over 30 requests per minute. Wait `retry_after_seconds` |
| 503 | Partner API temporarily disabled |

## Contact

Kevin Roth: kevinrothwx@gmail.com
