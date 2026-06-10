"""
One-shot warmer: fetch OSM hole geometry for every course in
golf/courses.py and cache it to static/data/course_holes/.

Run from the repo root:  python scripts/prefetch_course_holes.py

Lazy fetching already happens on first page view, so this is optional —
it just front-loads the Overpass calls and lets you commit the JSON so
production never waits on Overpass. Re-run with --force to refresh a
course after its OSM mapping improves.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from golf.courses import PGA_COURSES               # noqa: E402
from golf.holes import (                           # noqa: E402
    CACHE_DIR, MIN_HOLES_FOR_MAP, course_cache_slug, get_course_holes,
)


def main():
    force = "--force" in sys.argv
    results = []
    for name, meta in PGA_COURSES.items():
        cache_file = CACHE_DIR / f"{course_cache_slug(name)}.json"
        if cache_file.exists():
            if force:
                cache_file.unlink()
            else:
                print(f"  cached   {name}")
                continue
        holes = get_course_holes({**meta, "_canonical_name": name})
        if holes is None:
            status = "FETCH FAILED"
        elif len(holes) >= MIN_HOLES_FOR_MAP:
            status = f"{len(holes)} holes"
        else:
            status = f"only {len(holes)} holes (below render threshold)"
        results.append((name, status))
        print(f"  fetched  {name}: {status}")
        time.sleep(2)  # be polite to Overpass

    print(f"\nDone. Cache dir: {CACHE_DIR}")
    bad = [r for r in results if "holes" not in r[1] or "only" in r[1]]
    if bad:
        print("Needs attention (try a bigger osm_radius_m in courses.py, "
              "or the course isn't mapped on OSM yet):")
        for name, status in bad:
            print(f"  - {name}: {status}")


if __name__ == "__main__":
    main()
