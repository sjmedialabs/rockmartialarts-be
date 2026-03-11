from fastapi import APIRouter, Depends, File, UploadFile
from controllers.upload_controller import UploadController
from models.user_models import UserRole
from utils.unified_auth import require_role_unified

router = APIRouter()


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(
        require_role_unified([UserRole.SUPER_ADMIN, UserRole.BRANCH_MANAGER, UserRole.COACH_ADMIN, UserRole.COACH])
    ),
):
    """Upload a file (image, video, or PDF). Returns the public URL."""
    return await UploadController.upload_file(file, current_user)
