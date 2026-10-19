# MySportsWeather Forecast Embed (v1)

A per-game weather card you can drop into an article with an iframe. It shows
the kickoff temperature, wind (with a diagram of the wind direction relative
to the field) and rain chance. It updates on its own, so an article written
days ahead still shows the latest forecast when someone reads it.

No API key is needed for the embed.

## Embed code

The easiest way to get it is the picker (below), which fills everything in.
The code looks like this, with the game's URL in both places:

```html
<iframe src="https://mysportsweather.com/embed/nfl/2026-10-25/hou-jax"
        title="Weather forecast for this game"
        width="100%" height="360" loading="lazy"
        style="border:0;max-width:640px;display:block"></iframe>
<p>Weather forecast by <a href="https://mysportsweather.com/nfl/2026-10-25/hou-jax">MySportsWeather</a></p>
<script>window.addEventListener("message",function(e){if(e.origin!=="https://mysportsweather.com"||!e.data||!e.data.msw_embed_height)return;document.querySelectorAll('iframe[src^="https://mysportsweather.com/embed/"]').forEach(function(f){if(f.contentWindow===e.source)f.style.height=e.data.msw_embed_height+"px";});});</script>
```

- **The iframe** is the card.
- **The line under it** is the required attribution. Keep the link text as
  "MySportsWeather" and point it at the same game's page.
- **The script** is optional. It shrinks the iframe to fit the card exactly
  (about 205 px tall on desktop). If your CMS strips scripts, leave it out and
  the card sits in the fixed 360 px box, which fits it on any screen size.
  Several cards on one page is fine.

## Finding a game's embed code

Three ways:

1. **For writers: the embed picker.** Go to
   **https://mysportsweather.com/embed**, pick NFL or College Football, find
   the game and click **Copy embed code**. It copies everything above, ready
   to paste. There's a Preview button too.
2. **From the website.** Open the game's forecast page and add `/embed` after
   the domain:
   - Page: `https://mysportsweather.com/nfl/2026-10-25/hou-jax`
   - Embed: `https://mysportsweather.com/embed/nfl/2026-10-25/hou-jax`
3. **For developers: the Partner API.** Every game includes `page_url` and
   `embed_url`.

URL format:

| Sport | Embed URL |
|---|---|
| NFL | `/embed/nfl/{YYYY-MM-DD}/{game-slug}` |
| College football | `/embed/ncaaf/{YYYY-MM-DD}/{game-slug}` |

The date is the game's date in Eastern time (NFL) or local time (college).

## Sizing

- The card is responsive up to 640 px wide. Use `width="100%"`.
- Desktop: about 205 px tall. Phones: about 295 px, because the stats stack
  two across.

## What the card shows

| Situation | Card |
|---|---|
| Forecast available | Kickoff temperature, field wind diagram, wind speed (with gusts when notable), rain or snow chance at kickoff |
| Retractable roof | The outdoor forecast, with "Retractable roof" next to the stadium name |
| Domed stadium | A note that weather won't affect the game |
| Too far out | "Forecast isn't posted yet." Games appear about a week before kickoff |
| Game is over | A link to the current slate of forecasts |

The field diagram shows the wind blowing across or along the actual field,
using each stadium's measured orientation. It's left off for the few
stadiums we haven't measured.

All times on the card are Eastern. Forecasts refresh through the day and lock
in shortly before kickoff.

## Permitted use

Same terms as the Partner API: inside your articles and previews, with the
attribution line. Please don't build a standalone weather page out of embeds.

## Contact

Kevin Roth: kevinrothwx@gmail.com
