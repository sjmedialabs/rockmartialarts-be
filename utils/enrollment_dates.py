"""Compute enrollment end dates from duration catalog (id/code) or sensible defaults."""
import re
from datetime import datetime, timedelta
from typing import Optional

DEFAULT_ENROLLMENT_DAYS = 365


async def enrollment_subscription_end_after_payment(db, enrollment: dict) -> Optional[datetime]:
    """
    Authoritative subscription end after checkout payment: duration catalog + enrollment start.
    Does not use client-supplied month counts (those duplicated renewals / inflated validity).
    """
    dur_ref = enrollment.get("duration_id")
    if not dur_ref:
        return None
    raw_start = enrollment.get("start_date") or enrollment.get("enrollment_date")
    if raw_start is None:
        return None
    if isinstance(raw_start, str):
        try:
            start_naive = datetime.fromisoformat(raw_start.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    elif isinstance(raw_start, datetime):
        start_naive = raw_start.replace(tzinfo=None) if raw_start.tzinfo else raw_start
    else:
        return None

    months_hint = None
    dr = await db.durations.find_one({"id": str(dur_ref)})
    if not dr:
        dr = await db.durations.find_one({"code": str(dur_ref)})
    if dr and dr.get("duration_months") is not None:
        try:
            months_hint = int(dr["duration_months"])
        except (TypeError, ValueError):
            months_hint = None

    return await resolve_enrollment_end_date(db, str(dur_ref), start_naive, months_hint=months_hint)


def _parse_months_from_slug(s: str) -> Optional[int]:
    """Parse strings like 1-month, 3-months, 12m into month count."""
    if not s or not str(s).strip():
        return None
    t = str(s).strip().lower().replace(" ", "")
    m = re.match(r"^(\d+)[-_]?(month|months|mon|m)$", t)
    if m:
        try:
            n = int(m.group(1))
            return n if n > 0 else None
        except ValueError:
            return None
    return None


async def resolve_enrollment_end_date(
    db,
    duration_ref: Optional[str],
    start_date: datetime,
    months_hint: Optional[int] = None,
) -> datetime:
    """
    Map selected duration (UUID id or code string) to end_date.
    Uses duration_days when set, else duration_months from catalog, else months_hint,
    else slug patterns (1-month), else DEFAULT_ENROLLMENT_DAYS.

    Duration lookup matches payment pricing: try active record first, then any id/code
    (strict is_active-only lookup caused 1-month selections to fall back to 365 days).
    """
    ref = str(duration_ref).strip() if duration_ref else ""

    if ref:
        dur = await db.durations.find_one({"id": ref, "is_active": True})
        if not dur:
            dur = await db.durations.find_one({"id": ref})
        if not dur:
            dur = await db.durations.find_one({"code": ref, "is_active": True})
        if not dur:
            dur = await db.durations.find_one({"code": ref})
        if dur:
            dd = dur.get("duration_days")
            if dd is not None:
                try:
                    days = int(dd)
                    if days > 0:
                        return start_date + timedelta(days=days)
                except (TypeError, ValueError):
                    pass
            dm = dur.get("duration_months")
            if dm is not None:
                try:
                    months = int(dm)
                    if months > 0:
                        return start_date + timedelta(days=months * 30)
                except (TypeError, ValueError):
                    pass

    if months_hint is not None:
        try:
            mh = int(months_hint)
            if mh > 0:
                return start_date + timedelta(days=mh * 30)
        except (TypeError, ValueError):
            pass

    slug_months = _parse_months_from_slug(ref)
    if slug_months:
        return start_date + timedelta(days=slug_months * 30)

    return start_date + timedelta(days=DEFAULT_ENROLLMENT_DAYS)
