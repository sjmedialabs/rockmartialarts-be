"""Shared Razorpay SDK client and signature verification (keys stay on server)."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os

import razorpay
import requests
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def get_razorpay_client() -> razorpay.Client:
    key = os.getenv("RAZORPAY_KEY_ID", "").strip()
    sec = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    if not key or not sec:
        raise HTTPException(
            status_code=503,
            detail="Razorpay is not configured (RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET).",
        )
    sess = requests.Session()
    sess.trust_env = False
    return razorpay.Client(session=sess, auth=(key, sec))


def verify_razorpay_signature(order_id: str, pay_id: str, signature: str) -> bool:
    sec = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    if not sec:
        return False
    body = f"{order_id}|{pay_id}".encode("utf-8")
    expected = hmac.new(sec.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")
