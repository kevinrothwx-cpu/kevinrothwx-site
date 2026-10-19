# MySportsWeather Forecast Embed (v1)

A per-game weather card you can drop into an article with an iframe. It shows
the kickoff temperature, wind, rain chance and an hour-by-hour strip for the
game window. It updates on its own, so an article written days ahead still
shows the latest forecast when someone reads it.

No API key is needed for the embed.

## Embed code

Paste this where the card should appear, with the game's URL in both places:

```html
<iframe src="https://mysportsweather.com/embed/nfl/2026-10-25/hou-jax"
        title="Weather forecast for this game"
        width="100%" height="540" loading="lazy"
        style="border:0;max-width:640px;display:block"></iframe>
<p>Weather forecast by <a href="https://mysportsweather.com/nfl/2026-10-25/hou-jax">MySportsWeather</a></p>
```

The line under the iframe is the required attribution. Keep the link text as
"MySportsWeather" and point it at the same game's page.

## Finding a game's embed URL

Three ways:

1. **For writers: the embed picker.** Go to
   **https://mysportsweather.com/embed**, pick NFL or College Football, find
   the game and click **Copy embed code**. It copies the iframe and the
   attribution line together, ready to paste. There's a Preview button too.
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
- The card is about 410 px tall on desktop and up to about 540 px on narrow
  phones. A fixed `height="540"` is always safe but leaves blank space on
  desktop.
- **Optional auto-height.** The card reports its own height to the parent
  page. Add this once per page and every card resizes to fit:

```html
<script>
window.addEventListener("message", function (e) {
  if (e.origin !== "https://mysportsweather.com" || !e.data || !e.data.msw_embed_height) return;
  document.querySelectorAll('iframe[src^="https://mysportsweather.com/embed/"]').forEach(function (f) {
    if (f.contentWindow === e.source) f.style.height = e.data.msw_embed_height + "px";
  });
});
</script>
```

## What the card shows

| Situation | Card |
|---|---|
| Forecast available | Kickoff temperature, wind (with gusts when notable), rain chance, highest rain chance during the game, hourly strip |
| Retractable roof | The outdoor forecast, with a note that the roof may be closed |
| Domed stadium | A note that weather won't affect the game |
| Too far out | "Forecast isn't posted yet." Games appear about a week before kickoff |
| Game is over | A link to the current slate of forecasts |

All times on the card are Eastern. Forecasts refresh through the day and lock
in shortly before kickoff.

## Permitted use

Same terms as the Partner API: inside your articles and previews, with the
attribution line. Please don't build a standalone weather page out of embeds.

## Contact

Kevin Roth: kevinrothwx@gmail.com
