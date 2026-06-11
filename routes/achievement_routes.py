from fastapi import APIRouter, Depends, Query
from models.achievement_models import AchievementCreate, AchievementUpdate
from models.user_models import UserRole
from utils.unified_auth import require_role_unified, get_current_user_or_superadmin
from controllers.achievement_controller import AchievementController

router = APIRouter()


@router.post("/create")
async def create_achievement(
    data: AchievementCreate,
    current_user: dict = Depends(require_role_unified([UserRole.SUPER_ADMIN, UserRole.BRANCH_MANAGER, UserRole.COACH_ADMIN, UserRole.COACH])),
):
    """Create achievement for a student. Branch admin only for students in their branch."""
    return await AchievementController.create(data, current_user)


@router.put("/update/{achievement_id}")
async def update_achievement(
    achievement_id: str,
    data: AchievementUpdate,
    current_user: dict = Depends(require_role_unified([UserRole.SUPER_ADMIN, UserRole.BRANCH_MANAGER, UserRole.COACH_ADMIN, UserRole.COACH])),
):
    """Update achievement. Branch admin only for their branch."""
    return await AchievementController.update(achievement_id, data, current_user)


@router.delete("/delete/{achievement_id}")
async def delete_achievement(
    achievement_id: str,
    current_user: dict = Depends(require_role_unified([UserRole.SUPER_ADMIN, UserRole.BRANCH_MANAGER, UserRole.COACH_ADMIN, UserRole.COACH])),
):
    """Soft delete achievement."""
    return await AchievementController.delete(achievement_id, current_user)


@router.get("/student/{student_id}")
async def get_student_achievements(
    student_id: str,
    current_user: dict = Depends(require_role_unified([UserRole.SUPER_ADMIN, UserRole.BRANCH_MANAGER, UserRole.COACH_ADMIN, UserRole.COACH, UserRole.STUDENT])),
):
    """Get achievements for a student. Student can view own; admins can view based on branch."""
    return await AchievementController.get_by_student(student_id, current_user)


@router.get("/public/global")
async def get_global_achievements_public(
    skip: int = Query(0, ge=0),
    limit: int = Query(6, ge=1, le=50),
):
    """Public: get most recent achievements across all branches (for homepage). No auth."""
    return await AchievementController.get_global_public(skip=skip, limit=limit)


@router.get("/public/branch/{branch_id}")
async def get_branch_achievements_public(
    branch_id: str,
  skip: int = Query(0, ge=0),
  limit: int = Query(50, ge=1, le=200),
):
    """Public: get achievements for a branch (for branch detail page). No auth."""
    return await AchievementController.get_by_branch_public(branch_id, skip=skip, limit=limit)
