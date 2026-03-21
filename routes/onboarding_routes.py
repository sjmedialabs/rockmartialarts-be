"""Onboarding routes: generate link (admin), validate and submit (public)."""
from typing import Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from controllers.onboarding_controller import OnboardingController
from models.onboarding_models import (
    OnboardingGenerateLinkRequest,
    OnboardingGenerateLinkResponse,
    OnboardingValidateResponse,
    OnboardingSubmitRequest,
    OnboardingSubmitResponse,
)
from fastapi import HTTPException
from utils.unified_auth import get_current_user_or_superadmin
from models.user_models import UserRole

router = APIRouter()


class OnboardingSubmitBody(BaseModel):
    token: str
    password: str
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    branch_id: str
    course_id: str
    duration_id: str
    joining_date: str


@router.post("/generate-link", response_model=dict)
async def generate_onboarding_link(
    body: OnboardingGenerateLinkRequest,
    request: Request,
    current_user: dict = Depends(get_current_user_or_superadmin),
):
    """Generate a one-time onboarding link for an existing student. Super admin only. Link is valid for 5 days."""
    role = (current_user.get("role") or "").lower()
    if role != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Admin can generate onboarding links")

    base_url = request.base_url.__str__().rstrip("/")
    # Prefer frontend base URL from env so link points to the app, not the API
    import os
    frontend_url = os.getenv("FRONTEND_URL", base_url.replace(":8003", ":3022").replace("/api", ""))
    if not frontend_url.startswith("http"):
        frontend_url = f"https://{frontend_url}" if "localhost" not in frontend_url else f"http://{frontend_url}"

    return await OnboardingController.generate_link(body.student_id, frontend_url)


@router.get("/validate", response_model=dict)
async def validate_onboarding_token(token: str):
    """Validate token and return minimal student info for pre-fill. Public."""
    return await OnboardingController.validate_token(token)


@router.post("/submit", response_model=dict)
async def submit_onboarding(body: OnboardingSubmitBody):
    """Submit onboarding form: set password, profile, and enrollment (course, branch, duration, joining date). Public."""
    from datetime import date as date_type
    data = body.model_dump()
    if data.get("date_of_birth"):
        try:
            data["date_of_birth"] = date_type.fromisoformat(data["date_of_birth"])
        except Exception:
            data["date_of_birth"] = None
    if data.get("joining_date"):
        try:
            data["joining_date"] = date_type.fromisoformat(data["joining_date"])
        except Exception:
            pass
    return await OnboardingController.submit_onboarding(data)
