"""
persistence.py — JSON blob storage for writeups and forecast snapshots.

WHY this exists:
    Render containers are ephemeral — every restart wipes in-memory dicts.
    Sport writeups (typed by Kevin in the admin), forecast freezes (locked
    at first pitch / kickoff), and odds openings need to survive restarts.

BACKEND (2026-08-30 migration):
    Historically this wrote JSON files to /var/data, a Render persistent
    disk. That works, BUT Render disables zero-downtime deploys for any
    service with a disk attached:

        "Adding a persistent disk to your service disables zero-downtime
         deploys for it."  — render.com/docs/deploys

    That's the root cause of the ~25s of 502s on every push. To fix it we
    have to detach the disk, which means this data needs a new home:
    Render Postgres.

    Consumers are untouched. load_json / save_json / parse_dt / DATA_DIR
    keep the exact same signatures, so all 25 importing modules work
    without edits. Only the internals below change.

MODES (PERSISTENCE_BACKEND env var):
    "disk"      — filesystem only. The original behavior. DEFAULT, so
                  deploying this file alone changes nothing.
    "dual"      — write to BOTH disk and Postgres; read Postgres first
                  and fall back to disk on miss/error. This is the safety
                  phase: it proves Postgres holds correct live data while
                  the disk is still authoritative.
    "postgres"  — Postgres only. Set this once dual-write parity is
                  verified, then the disk can be detached in Render.

    If Postgres is requested but unreachable (missing DATABASE_URL, bad
    creds, network), we log loudly and fall back to disk. A database
    misconfiguration must never take the site down.

SCHEMA:
    CREATE TABLE kv (
        key        TEXT PRIMARY KEY,     -- the old filename, e.g. "writeups_nfl.json"
        value      JSONB NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    Keying on the original filename means the migration is a straight
    copy — no key remapping, no consumer changes.

DATETIME HANDLING:
    Datetimes serialize to ISO 8601 strings on save (unchanged). Callers
    needing datetime objects back call parse_dt() at the boundary.

NaN HANDLING:
    Python's json module happily writes NaN/Infinity, which are invalid
    JSON and rejected by Postgres JSONB. Disk writes tolerated them;
    Postgres would raise. _sanitize() converts non-finite floats to None
    before insert so we don't introduce a new failure mode.
"""

from __future__ import annotations

import json
import math
import os
import threading
from datetime import datetime
from typing import Any, Optional


# ── Disk paths (still used in "disk" and "dual" modes) ──────────────────
# Render mounts the persistent disk at /var/data when one is attached.
# Locally, and after the disk is detached, fall back to ./data/ so the
# same code runs everywhere. mlb/cache.py imports DATA_DIR for its
# separate pickle slate cache, so this stays exported.
_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/var/data" if os.path.isdir("/var/data") else os.path.join(_HERE, "data")
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except Exception as e:
    print(f"[persistence] could not create {DATA_DIR}: {e}", flush=True)


# ── Mode selection ──────────────────────────────────────────────────────
_MODE = (os.environ.get("PERSISTENCE_BACKEND") or "disk").strip().lower()
if _MODE not in ("disk", "dual", "postgres"):
    print(f"[persistence] unknown PERSISTENCE_BACKEND={_MODE!r}; using 'disk'",
          flush=True)
    _MODE = "disk"

_DATABASE_URL = (os.environ.get("DATABASE_URL") or "").strip()


# ── Locks ───────────────────────────────────────────────────────────────
# One lock per key so two threads writing the SAME blob serialize, but
# writes to DIFFERENT blobs don't block each other.
_file_locks: dict[str, threading.Lock] = {}
_locks_master = threading.Lock()


def _lock_for(filename: str) -> threading.Lock:
    with _locks_master:
        if filename not in _file_locks:
            _file_locks[filename] = threading.Lock()
        return _file_locks[filename]


# ── JSON helpers ────────────────────────────────────────────────────────

def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Cannot serialize {type(obj).__name__}")


