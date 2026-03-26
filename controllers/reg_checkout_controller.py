"""
OTP + Razorpay registration checkout.
Mongo collections (isolated from LMS `users`):
  reg_checkout_subscribers   — name, phone, is_verified, created_at
  reg_checkout_subscriptions — user_id, course_name, duration, amount, dates, status, payment_id
  reg_checkout_payments      — user_phone, razorpay ids, amount, status, created_at
  reg_checkout_otp           — phone, code_hash, expires_at, last_sent_at
"""

from __future__ import annotations

import hmac
import hashlib
import logging
import os
import random
import string
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

import jwt
import razorpay
from fastapi import HTTPException
from passlib.context import CryptContext

from models.reg_checkout_models import CreateRegOrderBody, VerifyOtpBody, VerifyRegPaymentBody
from utils.database import get_db
from utils.reg_checkout_sms import (
    public_sms_failure_hint,
    send_registration_sms,
    sms_provider_expects_delivery,
)

logger = logging.getLogger(__name__)

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

COL_SUBSCRIBERS = "reg_checkout_subscribers"
COL_SUBSCRIPTIONS = "reg_checkout_subscriptions"
COL_PAYMENTS = "reg_checkout_payments"
COL_OTP = "reg_checkout_otp"

SECRET_KEY = os.environ.get("SECRET_KEY", "student_management_secret_key_2025_secure")
JWT_ALG = "HS256"
OTP_TTL_MIN = 10
RESEND_COOLDOWN_SEC = 60

REQUIRE_OTP = os.getenv("REG_CHECKOUT_REQUIRE_OTP", "true").lower() in ("1", "true", "yes")


def _razorpay_client() -> razorpay.Client:
    key = os.getenv("RAZORPAY_KEY_ID", "").strip()
    sec = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    if not key or not sec:
        raise HTTPException(
            status_code=503,
            detail="Razorpay is not configured (RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET).",
        )
    return razorpay.Client(auth=(key, sec))


def _normalize_phone(phone: str) -> str:
    raw = (phone or "").strip()
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) >= 10:
        return digits[-10:] if len(digits) > 10 else digits
    return digits or raw


def _issue_phone_token(phone: str) -> str:
    norm = _normalize_phone(phone)
    return jwt.encode(
        {
            "sub": norm,
            "scope": "reg_checkout",
            "exp": datetime.utcnow() + timedelta(hours=1),
        },
        SECRET_KEY,
        algorithm=JWT_ALG,
    )


def _verify_phone_token(token: Optional[str], phone: str) -> None:
    if not REQUIRE_OTP:
        return
    if not token:
        raise HTTPException(status_code=401, detail="Phone verification required (missing token).")
    norm = _normalize_phone(phone)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALG])
        if payload.get("scope") != "reg_checkout" or str(payload.get("sub")) != norm:
            raise HTTPException(status_code=403, detail="Invalid phone verification.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired phone verification.")


