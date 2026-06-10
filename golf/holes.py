"""
golf.holes — per-hole course geometry from OpenStreetMap.

Fetches `golf=hole` ways around each course's lat/lon via the Overpass
API, caches the parsed geometry to static/data/course_holes/<slug>.json,
and prepares render-ready SVG coordinates for the course map macro.

Real-world OSM data is messy — validated against live data for Augusta,
Pinehurst, Pebble Beach, and TPC Sawgrass:
  - Multi-course facilities return duplicate hole numbers (Augusta's
    Par 3 Course, Sawgrass's Dye's Valley, Pebble's The Hay + MPCC).
  - Course identity shows up three different ways: a `golf:course:name`
    tag (Augusta), a ref suffix like "4 - #2" (Pinehurst), or a name
    prefix like "Stadium 4" (Sawgrass) — or not at all (Pebble).
  - Some holes are simply missing (Augusta 12, Sawgrass 13).
Selection strategy: group by course identity when present, pick the
group with the most distinct hole numbers, resolve remaining duplicates
by routing continuity (a hole's green should sit near the next tee),
then drop geographic outliers (e.g. a neighboring course's hole 10
masquerading as ours when our 10 isn't mapped).

Cache philosophy: course geometry never changes. The first request for a
course triggers one Overpass fetch; everything after reads the local
file. A fetch FAILURE is not cached to disk (we retry after a cool-down);
an EMPTY result is cached so unmapped courses don't hammer Overpass.

OSM data © OpenStreetMap contributors, ODbL.
"""

from __future__ import annotations

import json
import math
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import requests


OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_RADIUS_M = 800        # override per course via courses.py "osm_radius_m"
MIN_HOLES_FOR_MAP = 9         # don't render half-mapped courses
FETCH_FAIL_COOLDOWN_S = 3600  # wait an hour before retrying a failed fetch
OUTLIER_FLOOR_M = 1200        # never call a hole an outlier inside this radius

CACHE_DIR = Path(__file__).resolve().parent.parent / "static" / "data" / "course_holes"

_fetch_lock = threading.Lock()
_recent_failures: dict[str, float] = {}   # slug -> monotonic time of last failure


# ── Geometry helpers ──────────────────────────────────────────────────

def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial great-circle bearing from point 1 to point 2 (0–360, 0=N)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return math.degrees(math.atan2(x, y)) % 360


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in meters between two lat/lon points."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


