"""
overcast_impact.py — OVERcast CWS weather-impact strip for kevinrothwx.com/cws.

WHAT IT IS
  A drop-in module that turns a single game's forecast into the OVERcast
  "weather impact" strip (Runs / Home runs / Strikeouts vs the park's CWS
  history) that sits under each game's hourly forecast.

HOW TO USE  (this is the entire integration)
  1. Copy this file + games_clean_cws.csv into the site project.
  2. For each upcoming CWS game, call:

        from overcast_impact import render_impact_strip
        html = render_impact_strip(temp=85, dew=55, wind_mph=10, wind_dir_deg=180)

     and drop `html` into the page right under that game's hourly forecast.

  PASS THE SAME FORECAST THE PAGE ALREADY SHOWS (first-pitch temp, dewpoint,
  wind speed, wind direction in degrees). That keeps the strip and the grid
  above it in agreement, do NOT pull a second forecast.

NOTES
  - Standard library only. CF bearing = 135 (verified on satellite).
  - Runs use the full park history (2011-present); home runs & strikeouts use
    box scores from 2023 on (a smaller, shared sample). Each tile shows its own n.
  - No Over/Under, no cross-park comparison. Baseline = the average across all
    College World Series games at Charles Schwab Field.
  - wind_dir_deg is meteorological "from" degrees: 0=N, 90=E, 180=S, 270=W.
    If you only have a compass label, see COMPASS_TO_DEG at the bottom.
"""
import csv, os, functools

CF_BEARING   = 135
BASE_TOL     = {"temp": 9.0, "wind": 6.0, "dew": 20.0}
EXP_TOL      = {"temp": 11.0, "wind": 8.0, "dew": 23.0}
WIND_OFFSET  = 2.0          # NWS reads ~2 mph high vs in-stadium; matching only
SHRINK_K     = 4
CSV_PATH     = os.path.join(os.path.dirname(__file__), "games_clean_cws.csv")

# (csv column, display label, coverage note)
STATS = [("R", "Runs", "2011-present"),
         ("HR", "Home runs", "2023+"),
         ("K", "Strikeouts", "2023+")]
_C16 = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]

# ---------------- wind ----------------
def _angle_diff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)

def _bucket(wind_from, cf=CF_BEARING):
    if _angle_diff(wind_from, (cf + 180) % 360) <= 50: return "out"
    if _angle_diff(wind_from, cf) <= 45: return "in"
    return "cross"

def _wind_phrase(wind_from, cf=CF_BEARING):
    """('blowing in from right field', 'suppresses', 'in') for the prose line."""
    b = _bucket(wind_from, cf)
    delta = ((wind_from - cf + 180) % 360) - 180
    side = "right field" if delta > 0 else "left field"
    to   = "left field" if delta > 0 else "right field"
    if b == "in":
        where = "blowing in from center" if abs(delta) <= 22.5 else f"blowing in from {side}"
        return where, "suppresses", b
    if b == "out":
        where = "blowing out to center" if abs(abs(delta) - 180) <= 22.5 else f"blowing out toward {to}"
        return where, "boosts", b
    return "crossing the field", "has a mixed effect on", b

def _wind_lead(mph):
    """Speed-aware lead-in adjective so light vs strong winds produce different prose."""
    n = int(round(mph))
    if mph < 5:  return f"A calm {n} mph wind"
    if mph < 9:  return f"A light {n} mph wind"
    if mph < 14: return f"A steady {n} mph wind"
    if mph < 19: return f"A brisk {n} mph wind"
    return f"A strong {n} mph wind"

def _effect_tail(mph, effect):
    """Pair the historical-effect verb with a strength modifier matched to wind speed."""
    if "mixed" in effect:
        return f"historically {effect} scoring at Charles Schwab Field"
    if mph < 5:
        return f"historically {effect} scoring only marginally at Charles Schwab Field"
    if mph < 9:
        return f"historically {effect} scoring modestly at Charles Schwab Field"
    if mph < 19:
        return f"historically {effect} scoring at Charles Schwab Field"
    return f"historically {effect} scoring meaningfully at Charles Schwab Field"

# ---------------- engine ----------------
def _num(v):
    try: return float(v)
    except (TypeError, ValueError): return None

@functools.lru_cache(maxsize=4)
def _load_pool(path):
    pool = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            t, d, w, di = _num(r.get("temp")), _num(r.get("dew")), _num(r.get("wind")), _num(r.get("dir"))
            if t is None or di is None or w is None:
                continue
            pool.append({"temp": t, "dew": d, "wind": w, "dir": di, "bucket": _bucket(di),
                         "R": _num(r.get("R")), "HR": _num(r.get("HR")), "K": _num(r.get("K"))})
    return tuple(pool)

def _baseline(pool, stat):
    vals = [g[stat] for g in pool if g[stat] is not None]
    return (sum(vals) / len(vals), len(vals)) if vals else (None, 0)

def _fmt_pct(x):
    r = round(x)
    if r == 0 and x != 0: return 1 if x > 0 else -1
    return int(r)