def _verify_razorpay_signature(order_id: str, pay_id: str, signature: str) -> bool:
    sec = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    if not sec:
        return False
    body = f"{order_id}|{pay_id}".encode("utf-8")
    expected = hmac.new(sec.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def _dlt_template_id_primary_legacy(primary_key: str, legacy_key: str) -> Optional[str]:
    """Use explicit *TEMPLATE_ID env, or legacy var only when it looks like an id (not a message with %)."""
    v = os.getenv(primary_key, "").strip()
    if v:
        return v
    legacy = os.getenv(legacy_key, "").strip()
    if not legacy:
        return None
    if "%" in legacy or "{" in legacy or len(legacy) > 32:
        return None
    compact = legacy.replace("-", "").replace("_", "")
    if compact.isalnum() and len(compact) >= 6 and not legacy.lower().startswith("your "):
        return legacy
    return None


def _otp_dlt_template_id() -> Optional[str]:
    """
    DLT / smslogin `templateid` must be the provider's template ID (digits/alphanumeric),
    not the approved message text. Prefer DLT_OTP_TEMPLATE_ID; legacy DLT_TEMPLATE_OTP
    is used only when it looks like an ID (not a sentence).
    """
    v = os.getenv("DLT_OTP_TEMPLATE_ID", "").strip() or os.getenv("SMS_OTP_TEMPLATE_ID", "").strip()
    if v:
        return v
    legacy = os.getenv("DLT_TEMPLATE_OTP", "").strip()
    if not legacy or "%" in legacy or "{" in legacy or len(legacy) > 32:
        return None
    compact = legacy.replace("-", "").replace("_", "")
    if compact.isalnum() and not legacy.lower().startswith("your "):
        return legacy
    return None


def _otp_sms_message(otp: str) -> str:
    """SMS body must match the DLT-approved wording; use DLT_OTP_MESSAGE with %s or {otp}."""
    body = os.getenv("DLT_OTP_MESSAGE", "").strip()
    if not body:
        legacy = os.getenv("DLT_TEMPLATE_OTP", "").strip()
        if legacy and ("%s" in legacy or "{otp}" in legacy.lower()):
            body = legacy
    if body:
        if "%s" in body:
            try:
                return body % otp
            except Exception:
                logger.exception("DLT_OTP_MESSAGE / DLT_TEMPLATE_OTP %%s formatting failed")
        return body.replace("{otp}", otp)
    return (
        "ROCK MARTIAL ARTS ACADEMY: Your OTP is "
        f"{otp}. Use this to complete your registration/login. Do not share this code with anyone."
    )


def _parse_end_date(s: str) -> datetime:
    s = (s or "").strip().replace("Z", "")
    if "T" in s:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    d = date.fromisoformat(s[:10])
    return datetime(d.year, d.month, d.day, 23, 59, 59)


class RegCheckoutController:
    @staticmethod
    async def send_otp(phone: str) -> Dict[str, Any]:
        db = get_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not initialized")

        norm = _normalize_phone(phone)
        if len(norm) < 8:
            raise HTTPException(status_code=400, detail="Invalid phone number.")

        now = datetime.utcnow()
        existing = await db[COL_OTP].find_one({"phone": norm})
        if existing and existing.get("last_sent_at"):
            delta = (now - existing["last_sent_at"]).total_seconds()
            if delta < RESEND_COOLDOWN_SEC:
                raise HTTPException(
                    status_code=429,
                    detail=f"Please wait {int(RESEND_COOLDOWN_SEC - delta)}s before resending OTP.",
                )

        otp = "".join(random.choices(string.digits, k=6))
        code_hash = _pwd.hash(otp)
        expires = now + timedelta(minutes=OTP_TTL_MIN)

        await db[COL_OTP].update_one(
            {"phone": norm},
            {
                "$set": {
                    "phone": norm,
                    "code_hash": code_hash,
                    "expires_at": expires,
                    "last_sent_at": now,
                }
            },
            upsert=True,
        )

        msg = _otp_sms_message(otp)
        tid = _otp_dlt_template_id()
        if tid is None and sms_provider_expects_delivery():
            prov = (os.getenv("SMS_PROVIDER") or "json").strip().lower()
            if prov in ("smslogin", "smslogin_co", "rockacademy", "msg91"):
                logger.warning(
                    "OTP SMS: no DLT template id (set DLT_OTP_TEMPLATE_ID). "
                    "smslogin/MSG91 often require templateid for DLT."
                )
        ok, sms_err = send_registration_sms(phone, msg, template_id=tid)
        allow_stub = os.getenv("REG_CHECKOUT_ALLOW_SMS_STUB", "").lower() in (
            "1",
            "true",
            "yes",
        )
        expects_sms = sms_provider_expects_delivery()
        if expects_sms and not allow_stub and not ok:
            await db[COL_OTP].delete_one({"phone": norm})
            hint = public_sms_failure_hint(sms_err)
            base = (
                "Could not send OTP SMS. Set SMS_PROVIDER=smslogin, SMS_API_URL=https://smslogin.co/v3/api.php, "
                "SMS_USERNAME, SMS_API_KEY, SMS_SENDER_ID, DLT_OTP_TEMPLATE_ID (DLT template id from portal), "
                "and DLT_OTP_MESSAGE (approved body with %s for OTP). Check server logs for the gateway response."
            )
            if hint:
                base = f"{base} Hint: {hint}"
            base += (
                " For local/staging without SMS, set REG_CHECKOUT_ALLOW_SMS_STUB=true (OTP is still stored; "
                "check server logs for the code)."
            )
            raise HTTPException(status_code=503, detail=base)
        if expects_sms and allow_stub and not ok:
            logger.warning(
                "OTP SMS send failed but REG_CHECKOUT_ALLOW_SMS_STUB=true — continuing without delivery."
            )
        if not expects_sms:
            logger.warning(
                "SMS gateway not configured for OTP (e.g. SMS_PROVIDER=json with no SMS_API_URL). "
                "OTP is stored but not sent to the handset — configure Rock Academy SMS env or set "
                "REG_CHECKOUT_ALLOW_SMS_STUB=true only for local dev."
            )
        elif expects_sms and ok:
            logger.info("OTP sent via SMS for phone ending ...%s", norm[-4:])

        return {"message": "OTP sent", "expires_in_seconds": OTP_TTL_MIN * 60}

    @staticmethod
    async def verify_otp(body: VerifyOtpBody) -> Dict[str, Any]:
        db = get_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not initialized")

        norm = _normalize_phone(body.phone)
        doc = await db[COL_OTP].find_one({"phone": norm})
        if not doc:
            raise HTTPException(status_code=400, detail="No OTP request for this number.")

        if doc.get("expires_at") and datetime.utcnow() > doc["expires_at"]:
            raise HTTPException(status_code=400, detail="OTP expired. Request a new one.")

        if not _pwd.verify(body.otp, doc["code_hash"]):
            raise HTTPException(status_code=400, detail="Invalid OTP.")

        await db[COL_OTP].delete_one({"phone": norm})

        token = _issue_phone_token(norm)
        return {
            "verified": True,
            "verification_token": token,
            "expires_in": 3600,
        }

    @staticmethod
    async def create_order(body: CreateRegOrderBody) -> Dict[str, Any]:
        _verify_phone_token(body.verification_token, body.phone)

        client = _razorpay_client()
        amount_paise = int(round(float(body.amount) * 100))
        if amount_paise < 100:
            raise HTTPException(status_code=400, detail="Amount too small.")

        try:
            order = client.order.create(
                {
                    "amount": amount_paise,
                    "currency": "INR",
                    "payment_capture": 1,
                    "notes": {
                        "phone": _normalize_phone(body.phone),
                        "course": (body.course_name or "")[:120],
                    },
                }
            )
        except Exception as e:
            logger.exception("Razorpay order.create failed")
            raise HTTPException(status_code=502, detail=f"Payment provider error: {str(e)}")

        db = get_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not initialized")

        now = datetime.utcnow()
        await db[COL_PAYMENTS].insert_one(
            {
                "user_phone": _normalize_phone(body.phone),
                "razorpay_order_id": order["id"],
                "razorpay_payment_id": None,
                "razorpay_signature": None,
                "amount": float(body.amount),
                "status": "created",
                "created_at": now,
                "course_name": body.course_name,
                "duration": body.duration,
                "customer_name": body.name,
            }
        )

        key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
        return {
            "order_id": order["id"],
            "key": key_id,
            "amount": amount_paise,
            "currency": "INR",
        }

    @staticmethod
    async def verify_payment(body: VerifyRegPaymentBody) -> Dict[str, Any]:
        _verify_phone_token(body.verification_token, body.phone)

        if not _verify_razorpay_signature(
            body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature
        ):
            raise HTTPException(status_code=400, detail="Invalid payment signature")

        db = get_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not initialized")

        pay = await db[COL_PAYMENTS].find_one({"razorpay_order_id": body.razorpay_order_id})
        if not pay:
            raise HTTPException(status_code=404, detail="Unknown order id")

        norm_phone = _normalize_phone(body.phone)
        if pay.get("user_phone") != norm_phone:
            raise HTTPException(status_code=403, detail="Phone does not match order")

        dup = await db[COL_SUBSCRIPTIONS].find_one({"payment_id": body.razorpay_payment_id})
        if dup:
            return {"status": "success", "idempotent": True, "subscription_id": str(dup["_id"])}

        now = datetime.utcnow()
        await db[COL_PAYMENTS].update_one(
            {"razorpay_order_id": body.razorpay_order_id},
            {
                "$set": {
                    "status": "paid",
                    "razorpay_payment_id": body.razorpay_payment_id,
                    "razorpay_signature": body.razorpay_signature,
                    "paid_at": now,
                }
            },
        )

        user = await db[COL_SUBSCRIBERS].find_one({"phone": norm_phone})
        if not user:
            ins = await db[COL_SUBSCRIBERS].insert_one(
                {
                    "name": body.name.strip(),
                    "phone": norm_phone,
                    "is_verified": True,
                    "created_at": now,
                }
            )
            user_id = ins.inserted_id
        else:
            user_id = user["_id"]
            await db[COL_SUBSCRIBERS].update_one(
                {"_id": user_id},
                {"$set": {"name": body.name.strip(), "is_verified": True}},
            )

        end_dt = _parse_end_date(body.end_date)
        sub = await db[COL_SUBSCRIPTIONS].insert_one(
            {
                "user_id": user_id,
                "course_name": body.course_name,
                "duration": body.duration,
                "amount": float(body.amount),
                "start_date": now,
                "end_date": end_dt,
                "status": "active",
                "payment_id": body.razorpay_payment_id,
            }
        )

        welcome = (
            f"ROCK MARTIAL ARTS ACADEMY: Welcome {body.name}! Your registration for "
            f"{body.course_name} – {body.duration} is confirmed. Get ready to train hard and grow stronger every day. See you in class!"
        )
        tid_w = _dlt_template_id_primary_legacy(
            "DLT_WELCOME_TEMPLATE_ID", "DLT_TEMPLATE_WELCOME"
        )
        if not send_registration_sms(body.phone, welcome, template_id=tid_w)[0]:
            logger.warning(
                "Welcome SMS failed for payment_id=%s phone=...%s",
                body.razorpay_payment_id,
                _normalize_phone(body.phone)[-4:],
            )

        tid_pay = _dlt_template_id_primary_legacy(
            "DLT_PAYMENT_TEMPLATE_ID", "DLT_TEMPLATE_PAYMENT_CONFIRMED"
        )
        if tid_pay:
            amt = float(body.amount)
            pay_msg = (
                f"ROCK MARTIAL ARTS ACADEMY: Hi {body.name.strip()}, your payment of ₹{amt:.0f} for "
                f"{body.course_name} – {body.duration} was received successfully. "
                "Thank you — see you in class!"
            )
            if not send_registration_sms(body.phone, pay_msg, template_id=tid_pay)[0]:
                logger.warning(
                    "Payment confirmation SMS failed for payment_id=%s",
                    body.razorpay_payment_id,
                )

        return {
            "status": "success",
            "subscription_id": str(sub.inserted_id),
            "user_id": str(user_id),
        }

    @staticmethod
    async def run_renewal_reminders(secret: str) -> Dict[str, Any]:
        expected = os.getenv("REG_CHECKOUT_CRON_SECRET", "").strip()
        if not expected or secret != expected:
            raise HTTPException(status_code=403, detail="Invalid cron secret")

        db = get_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not initialized")

        now = datetime.utcnow()
        until = now + timedelta(days=7)
        q = {
            "status": "active",
            "end_date": {"$gte": now, "$lte": until},
            "$or": [{"renewal_reminder_sent": {"$exists": False}}, {"renewal_reminder_sent": False}],
        }

        sent = 0
        async for sub in db[COL_SUBSCRIPTIONS].find(q):
            user = await db[COL_SUBSCRIBERS].find_one({"_id": sub["user_id"]})
            if not user:
                continue
            phone = user.get("phone")
            name = user.get("name", "Student")
            end = sub.get("end_date")
            if isinstance(end, datetime):
                validity = end.strftime("%d-%m-%Y")
            else:
                validity = str(end)

            msg = (
                f"ROCK MARTIAL ARTS ACADEMY: Hi {name}, your plan ends on {validity}. "
                "Don't break your momentum—renew now and keep progressing. Stay strong!"
            )
            tid = _dlt_template_id_primary_legacy(
                "DLT_REMINDER_TEMPLATE_ID", "DLT_TEMPLATE_REMINDER"
            )
            ok, _ = send_registration_sms(phone, msg, template_id=tid)
            if ok:
                await db[COL_SUBSCRIPTIONS].update_one(
                    {"_id": sub["_id"]},
                    {"$set": {"renewal_reminder_sent": True, "renewal_reminder_at": now}},
                )
                sent += 1

        return {"message": "Renewal reminders processed", "sent": sent}
