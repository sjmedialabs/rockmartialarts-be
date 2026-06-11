"""Indian mobile normalization (+91 E.164) for auth, registration checkout, and SMS."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_IN_MOBILE_RE = re.compile(r"^[6-9]\d{9}$")


def canonical_indian_phone(phone: Optional[str]) -> Optional[str]:
    """Return +91XXXXXXXXXX for valid Indian mobiles, else None."""
    if not phone:
        return None
    digits = "".join(c for c in phone.strip() if c.isdigit())
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    elif len(digits) > 10:
        digits = digits[-10:]
    if not _IN_MOBILE_RE.match(digits):
        return None
    return f"+91{digits}"


def otp_phone_variants(canonical: str) -> List[str]:
    """Lookup keys for OTP docs; legacy rows may use 10-digit national only."""
    out: List[str] = [canonical]
    if canonical.startswith("+91") and len(canonical) == 13:
        out.append(canonical[3:])
    return out


def subscriber_phone_matches(stored: Any, canonical: str) -> bool:
    if stored == canonical:
        return True
    sc = canonical_indian_phone(str(stored)) if stored else None
    return sc == canonical


def subscriber_phone_lookup_filter(canonical: str) -> Dict[str, Any]:
    variants: List[str] = [canonical]
    if canonical.startswith("+91") and len(canonical) == 13:
        variants.append(canonical[3:])
    return {"phone": {"$in": variants}}
