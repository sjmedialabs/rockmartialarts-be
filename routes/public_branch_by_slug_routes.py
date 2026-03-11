"""Public branch by URL slug - GET /api/public-branch-by-slug/{slug}."""
from fastapi import APIRouter
from controllers.branch_controller import BranchController

router = APIRouter()


@router.get("/{slug}")
async def get_public_branch_by_slug(slug: str):
    """Get one branch by URL slug for public detail page (no authentication required)."""
    return await BranchController.get_branch_by_slug(slug)
