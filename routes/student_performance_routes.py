from fastapi import APIRouter, Depends

from controllers.student_performance_controller import StudentPerformanceController
from models.student_performance_models import (
    CoachFeedbackUpsert,
    GoalsUpsert,
    MedalStatsUpsert,
    ProfilePerformanceUpsert,
    SkillMetricsUpsert,
    WarriorStatsUpsert,
)
from models.user_models import UserRole
from utils.unified_auth import require_role_unified

router = APIRouter()


@router.get("/dashboard/{student_id}")
async def get_student_performance_dashboard(
    student_id: str,
    current_user: dict = Depends(
        require_role_unified(
            [
                UserRole.STUDENT,
                UserRole.SUPER_ADMIN,
                UserRole.COACH_ADMIN,
                UserRole.COACH,
                UserRole.BRANCH_MANAGER,
            ]
        )
    ),
):
    return await StudentPerformanceController.get_dashboard(student_id, current_user)


@router.put("/achievements/{student_id}")
async def put_performance_achievements(
    student_id: str,
    body: MedalStatsUpsert,
    current_user: dict = Depends(
        require_role_unified(
            [UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN, UserRole.COACH, UserRole.BRANCH_MANAGER]
        )
    ),
):
    return await StudentPerformanceController.put_medals(student_id, body, current_user)


@router.put("/skills/{student_id}")
async def put_performance_skills(
    student_id: str,
    body: SkillMetricsUpsert,
    current_user: dict = Depends(
        require_role_unified(
            [UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN, UserRole.COACH, UserRole.BRANCH_MANAGER]
        )
    ),
):
    return await StudentPerformanceController.put_skills(student_id, body, current_user)


@router.put("/goals/{student_id}")
async def put_performance_goals(
    student_id: str,
    body: GoalsUpsert,
    current_user: dict = Depends(
        require_role_unified(
            [UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN, UserRole.COACH, UserRole.BRANCH_MANAGER]
        )
    ),
):
    return await StudentPerformanceController.put_goals(student_id, body, current_user)


@router.put("/feedback/{student_id}")
async def put_performance_feedback(
    student_id: str,
    body: CoachFeedbackUpsert,
    current_user: dict = Depends(
        require_role_unified(
            [UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN, UserRole.COACH, UserRole.BRANCH_MANAGER]
        )
    ),
):
    return await StudentPerformanceController.put_feedback(student_id, body, current_user)


@router.put("/profile/{student_id}")
async def put_performance_profile(
    student_id: str,
    body: ProfilePerformanceUpsert,
    current_user: dict = Depends(
        require_role_unified(
            [UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN, UserRole.COACH, UserRole.BRANCH_MANAGER]
        )
    ),
):
    return await StudentPerformanceController.put_profile(student_id, body, current_user)


@router.put("/warrior-stats/{student_id}")
async def put_performance_warrior_stats(
    student_id: str,
    body: WarriorStatsUpsert,
    current_user: dict = Depends(
        require_role_unified(
            [UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN, UserRole.COACH, UserRole.BRANCH_MANAGER]
        )
    ),
):
    return await StudentPerformanceController.put_warrior(student_id, body, current_user)
