"""IndexNow protocol client for Bing + Yandex (and indirectly ChatGPT search).

IndexNow is an open standard developed by Microsoft and Yandex for proactively
pinging search engines when URLs are created or change. By pushing new game
URLs the moment a slate rebuilds, we get into Bing's index in minutes instead
of waiting for the crawler to find us on its own schedule. ChatGPT-search
reads from the Bing index, so this also indirectly improves LLM discoverability.

Spec: https://www.indexnow.org/documentation

The key is public by design — IndexNow requires it be served at
https://<host>/<KEY>.txt so the search engine can confirm site ownership.
There is nothing sensitive about it. A stable random value is baked in so
the verification file URL never changes.
"""

import json
import logging
from typing import Iterable
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

log = logging.getLogger(__name__)

INDEXNOW_KEY = "586e4a915efddc888238515477087ac3"

INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_URLS_PER_REQUEST = 10000


def notify(urls: Iterable[str], host: str = "mysportsweather.com") -> bool:
    """POST a batch of URLs to IndexNow. Returns True on success, False otherwise.

    IndexNow accepts up to 10k URLs per request — well above any slate size
    we generate. Empty or non-http URLs are filtered out defensively.

    On failure this logs a warning (with Bing's response body when available,
    so we can see the actual rejection reason) and returns False. It does NOT
    raise — indexing pushes are best-effort and should never break the request
    that triggered them.
    """
    url_list = [u for u in urls if isinstance(u, str) and u.startswith("http")]
    if not url_list:
        return True

    payload = {
        "host": host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{host}/{INDEXNOW_KEY}.txt",
        "urlList": url_list[:MAX_URLS_PER_REQUEST],
    }

    body = json.dumps(payload).encode("utf-8")
    req = Request(
        INDEXNOW_ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=10) as resp:
            status = resp.status
            if 200 <= status < 300:
                log.info(f"IndexNow accepted {len(url_list)} URLs (status {status})")
                return True
            # Non-2xx that didn't raise (rare — redirect edge cases).
            body_preview = _safe_read_body(resp)
            msg = f"IndexNow status {status} for {len(url_list)} URLs; body: {body_preview!r}"
            log.warning(msg)
            print(f"[indexnow] {msg}", flush=True)
            return False
    except HTTPError as e:
        # 4xx / 5xx: read Bing's response body — it explains WHY they rejected
        # the submission (InvalidHost, InvalidUrl, Forbidden, TooManyUrls, etc.)
        body_preview = _safe_read_body(e)
        msg = f"IndexNow HTTP {e.code} for {len(url_list)} URLs; body: {body_preview!r}"
        log.warning(msg)
        print(f"[indexnow] {msg}", flush=True)
        return False
    except URLError as e:
        msg = f"IndexNow request failed (network/URL error): {e}"
        log.warning(msg)
        print(f"[indexnow] {msg}", flush=True)
        return False
    except Exception as e:
        log.exception(f"IndexNow unexpected error: {e}")
        print(f"[indexnow] unexpected error: {type(e).__name__}: {e}", flush=True)
        return False


def _safe_read_body(resp_or_err, max_bytes: int = 2000) -> str:
    """Read up to ``max_bytes`` from an HTTP response or HTTPError.
    Returns a decoded string (replacement chars on bad bytes) or "" on
    any failure — never raises."""
    try:
        raw = resp_or_err.read(max_bytes)
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="replace")
        return str(raw)
    except Exception:
        return ""


# EOF-CANARY 2026-07-18-indexnow-body-logging
