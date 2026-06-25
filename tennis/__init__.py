"""tennis — Grand Slam tournament auto-forecast.

4 hard-coded Slam venues, each with a fixed annual ~14-day window:
  - Australian Open (Melbourne, AU)
  - French Open / Roland Garros (Paris, FR)
  - Wimbledon (London, GB)
  - US Open (NYC, US)

Card auto-shows during an active Slam, hides between. No manual writeups —
this is a SEO/coverage product, not a Kevin-commentary product (per Kevin's
explicit scoping: "automate it, pop it up during majors, take it down when
there are no majors running"). For the same reason, no storage.py / admin.

Mirrors the golf/ module pattern for daily hourly forecasts, plus the
worldcup/ international-venue handling (WeatherAPI fallback for non-CONUS
venues since NWS doesn't cover them).
"""
