from fastapi import APIRouter, Depends, Query
from typing import Optional

from controllers.lead_controller import LeadController
from models.lead_models import LeadCreate, LeadResponse
from models.user_models import UserRole
from utils.unified_auth import require_role_unified

router = APIRouter()


@router.post("", response_model=LeadResponse, status_code=201)
async def create_lead(payload: LeadCreate):
    """Public: capture registration / interest leads (no auth)."""
    return await LeadController.create_lead(payload)


@router.get("")
async def list_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    current_user: dict = Depends(require_role_unified([UserRole.SUPER_ADMIN])),
):
    """Super Admin: list leads with optional search and pagination."""
    return await LeadController.list_leads(skip=skip, limit=limit, search=search)