_COMPASS_8 = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def _compass8(deg: float) -> str:
    return _COMPASS_8[int((deg + 22.5) % 360 // 45)]


def _midpoint(points: list) -> list:
    return points[len(points) // 2]


# ── OSM tag parsing ───────────────────────────────────────────────────

def _parse_num(tags: dict):
    """Hole number from ref ('7', '7 - #2') or name ('Stadium 7'). None if absent."""
    m = re.match(r"\s*(\d+)", tags.get("ref") or "")
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*$", tags.get("name") or "")
    return int(m.group(1)) if m else None


def _course_key(tags: dict) -> str:
    """
    Identity of the course a hole belongs to, normalized. Empty string
    when OSM gives us nothing to go on.
    """
    name = tags.get("golf:course:name")
    if name:
        return name.strip().lower()
    ref = tags.get("ref") or ""
    m = re.match(r"\s*\d+\s*(\D.*)$", ref)   # suffix must start non-digit ('10' is just a number)
    if m:
        return re.sub(r"^[-–—:\s]+", "", m.group(1)).strip().lower()
    m = re.match(r"^(.*\D)\s*\d+\s*$", tags.get("name") or "")
    if m and m.group(1).strip():
        return m.group(1).strip().lower()
    return ""


# ── Hole selection (the messy part) ───────────────────────────────────

def _pick_course_group(holes: list[dict], lat: float, lon: float) -> list[dict]:
    """Group holes by course identity; keep the most complete course."""
    groups: dict[str, list[dict]] = {}
    for h in holes:
        groups.setdefault(h["_key"], []).append(h)

    def group_rank(item):
        key, hs = item
        distinct = len({h["num"] for h in hs})
        total_d = sum(
            haversine_m(*_midpoint(h["points"]), lat, lon) for h in hs
        )
        return (-distinct, total_d)

    return sorted(groups.items(), key=group_rank)[0][1]


def _filter_candidates(holes: list[dict], lat: float, lon: float) -> list[dict]:
    """
    Pre-filter implausible candidates before duplicate resolution. The
    trusted skeleton is the median center of UNIQUE-numbered holes (median
    is robust to a minority of strays). Candidates far outside it are a
    neighboring course's holes — e.g. MPCC's 10/11 standing in for
    Pebble's unmapped ones, which would otherwise drag the routing chain
    toward the wrong course.
    """
    counts: dict[int, int] = {}
    for h in holes:
        counts[h["num"]] = counts.get(h["num"], 0) + 1
    unique_mids = [_midpoint(h["points"]) for h in holes if counts[h["num"]] == 1]

    if len(unique_mids) >= 3:
        center = (median(m[0] for m in unique_mids), median(m[1] for m in unique_mids))
        dists = [haversine_m(m[0], m[1], *center) for m in unique_mids]
        med_d = median(dists)
        mad = median(abs(d - med_d) for d in dists)
        threshold = max(OUTLIER_FLOOR_M, med_d + 3 * mad)
    else:
        center, threshold = (lat, lon), 2500.0

    kept = [
        h for h in holes
        if haversine_m(*_midpoint(h["points"]), *center) <= threshold
    ]
    return kept if len(kept) >= MIN_HOLES_FOR_MAP else holes


def _resolve_duplicates(holes: list[dict]) -> list[dict]:
    """
    One hole per number. When a number has several candidates (adjacent
    courses with bare numeric refs), choose the combination that keeps
    the routing coherent: minimize total green→next-tee distance via DP.
    """
    by_num: dict[int, list[dict]] = {}
    for h in holes:
        by_num.setdefault(h["num"], []).append(h)
    nums = sorted(by_num)
    if not nums:
        return []

    costs = [0.0] * len(by_num[nums[0]])
    back: list[list[int]] = []
    for k in range(1, len(nums)):
        prev_c, cur_c = by_num[nums[k - 1]], by_num[nums[k]]
        new_costs, bp = [], []
        for cj in cur_c:
            tee = cj["points"][0]
            options = [
                costs[i] + haversine_m(ci["points"][-1][0], ci["points"][-1][1],
                                       tee[0], tee[1])
                for i, ci in enumerate(prev_c)
            ]
            best = min(range(len(options)), key=options.__getitem__)
            new_costs.append(options[best])
            bp.append(best)
        costs, back = new_costs, back + [bp]

    pick = min(range(len(costs)), key=costs.__getitem__)
    chosen = [by_num[nums[-1]][pick]]
    for k in range(len(nums) - 2, -1, -1):
        pick = back[k][pick]
        chosen.append(by_num[nums[k]][pick])
    return chosen[::-1]


def _drop_outliers(holes: list[dict]) -> list[dict]:
    """
    Drop holes implausibly far from the course's median center — e.g. a
    neighboring course's hole picked up because ours isn't mapped.
    """
    if len(holes) < 12:
        return holes
    mids = [_midpoint(h["points"]) for h in holes]
    center = (median(m[0] for m in mids), median(m[1] for m in mids))
    dists = [haversine_m(m[0], m[1], *center) for m in mids]
    med_d = median(dists)
    mad = median(abs(d - med_d) for d in dists)
    threshold = max(OUTLIER_FLOOR_M, med_d + 3 * mad)
    kept = [h for h, d in zip(holes, dists) if d <= threshold]
    return kept if len(kept) >= MIN_HOLES_FOR_MAP else holes


# ── Overpass fetch + disk cache ───────────────────────────────────────

def course_cache_slug(canonical_name: str) -> str:
    """'Pinehurst Resort & Country Club' -> 'pinehurst-resort-country-club'."""
    return re.sub(r"[^a-z0-9]+", "-", canonical_name.lower()).strip("-")


def _overpass_query(lat: float, lon: float, radius_m: int) -> str:
    return (
        f'[out:json][timeout:25];'
        f'(way["golf"="hole"](around:{radius_m},{lat},{lon}););'
        f'out geom;'
    )


def parse_overpass_elements(elements: list, lat: float, lon: float) -> list[dict]:
    """Raw Overpass elements -> clean, selected, ordered hole list."""
    holes = []
    for el in elements:
        geom = el.get("geometry") or []
        tags = el.get("tags") or {}
        num = _parse_num(tags)
        if len(geom) < 2 or num is None:
            continue
        try:
            par = int(tags["par"]) if tags.get("par") else None
        except ValueError:
            par = None
        name = (tags.get("name") or "").strip()
        if re.fullmatch(r"(hole\s*)?\d+", name, re.I):
            name = ""   # 'Hole 7' adds nothing over the number
        holes.append({
            "num": num,
            "par": par,
            "name": name or None,
            "points": [[round(g["lat"], 6), round(g["lon"], 6)] for g in geom],
            "_key": _course_key(tags),
        })

    if holes:
        holes = _pick_course_group(holes, lat, lon)
        holes = _filter_candidates(holes, lat, lon)
        holes = _resolve_duplicates(holes)
        holes = _drop_outliers(holes)
    for h in holes:
        h.pop("_key", None)
    return sorted(holes, key=lambda h: h["num"])


def fetch_holes_from_osm(lat: float, lon: float, radius_m: int = DEFAULT_RADIUS_M) -> list[dict]:
    """Query Overpass for golf=hole ways near (lat, lon). Raises on HTTP failure."""
    resp = requests.post(
        OVERPASS_URL,
        data={"data": _overpass_query(lat, lon, radius_m)},
        headers={"User-Agent": "kevinrothwx.com course-map (kevinrothwx@gmail.com)"},
        timeout=30,
    )
    resp.raise_for_status()
    return parse_overpass_elements(resp.json().get("elements", []), lat, lon)


def get_course_holes(course_meta: dict) -> list[dict] | None:
    """
    Return the cached hole list for a course, fetching from Overpass on
    first use. Returns [] for a course confirmed unmapped on OSM, or None
    when geometry is unavailable right now (fetch failed; will retry later).
    """
    canon = course_meta.get("_canonical_name")
    if not canon:
        return None
    slug = course_cache_slug(canon)
    cache_file = CACHE_DIR / f"{slug}.json"

    def _read_cache():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))["holes"]
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    if cache_file.exists():
        cached = _read_cache()
        if cached is not None:
            return cached

    last_fail = _recent_failures.get(slug)
    if last_fail and (time.monotonic() - last_fail) < FETCH_FAIL_COOLDOWN_S:
        return None

    with _fetch_lock:
        if cache_file.exists():  # another thread won the race
            cached = _read_cache()
            if cached is not None:
                return cached
        try:
            radius = int(course_meta.get("osm_radius_m", DEFAULT_RADIUS_M))
            holes = fetch_holes_from_osm(course_meta["lat"], course_meta["lon"], radius)
        except Exception as e:
            _recent_failures[slug] = time.monotonic()
            print(f"[golf.holes] Overpass fetch failed for {canon}: {e}", flush=True)
            return None

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({
            "course": canon,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "openstreetmap-overpass",
            "license": "ODbL",
            "radius_m": radius,
            "holes": holes,
        }, indent=1), encoding="utf-8")
        _recent_failures.pop(slug, None)
        return holes


