from fastapi import APIRouter, Depends

from models.homepage_content_models import HomepageAboutUpdate
from models.user_models import UserRole
from utils.unified_auth import require_role_unified
from controllers import homepage_content_controller as ctrl

router = APIRouter()


@router.get("/public")
async def get_homepage_public():
    """Public homepage structured content (about section)."""
    return await ctrl.get_public()


@router.put("/about")
async def put_homepage_about(
    data: HomepageAboutUpdate,
    current_user: dict = Depends(require_role_unified([UserRole.SUPER_ADMIN])),
):
    return await ctrl.update_about(data, current_user)
