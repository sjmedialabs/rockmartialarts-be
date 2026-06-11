"""Pydantic models for OTP + Razorpay registration checkout (separate from LMS users)."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class SendOtpBody(BaseModel):
    """Client sends E.164 Indian mobile (+91 + 10 digits) or national variants normalized server-side."""
    phone: str = Field(..., min_length=10, max_length=20)


class VerifyOtpBody(BaseModel):
    phone: str
    otp: str = Field(..., min_length=4, max_length=8)


class CreateRegOrderBody(BaseModel):
    phone: str
    amount: float = Field(..., gt=0)
    name: Optional[str] = None
    course_name: Optional[str] = None
    duration: Optional[str] = None
    verification_token: Optional[str] = None


class VerifyRegPaymentBody(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    phone: str
    name: str
    course_name: str
    duration: str
    end_date: str  # ISO date string
    amount: float = Field(..., gt=0)
    verification_token: Optional[str] = None


class RenewalCronBody(BaseModel):
    secret: str