# ── SVG projection ────────────────────────────────────────────────────

SVG_CONTENT_MAX = 940.0   # longest dimension of the projected course
SVG_PAD = 48.0            # frame padding (room for labels + compass)


def prepare_course_map(holes: list[dict]) -> dict | None:
    """
    Project hole geometry into a north-up SVG coordinate space and compute
    per-hole bearing, yardage, and label position. Returns a dict the
    course_hole_map macro renders directly, or None if not enough holes.
    """
    holes = [h for h in holes if len(h.get("points", [])) >= 2]
    if len(holes) < MIN_HOLES_FOR_MAP:
        return None

    all_pts = [p for h in holes for p in h["points"]]
    lat0 = sum(p[0] for p in all_pts) / len(all_pts)
    k = math.cos(math.radians(lat0))  # shrink longitude at this latitude

    xs = [p[1] * k for p in all_pts]
    ys = [p[0] for p in all_pts]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    span = max(max_x - min_x, max_y - min_y) or 1e-9
    scale = SVG_CONTENT_MAX / span

    width = round((max_x - min_x) * scale + 2 * SVG_PAD, 1)
    height = round((max_y - min_y) * scale + 2 * SVG_PAD, 1)

    def project(pt):
        x = SVG_PAD + (pt[1] * k - min_x) * scale
        y = SVG_PAD + (max_y - pt[0]) * scale  # flip: north up
        return (round(x, 1), round(y, 1))

    out_holes = []
    for h in holes:
        pts = [project(p) for p in h["points"]]
        tee_ll, green_ll = h["points"][0], h["points"][-1]
        brg = bearing_deg(tee_ll[0], tee_ll[1], green_ll[0], green_ll[1])
        yards = sum(
            haversine_m(a[0], a[1], b[0], b[1])
            for a, b in zip(h["points"], h["points"][1:])
        ) * 1.09361

        # Label sits just past the green, along the final segment direction
        gx, gy = pts[-1]
        px, py = pts[-2]
        seg = math.hypot(gx - px, gy - py) or 1.0
        lx = gx + (gx - px) / seg * 18
        ly = gy + (gy - py) / seg * 18

        out_holes.append({
            "num": h["num"],
            "par": h.get("par"),
            "name": h.get("name"),
            "yards": round(yards),
            "bearing": round(brg),
            "plays": _compass8(brg),
            "points_attr": " ".join(f"{x},{y}" for x, y in pts),
            "tee": pts[0],
            "green": pts[-1],
            "label": (round(lx, 1), round(ly, 1)),
            "impact": "unknown",
        })

    # Nudge colliding labels apart (greens cluster at the turn and clubhouse)
    labels = [list(h["label"]) for h in out_holes]
    for _ in range(24):
        moved = False
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                dx = labels[j][0] - labels[i][0]
                dy = labels[j][1] - labels[i][1]
                d = math.hypot(dx, dy)
                if d < 22:
                    if d < 1e-6:
                        dx, dy, d = 1.0, 0.0, 1.0
                    push = (22 - d) / 2
                    labels[i][0] -= dx / d * push
                    labels[i][1] -= dy / d * push
                    labels[j][0] += dx / d * push
                    labels[j][1] += dy / d * push
                    moved = True
        if not moved:
            break
    for h, (lx, ly) in zip(out_holes, labels):
        h["label"] = (round(min(max(lx, 14), width - 14), 1),
                      round(min(max(ly, 16), height - 10), 1))

    return {
        "width": width,
        "height": height,
        "compass": (width - 54, 54),
        "holes": out_holes,
        "hole_count": len(out_holes),
        "wind_deg": None,
        "wind_speed": None,
        "round_label": None,
    }