def _sanitize(obj):
    """Recursively replace non-finite floats (NaN, inf, -inf) with None.

    Postgres JSONB rejects them; the filesystem tolerated them. Without
    this, a single NaN in a forecast field would fail the whole save."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    return obj


# ── Postgres backend ────────────────────────────────────────────────────
_pg_pool = None
_pg_init_lock = threading.Lock()
_pg_ready = False


def _init_pg() -> bool:
    """Create the connection pool and ensure the kv table exists.

    Returns True on success. On ANY failure logs and returns False, and
    the caller degrades to disk. Never raises — a database problem must
    not be able to take the site down."""
    global _pg_pool, _pg_ready
    if _pg_ready:
        return True
    with _pg_init_lock:
        if _pg_ready:
            return True
        if not _DATABASE_URL:
            print("[persistence] PERSISTENCE_BACKEND wants Postgres but "
                  "DATABASE_URL is unset — falling back to disk", flush=True)
            return False
        try:
            from psycopg2 import pool as _pgpool
            # Small pool: gunicorn runs -w 1 --threads 4, and write volume
            # is a few hundred/day. 1-5 connections is plenty.
            _pg_pool = _pgpool.ThreadedConnectionPool(
                minconn=1, maxconn=5, dsn=_DATABASE_URL, connect_timeout=8,
            )
            conn = _pg_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS kv (
                            key        TEXT PRIMARY KEY,
                            value      JSONB NOT NULL,
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                        );
                        """
                    )
                conn.commit()
            finally:
                _pg_pool.putconn(conn)
            _pg_ready = True
            print("[persistence] Postgres backend ready (kv table ensured)",
                  flush=True)
            return True
        except Exception as e:
            print(f"[persistence] Postgres init FAILED: {type(e).__name__}: {e} "
                  f"— falling back to disk", flush=True)
            _pg_pool = None
            return False


class _pg_conn:
    """Context manager that borrows a pooled connection and always returns
    it, even on error."""

    def __enter__(self):
        self.conn = _pg_pool.getconn()
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is not None:
                self.conn.rollback()
        finally:
            _pg_pool.putconn(self.conn)
        return False


def _pg_load(key: str):
    """Return the stored object, or None if the key is absent.
    Raises on connection/query error so the caller can decide to fall
    back to disk."""
    with _pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM kv WHERE key = %s;", (key,))
            row = cur.fetchone()
    return row[0] if row else None


def _pg_save(key: str, data: Any) -> None:
    """Upsert a blob. Raises on error so the caller can log/fall back."""
    payload = json.dumps(_sanitize(data), default=_json_default)
    with _pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO kv (key, value, updated_at)
                VALUES (%s, %s::jsonb, now())
                ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value,
                        updated_at = now();
                """,
                (key, payload),
            )
        conn.commit()


# ── Disk backend ────────────────────────────────────────────────────────

def _disk_load(filename: str, default: Any) -> Any:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return default if default is not None else {}
    try:
        with _lock_for(filename):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[persistence] failed to load {filename} from disk: {e}", flush=True)
        return default if default is not None else {}


def _disk_save(filename: str, data: Any) -> None:
    """Atomic write: tmp + rename, so a crash mid-write leaves the previous
    version intact rather than corrupting the file."""
    path = os.path.join(DATA_DIR, filename)
    tmp = path + ".tmp"
    try:
        with _lock_for(filename):
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=_json_default)
            os.replace(tmp, path)
    except Exception as e:
        print(f"[persistence] failed to save {filename} to disk: {e}", flush=True)


# ── Public API (signatures unchanged from the disk-only version) ────────

def load_json(filename: str, default: Any = None) -> Any:
    """Read a JSON blob. Returns `default` (or {}) when absent or unreadable.

    disk     → filesystem
    dual     → Postgres first, disk fallback on miss or error
    postgres → Postgres only
    """
    if _MODE == "disk":
        return _disk_load(filename, default)

    if _init_pg():
        try:
            val = _pg_load(filename)
            if val is not None:
                return val
            # Key absent in Postgres. In dual mode that's expected before
            # the first write of each blob — read through to disk.
            if _MODE == "dual":
                return _disk_load(filename, default)
            return default if default is not None else {}
        except Exception as e:
            print(f"[persistence] Postgres read failed for {filename}: "
                  f"{type(e).__name__}: {e}", flush=True)
            # postgres-only mode still falls back to disk on a hard error.
            # If the disk is gone this returns the default, which is the
            # same graceful-empty behavior as a cold cache.
            return _disk_load(filename, default)

    return _disk_load(filename, default)


def save_json(filename: str, data: Any) -> None:
    """Write a JSON blob.

    disk     → filesystem only
    dual     → BOTH (disk stays authoritative during verification)
    postgres → Postgres only
    """
    if _MODE == "disk":
        _disk_save(filename, data)
        return

    if _MODE == "dual":
        # Disk first — it's still the source of truth during this phase,
        # so a Postgres problem can't cost us data.
        _disk_save(filename, data)

    if _init_pg():
        try:
            _pg_save(filename, data)
        except Exception as e:
            print(f"[persistence] Postgres write failed for {filename}: "
                  f"{type(e).__name__}: {e}", flush=True)
            if _MODE == "postgres":
                # Last-resort disk write so the data isn't simply lost.
                # Harmless if the disk is detached (write fails, logs).
                _disk_save(filename, data)
    elif _MODE == "postgres":
        _disk_save(filename, data)


def parse_dt(s: Optional[str]) -> Optional[datetime]:
    """Convert an ISO 8601 string back to a datetime. Used by callers that
    need datetime objects for comparisons (forecast freeze cleanup, etc.).
    Returns None if input is None, empty, or unparseable."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


