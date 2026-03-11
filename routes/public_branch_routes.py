"""Single public branch by ID - separate path to avoid any conflict with /api/branches/*."""
from fastapi import APIRouter, Body
from pydantic import BaseModel
from controllers.branch_controller import BranchController

router = APIRouter()


class BranchByIdRequest(BaseModel):
    id: str


@router.get("/{branch_id}")
async def get_public_branch_by_id(branch_id: str):
    """Get one branch by ID for public detail page (no authentication required)."""
    return await BranchController.get_branch_public(branch_id)


@router.post("")
async def get_public_branch_by_id_post(body: BranchByIdRequest = Body(...)):
    """Get one branch by ID (POST with JSON body) for public detail page."""
    return await BranchController.get_branch_public(body.id)