def _score(pool, stat, temp, dew, wind, wdir):
    b = _bucket(wdir)
    mw = max(0.0, wind - WIND_OFFSET)
    base, _ = _baseline(pool, stat)
    if base is None:
        return {"pct": None, "n": 0, "sim": None, "base": None}
    def match(tol):
        out = []
        for g in pool:
            if g["bucket"] != b or g[stat] is None:
                continue
            dt, dw, dd = abs(g["temp"] - temp), abs(g["wind"] - mw), abs(g["dew"] - dew)
            if dt <= tol["temp"] and dw <= tol["wind"] and dd <= tol["dew"]:
                ang = _angle_diff(g["dir"], wdir)
                dist = 0.4*dt/tol["temp"] + 0.3*dw/tol["wind"] + 0.2*dd/tol["dew"] + 0.2*ang/180
                out.append((g, 1.0 / (1.0 + dist)))
        return out
    m = match(BASE_TOL)
    if len(m) < 15:
        m2 = match(EXP_TOL)
        if len(m2) > len(m): m = m2
    n = len(m)
    if n == 0:
        return {"pct": None, "n": 0, "sim": None, "base": round(base, 1)}
    wsum = sum(w for _, w in m)
    sim = sum(g[stat] * w for g, w in m) / wsum
    shrunk = base + (n / (n + SHRINK_K)) * (sim - base)
    return {"pct": _fmt_pct((shrunk / base - 1) * 100), "n": n,
            "sim": round(shrunk, 1), "base": round(base, 1)}

def compute_impact(temp, dew, wind_mph, wind_dir_deg, csv_path=CSV_PATH):
    """Return {'R':{...}, 'HR':{...}, 'K':{...}} for callers that want to render their own."""
    pool = _load_pool(csv_path)
    return {col: _score(pool, col, temp, dew, wind_mph, wind_dir_deg) for col, _, _ in STATS}

# ---------------- render ----------------
def _tile(label, unit, res, coverage, hero):
    width = "1.5fr" if hero else "1fr"
    if not res or res.get("pct") is None:
        body = '<div style="font-size:13px;color:#9ca3af;font-style:italic;margin-top:10px;">building, not enough data yet</div>'
        return f'<div style="border:1px solid #e5e7eb;border-radius:12px;padding:16px;background:#fff;"><div style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:#6b7280;font-weight:600;white-space:nowrap;">{label}</div>{body}</div>'
    pct = res["pct"]
    color = "#16a34a" if pct > 0 else ("#dc2626" if pct < 0 else "#6b7280")
    sign = "+" if pct > 0 else ("−" if pct < 0 else "")
    val = str(abs(pct)) if pct < 0 else str(pct)
    return (f'<div style="border:1px solid #e5e7eb;border-radius:12px;padding:16px;background:#fff;">'
            f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:#6b7280;font-weight:600;white-space:nowrap;">{label}</div>'
            f'<div style="font-size:32px;font-weight:700;color:{color};line-height:1.1;margin-top:6px;">{sign}{val}%</div>'
            f'<div style="font-size:12.5px;margin-top:8px;line-height:1.7;white-space:nowrap;">'
            f'<span style="color:#374151;font-weight:600;">{res["sim"]}</span> <span style="color:#9ca3af;">{unit} in this weather</span><br>'
            f'<span style="color:#374151;font-weight:600;">{res["base"]}</span> <span style="color:#9ca3af;">Omaha CWS avg</span></div>'
            f'<div style="font-size:11px;color:#9ca3af;margin-top:12px;white-space:nowrap;">{res["n"]} games &middot; {coverage}</div>'
            f'</div>')

def render_impact_strip(temp, dew, wind_mph, wind_dir_deg, csv_path=CSV_PATH):
    """Return the OVERcast impact strip as an HTML string for one game."""
    results = compute_impact(temp, dew, wind_mph, wind_dir_deg, csv_path)
    where, effect, _ = _wind_phrase(wind_dir_deg)
    lead = _wind_lead(wind_mph)
    tail = _effect_tail(wind_mph, effect)
    tiles = "".join(_tile(lbl, "/gm", results.get(col), cov, hero=(col == "R"))
                    for col, lbl, cov in STATS)
    return f'''<div style="max-width:860px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#111827;">
  <div style="border-top:1px solid #e5e7eb;padding-top:16px;display:flex;align-items:baseline;justify-content:space-between;">
    <div style="font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:#6b7280;font-weight:600;">Weather impact &middot; vs CWS history at Omaha</div>
    <div style="font-size:12px;color:#9ca3af;font-weight:600;letter-spacing:.04em;">OVER<span style="color:#0ea5e9;">cast</span></div>
  </div>
  <div style="margin:12px 0 16px;font-size:15px;color:#374151;line-height:1.5;">
    {lead}, <strong style="color:#111827;">{where}</strong>, which {tail}.
  </div>
  <div style="display:grid;grid-template-columns:1.5fr 1fr 1fr;gap:12px;align-items:start;">{tiles}</div>
  <div style="font-size:11.5px;color:#9ca3af;margin-top:14px;line-height:1.5;">
    Baseline is the average across all College World Series games at Charles Schwab Field. Runs span every CWS here (2011-present); home runs &amp; strikeouts use box scores from 2023 on, a smaller shared sample that deepens each June.
  </div>
</div>'''

# Pass wind_dir_deg in degrees. If you only have a compass label, map it:
COMPASS_TO_DEG = {"N":0,"NNE":23,"NE":45,"ENE":68,"E":90,"ESE":113,"SE":135,"SSE":158,
                  "S":180,"SSW":203,"SW":225,"WSW":248,"W":270,"WNW":293,"NW":315,"NNW":338}

if __name__ == "__main__":
    # quick self-check with tonight's Ole Miss @ UNC forecast
    print(render_impact_strip(temp=85, dew=55, wind_mph=10, wind_dir_deg=180)[:600])
