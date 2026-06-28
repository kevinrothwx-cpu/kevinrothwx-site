"""Generic alerting via Gmail SMTP.

Sends ops alerts to ALERTS_TO_EMAIL (default kevinrothwx@gmail.com) via
Gmail's SMTP server using an app password stored in the GMAIL_APP_PASSWORD
env var. If either env var is missing, send_alert is a no-op so production
never crashes when alerting is unconfigured (useful during local dev too).

Cooldown is per-condition-key, in-memory only. After firing for a given
condition, the next alert with that same key is suppressed for COOLDOWN_SEC
seconds. This prevents alert storms — if NWS goes down for an hour we get
one email per hour for that condition, not 240 of them.

Usage:
    from alerts import send_alert
    send_alert(
        condition="nws_rate_limit",
        subject="NWS rate limiting kevinrothwx-site",
        body="Got 47 429s in the last 5 min. Falling back to WeatherAPI.",
    )
"""

from __future__ import annotations

import logging
import os
import smtplib
import time
from email.mime.text import MIMEText
from typing import Optional

log = logging.getLogger(__name__)

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587

# The Gmail account that SENDS alerts. Configured via GMAIL_USER env var so
# Kevin can use his personal Google account (e.g. kjrfsu@gmail.com) for
# generating the app password, separately from the kevinrothwx@gmail.com
# brand inbox that receives them.
def _gmail_user() -> str:
    return os.environ.get("GMAIL_USER", "").strip() or "kevinrothwx@gmail.com"

COOLDOWN_SEC = 60 * 60   # 1 hour per condition

# In-memory cooldown tracker: {condition_key: last_sent_epoch}
_last_sent: dict[str, float] = {}


def send_alert(condition: str,
               subject: str,
               body: str,
               to_email: Optional[str] = None) -> bool:
    """Send an alert email. Returns True on send, False on no-op/error.

    Args:
        condition: Cooldown bucket key. Repeated calls with the same key
                   inside COOLDOWN_SEC are suppressed. Use a stable string
                   like "nws_rate_limit" or "warmer_dead_mlb".
        subject: Email subject line. Will be prefixed with "[mysportsweather] ".
        body: Plain-text email body.
        to_email: Recipient. Defaults to ALERTS_TO_EMAIL env var, then
                  kevinrothwx@gmail.com.

    Returns False without raising if:
        - GMAIL_APP_PASSWORD env var is unset (alerting disabled)
        - Cooldown is active for this condition
        - SMTP send fails (logged as warning)
    """
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    if not app_password:
        log.debug(f"alerts: skipping {condition} — GMAIL_APP_PASSWORD unset")
        return False

    now = time.time()
    last = _last_sent.get(condition, 0)
    if now - last < COOLDOWN_SEC:
        remaining = COOLDOWN_SEC - (now - last)
        log.debug(f"alerts: skipping {condition} — cooldown {int(remaining)}s left")
        return False

    recipient = (to_email
                 or os.environ.get("ALERTS_TO_EMAIL", "").strip()
                 or "kevinrothwx@gmail.com")

    sender = _gmail_user()
    msg = MIMEText(body)
    msg["Subject"] = f"[mysportsweather] {subject}"
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(sender, app_password)
            smtp.send_message(msg)
        _last_sent[condition] = now
        log.info(f"alerts: sent {condition} to {recipient}")
        return True
    except Exception as e:
        log.warning(f"alerts: SMTP send failed for {condition}: {e}")
        return False




def is_configured() -> bool:
    """True if GMAIL_APP_PASSWORD env var is set (alerts will actually fire)."""
    return bool(os.environ.get("GMAIL_APP_PASSWORD", "").strip())


def cooldown_remaining(condition: str) -> int:
    """Seconds until the named condition can fire again. 0 if not in cooldown."""
    last = _last_sent.get(condition, 0)
    remaining = COOLDOWN_SEC - (time.time() - last)
    return max(0, int(remaining))