# ── Migration + verification helpers (used by /admin/persistence) ───────

def backend_status() -> dict:
    """Snapshot of how persistence is currently wired. Surfaced in admin
    so we can confirm the mode actually took effect after a deploy.

    psycopg2_version is checked explicitly because the driver import is
    lazy (it only happens inside _init_pg, which never runs in disk
    mode). Without this probe you couldn't tell a successful install from
    a failed one until you flipped to dual and it broke.
    """
    try:
        import psycopg2 as _pg2
        driver = getattr(_pg2, "__version__", "installed")
    except Exception as e:
        driver = f"NOT INSTALLED ({type(e).__name__})"
    return {
        "mode":             _MODE,
        "psycopg2_version": driver,
        "database_url_set": bool(_DATABASE_URL),
        "postgres_ready":   _pg_ready,
        "data_dir":         DATA_DIR,
        "data_dir_exists":  os.path.isdir(DATA_DIR),
    }


def list_disk_keys() -> list[str]:
    """Every .json blob currently on disk."""
    try:
        return sorted(
            fn for fn in os.listdir(DATA_DIR)
            if fn.endswith(".json") and not fn.endswith(".tmp")
        )
    except Exception as e:
        print(f"[persistence] list_disk_keys failed: {e}", flush=True)
        return []


def list_pg_keys() -> list[str]:
    """Every key currently in Postgres."""
    if not _init_pg():
        return []
    try:
        with _pg_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT key FROM kv ORDER BY key;")
                return [r[0] for r in cur.fetchall()]
    except Exception as e:
        print(f"[persistence] list_pg_keys failed: {e}", flush=True)
        return []


def migrate_disk_to_pg(overwrite: bool = False) -> dict:
    """One-shot copy of every disk blob into Postgres.

    Safe to run repeatedly. With overwrite=False (default) existing
    Postgres keys are left alone, so a re-run only fills gaps and can't
    clobber fresher data written by the live app.
    """
    if not _init_pg():
        return {"ok": False, "error": "Postgres unavailable"}

    existing = set(list_pg_keys())
    copied, skipped, failed = [], [], []

    for key in list_disk_keys():
        if key in existing and not overwrite:
            skipped.append(key)
            continue
        try:
            data = _disk_load(key, default=None)
            if data is None:
                skipped.append(key)
                continue
            _pg_save(key, data)
            copied.append(key)
        except Exception as e:
            failed.append(f"{key}: {type(e).__name__}: {e}")

    print(f"[persistence] migrate: {len(copied)} copied, {len(skipped)} skipped, "
          f"{len(failed)} failed", flush=True)
    return {"ok": True, "copied": copied, "skipped": skipped, "failed": failed}


def verify_parity() -> dict:
    """Compare every disk blob against its Postgres counterpart.

    Comparison is on the PARSED structure, not raw text — JSONB
    normalizes key order and whitespace, so a byte compare would report
    false mismatches. This is the gate for flipping to postgres-only.
    """
    if not _init_pg():
        return {"ok": False, "error": "Postgres unavailable"}

    disk_keys = list_disk_keys()
    pg_keys = set(list_pg_keys())

    match, mismatch, missing_in_pg, errors = [], [], [], []

    for key in disk_keys:
        if key not in pg_keys:
            missing_in_pg.append(key)
            continue
        try:
            disk_val = _disk_load(key, default=None)
            pg_val = _pg_load(key)
            # Round-trip the disk value through the same sanitize +
            # serialize path Postgres went through, so we're comparing
            # like with like.
            normalized_disk = json.loads(
                json.dumps(_sanitize(disk_val), default=_json_default)
            )
            if normalized_disk == pg_val:
                match.append(key)
            else:
                mismatch.append(key)
        except Exception as e:
            errors.append(f"{key}: {type(e).__name__}: {e}")

    orphans = sorted(pg_keys - set(disk_keys))

    return {
        "ok": True,
        "in_sync": len(mismatch) == 0 and len(missing_in_pg) == 0 and len(errors) == 0,
        "match": match,
        "mismatch": mismatch,
        "missing_in_pg": missing_in_pg,
        "only_in_pg": orphans,
        "errors": errors,
    }


# Boot log — makes the active backend obvious in Render logs.
print(f"[persistence] backend mode={_MODE} data_dir={DATA_DIR} "
      f"database_url={'set' if _DATABASE_URL else 'unset'}", flush=True)
