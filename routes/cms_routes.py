from fastapi import APIRouter, Depends, Query, status
from controllers.cms_controller import CMSController
from models.cms_models import CMSContentUpdate, CMSContentResponse
from models.user_models import UserRole
from utils.unified_auth import require_role_unified

router = APIRouter()




@router.get("/public/branch-testimonials/{branch_id}")
async def get_branch_testimonials_public(
    branch_id: str,
    limit: int = Query(4, ge=1, le=20),
):
    """Branch-scoped testimonials for public website (no auth required)."""
    return await CMSController.get_branch_testimonials_public(branch_id, limit)


@router.get("/public")
async def get_cms_content_public():
    """Get CMS content for public website (no auth required)"""
    return await CMSController.get_cms_content_public()

@router.get("", response_model=CMSContentResponse)
async def get_cms_content(
    current_user: dict = Depends(require_role_unified([UserRole.SUPER_ADMIN]))
):
    """Get CMS content (homepage sections, footer, branding, page SEO)"""
    return await CMSController.get_cms_content(current_user)


@router.put("", response_model=CMSContentResponse)
async def update_cms_content(
    data: CMSContentUpdate,
    current_user: dict = Depends(require_role_unified([UserRole.SUPER_ADMIN]))
):
    """Update CMS content"""
    return await CMSController.update_cms_content(data, current_user)


@router.put("/branding/{field}")
async def update_branding_image(
    field: str,
    image_url: str,
    current_user: dict = Depends(require_role_unified([UserRole.SUPER_ADMIN]))
):
    """Update a branding image (navbar_logo, footer_logo, favicon, site_loader_image)"""
    return await CMSController.upload_branding_image(field, image_url, current_user)
