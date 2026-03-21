"""Compute enrollment end dates from duration catalog (id/code) or sensible defaults."""
from datetime import datetime, timedelta
from typing import Optional

DEFAULT_ENROLLMENT_DAYS = 365


async def resolve_enrollment_end_date(
    db,
    duration_ref: Optional[str],
    start_date: datetime,
) -> datetime:
    """
    Map selected duration (UUID id or code string) to end_date.
    Uses duration_days when set, else duration_months * 30 (same convention as other controllers).
    """
    if duration_ref and str(duration_ref).strip():
        ref = str(duration_ref).strip()
        dur = await db.durations.find_one({"id": ref, "is_active": True})
        if not dur:
            dur = await db.durations.find_one({"code": ref, "is_active": True})
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
    return start_date + timedelta(days=DEFAULT_ENROLLMENT_DAYS)
