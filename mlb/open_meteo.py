"""
DEPRECATED — replaced by mlb/weatherapi.py on June 8, 2026.

We switched from Open-Meteo to WeatherAPI.com because:
  1. Kevin already has a WeatherAPI account in use elsewhere.
  2. WeatherAPI returns more consistent data shapes globally.
  3. Single provider for all international venues reduces maintenance.

If you see this file in the repo, you can safely delete it.
"""
raise ImportError(
    "mlb.open_meteo is deprecated — use mlb.weatherapi instead. "
    "See file header for migration notes."
)
