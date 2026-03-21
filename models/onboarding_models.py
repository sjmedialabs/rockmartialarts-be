"""Models for existing-student onboarding (invite link flow)."""
from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from typing import Optional


class OnboardingGenerateLinkRequest(BaseModel):
    """Admin requests an onboarding link for a student."""
    student_id: str


class OnboardingGenerateLinkResponse(BaseModel):
    """Response with one-time link for the student."""
    token: str
    link: str
    expires_at: datetime
    student_email: str
    student_phone: str


class OnboardingValidateResponse(BaseModel):
    """Public validate response: minimal student info for pre-fill (no secrets)."""
    valid: bool
    message: Optional[str] = None
    student: Optional[dict] = None  # id, email (masked), phone (masked), first_name, last_name, date_of_birth, gender
    expires_at: Optional[datetime] = None


class OnboardingSubmitRequest(BaseModel):
    """Student submits onboarding form (set password + profile + course/branch/duration/joining)."""
    token: str
    password: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    # Enrollment: course, branch, duration, joining date
    branch_id: str
    course_id: str
    duration_id: str  # used to get duration_months for end_date
    joining_date: date  # start_date of enrollment


class OnboardingSubmitResponse(BaseModel):
    """Success response after onboarding."""
    message: str
    user_id: str
