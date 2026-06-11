"""Admission fee: charge only on first completed enrollment (self or per-beneficiary)."""
from typing import Optional

from models.enrollment_models import PaymentStatus as EnrollmentPaymentStatus


def _normalize_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def _normalize_phone(value: Optional[str]) -> str:
    if not value:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def _beneficiary_signature(beneficiary: Optional[dict]) -> str:
    if not beneficiary:
        return "self"
    btype = _normalize_text(beneficiary.get("beneficiary_type") or "self")
    if btype == "self":
        return "self"
    name = _normalize_text(beneficiary.get("beneficiary_name"))
    phone = _normalize_phone(beneficiary.get("beneficiary_phone"))
    return f"{btype}|{name}|{phone}"


async def student_has_prior_paid_enrollment(
    db,
    student_id: str,
    *,
    course_id: Optional[str] = None,
    beneficiary: Optional[dict] = None,
) -> bool:
    """True if the student (or beneficiary) already has a completed paid enrollment."""
    b = beneficiary or {"beneficiary_type": "self"}
    btype = _normalize_text(b.get("beneficiary_type") or "self")
    completed_filter: dict = {
        "student_id": student_id,
        "payment_status": {"$in": [EnrollmentPaymentStatus.PAID.value, "completed"]},
    }
    if course_id:
        completed_filter["course_id"] = course_id

    if btype == "self":
        return (
            await db.enrollments.find_one(
                {
                    **completed_filter,
                    "$or": [
                        {"beneficiary": {"$exists": False}},
                        {"beneficiary": None},
                        {"beneficiary.beneficiary_type": {"$exists": False}},
                        {"beneficiary.beneficiary_type": "self"},
                    ],
                }
            )
            is not None
        )

    target_sig = _beneficiary_signature(b)
    existing_other = await db.enrollments.find(
        {**completed_filter, "beneficiary": {"$exists": True}},
    ).to_list(length=None)
    return any(_beneficiary_signature(row.get("beneficiary")) == target_sig for row in existing_other)


async def should_charge_admission_fee_for_checkout(
    db,
    student_id: str,
    beneficiary: Optional[dict],
) -> bool:
    """
    Admission fee rules:
    - Charge only on the student's first successful (paid) transaction.
    - Renewals and later course purchases do not include admission again.
    - Self: first completed (non-pending) self enrollment only.
    - Other beneficiary: once per unique beneficiary.
    """
    has_prior = await student_has_prior_paid_enrollment(db, student_id, beneficiary=beneficiary)
    return not has_prior
