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
from urllib.error import URLError

log = logging.getLogger(__name__)

INDEXNOW_KEY = "586e4a915efddc888238515477087ac3"

INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_URLS_PER_REQUEST = 10000


def notify(urls: Iterable[str], host: str = "mysportsweather.com") -> bool:
    """POST a batch of URLs to IndexNow. Returns True on success, False otherwise.

    IndexNow accepts up to 10k URLs per request — well above any slate size
    we generate. Empty or non-http URLs are filtered out defensively.

    On failure this logs a warning and returns False. It does NOT raise —
    indexing pushes are best-effort and should never break the request that
    triggered them.
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
            log.warning(f"IndexNow returned status {status} for {len(url_list)} URLs")
            return False
    except URLError as e:
        log.warning(f"IndexNow request failed: {e}")
        return False
    except Exception as e:
        log.exception(f"IndexNow unexpected error: {e}")
        return False
