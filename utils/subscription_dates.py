"""Subscription period end: consistent UTC end-of-day comparisons (no string compares)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def subscription_end_of_day_utc(end_val: Any) -> Optional[datetime]:
    """
    Last instant the subscription is valid: end of the **calendar day (UTC)** that contains end_val.

    Naive datetimes are treated as UTC. ISO date-only strings use that date at 23:59:59.999999 UTC.
    """
    if end_val is None:
        return None

    if isinstance(end_val, datetime):
        dt = _ensure_utc(end_val)
        d = dt.date()
        return datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=timezone.utc)

    if type(end_val) is date:
        d = end_val
        return datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=timezone.utc)

    s = str(end_val).strip()
    if not s:
        return None

    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            y, m, d = int(s[0:4]), int(s[5:7]), int(s[8:10])
            return datetime(y, m, d, 23, 59, 59, 999999, tzinfo=timezone.utc)
        except ValueError:
            pass

    try:
        raw = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None

    dt = _ensure_utc(raw)
    d = dt.date()
    return datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=timezone.utc)


def is_subscription_period_over(end_val: Any, now: Optional[datetime] = None) -> bool:
    """True only after the subscription's last day (UTC) has fully ended."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)

    end_eod = subscription_end_of_day_utc(end_val)
    if end_eod is None:
        return False

    expired = now > end_eod
    logger.debug(
        "subscription expiry check: now=%s end_eod=%s expired=%s raw_end=%s",
        now.isoformat(),
        end_eod.isoformat(),
        expired,
        end_val,
    )
    return expired
