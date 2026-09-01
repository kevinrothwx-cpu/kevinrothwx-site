"""check_venue_fields.py — guard against venue fields silently disappearing.

WHY THIS EXISTS
    field_bearing_degrees was added to cfb/venues.py and wired through the
    template, and the arrows still rendered raw compass on every game. No
    error, no log line, nothing in the syntax sweep — the data just wasn't
    there.

    Cause: cfb/schedule.py._build_venue_record rebuilt the venue as a
    hand-written dict listing seven fields by name. Anything not on that
    list was dropped on the floor. It was written before bearings existed,
    so it had no way to know.

    That failure mode is invisible by construction: a missing key reads as
    None, None is a legitimate value ("unmeasured"), and the fallback path
    renders something plausible. The only way to catch it is to assert the
    field survives the trip from venues.py to the game dict.

RUN
    python3 check_venue_fields.py

    Exits non-zero on failure. Worth running after touching anything in
    cfb/schedule.py, cfb/cfbd_client.py, nfl/schedule.py, or either
    venues.py — i.e. anywhere a venue dict is built or copied.
"""

from __future__ import annotations

import sys

# Fields that must survive from the venues table to the rendered game dict.
# Add to this list whenever a new venue attribute starts driving display.
REQUIRED_VENUE_FIELDS = ["name", "city", "lat", "lon", "field_bearing_degrees"]

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'OK  ' if ok else 'FAIL'}  {label}{('  — ' + detail) if detail else ''}")
    if not ok:
        failures.append(label)


def main() -> int:
    print("CFB — ESPN schedule path (_build_venue_record)")
    from cfb.schedule import _build_venue_record
    from cfb.venues import FBS_TEAMS

    # Every FBS home venue must carry every required key through the builder.
    for field in REQUIRED_VENUE_FIELDS:
        missing = [
            FBS_TEAMS[tid]["short"]
            for tid in FBS_TEAMS
            if FBS_TEAMS[tid].get("stadium")
            and field not in _build_venue_record(
                {}, {"team_id": tid, "_in_local_db": True}, False)
        ]
        check(f"all home venues carry '{field}'", not missing,
              f"{len(missing)} missing: {missing[:5]}" if missing else "")

    # A known bearing must arrive with its VALUE intact, not just its key.
    gt = next((tid for tid, t in FBS_TEAMS.items()
               if t.get("short") == "Georgia Tech"), None)
    if gt:
        v = _build_venue_record({}, {"team_id": gt, "_in_local_db": True}, False)
        want = FBS_TEAMS[gt]["stadium"].get("field_bearing_degrees")
        check("bearing value survives (Georgia Tech)",
              v.get("field_bearing_degrees") == want,
              f"got {v.get('field_bearing_degrees')}, want {want}")

    print("\nCFB — CFBD path (cfbd_client copies the stadium dict wholesale)")
    import cfb.cfbd_client as cc
    src = open(cc.__file__, encoding="utf-8").read()
    check("cfbd_client copies the whole dict, no field whitelist",
          'dict(home_team.get("stadium")' in src)

    print("\nCFB — arrow math is actually field-relative")
    import app as msw
    import re
    m = msw.app.jinja_env.get_template("ncaaf/_macros.html").module

    def rot(html):
        hit = re.search(r"rotate\(([-\d.]+) 20 12\)", str(html))
        return float(hit.group(1)) if hit else None

    a = rot(m.cfb_stadium_icon(270, "", field_bearing=0))
    b = rot(m.cfb_stadium_icon(270, "", field_bearing=90))
    check("same wind + different field => different arrow", a != b,
          f"N/S field {a}deg vs E/W field {b}deg")

    # Unmeasured must degrade to the old raw-compass behavior, not to zero.
    raw = rot(m.cfb_stadium_icon(270, "", field_bearing=None))
    check("unmeasured falls back to raw compass", raw == 90.0,
          f"got {raw}, want 90.0")

    print("\nNFL — venue dict passed through, not rebuilt")
    import nfl.schedule as ns
    nsrc = open(ns.__file__, encoding="utf-8").read()
    check("nfl/schedule.py has no venue field whitelist",
          '"roof_type":' not in nsrc)

    from nfl.venues import NFL_TEAMS
    nfl_missing = [
        t.get("short") or t.get("name")
        for t in NFL_TEAMS.values()
        if t.get("stadium")
        and (t["stadium"].get("roof_type") or "") != "fixed_dome"
        and t["stadium"].get("field_bearing_degrees") is None
    ]
    check("all open-air NFL venues have a bearing", not nfl_missing,
          f"{len(nfl_missing)} missing: {nfl_missing[:5]}" if nfl_missing else "")

    print()
    if failures:
        print(f"FAILED — {len(failures)} check(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All venue field checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
