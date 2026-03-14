from fastapi import HTTPException, status
from datetime import datetime
from typing import List, Optional

from models.achievement_models import StudentAchievement, AchievementCreate, AchievementUpdate
from models.user_models import UserRole
from utils.database import get_db
from utils.helpers import serialize_doc


async def _get_student_branch_id(student_id: str) -> Optional[str]:
    """Resolve branch_id for a student from user.branch_id or enrollments."""
    db = get_db()
    user = await db.users.find_one({"id": student_id, "role": "student"})
    if not user:
        return None
    if user.get("branch_id"):
        return user["branch_id"]
    enrollment = await db.enrollments.find_one(
        {"student_id": student_id, "is_active": True},
        sort=[("created_at", -1)]
    )
    return enrollment.get("branch_id") if enrollment else None


def _can_manage_achievement(current_user: dict, branch_id: str) -> bool:
    """Super admin can manage all; branch manager only their branches."""
    role = current_user.get("role")
    if role == "super_admin":
        return True
    if role == "branch_manager":
        managed = current_user.get("managed_branches") or []
        return branch_id in managed
    return False


def _can_view_student_achievements(current_user: dict, student_id: str, branch_id: str) -> bool:
    """Super admin, branch manager (their branch), or the student themselves."""
    role = current_user.get("role")
    if role == "super_admin":
        return True
    if role == "branch_manager":
        managed = current_user.get("managed_branches") or []
        return branch_id in managed
    if role == "student" and current_user.get("id") == student_id:
        return True
    if role in ("coach_admin", "coach"):
        return True
    return False


class AchievementController:
    @staticmethod
    async def create(data: AchievementCreate, current_user: dict):
        db = get_db()
        branch_id = await _get_student_branch_id(data.student_id)
        if not branch_id:
            raise HTTPException(status_code=400, detail="Student not found or has no branch")
        if not _can_manage_achievement(current_user, branch_id):
            raise HTTPException(status_code=403, detail="Not allowed to create achievements for this student")

        achievement = StudentAchievement(
            student_id=data.student_id,
            branch_id=branch_id,
            title=data.title,
            description=data.description,
            images=data.images or [],
            documents=data.documents or [],
            created_by=current_user.get("id"),
        )
        doc = achievement.dict()
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()
        await db.student_achievements.insert_one(doc)
        return serialize_doc(doc)

    @staticmethod
    async def update(achievement_id: str, data: AchievementUpdate, current_user: dict):
        db = get_db()
        achievement = await db.student_achievements.find_one({"id": achievement_id})
        if not achievement:
            raise HTTPException(status_code=404, detail="Achievement not found")
        if achievement.get("is_deleted"):
            raise HTTPException(status_code=404, detail="Achievement not found")
        branch_id = achievement["branch_id"]
        if not _can_manage_achievement(current_user, branch_id):
            raise HTTPException(status_code=403, detail="Not allowed to edit this achievement")

        update_fields = {}
        if data.title is not None:
            update_fields["title"] = data.title
        if data.description is not None:
            update_fields["description"] = data.description
        if data.images is not None:
            update_fields["images"] = data.images
        if data.documents is not None:
            update_fields["documents"] = data.documents
        update_fields["updated_at"] = datetime.utcnow()
        await db.student_achievements.update_one(
            {"id": achievement_id},
            {"$set": update_fields}
        )
        updated = await db.student_achievements.find_one({"id": achievement_id})
        return serialize_doc(updated)

    @staticmethod
    async def delete(achievement_id: str, current_user: dict):
        db = get_db()
        achievement = await db.student_achievements.find_one({"id": achievement_id})
        if not achievement:
            raise HTTPException(status_code=404, detail="Achievement not found")
        branch_id = achievement["branch_id"]
        if not _can_manage_achievement(current_user, branch_id):
            raise HTTPException(status_code=403, detail="Not allowed to delete this achievement")
        await db.student_achievements.update_one(
            {"id": achievement_id},
            {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}}
        )
        return {"message": "Achievement deleted"}

    @staticmethod
    async def get_by_student(student_id: str, current_user: dict):
        db = get_db()
        user = await db.users.find_one({"id": student_id})
        if not user:
            raise HTTPException(status_code=404, detail="Student not found")
        branch_id = await _get_student_branch_id(student_id)
        if not _can_view_student_achievements(current_user, student_id, branch_id or ""):
            raise HTTPException(status_code=403, detail="Not allowed to view these achievements")

        cursor = db.student_achievements.find({
            "student_id": student_id,
            "is_deleted": False
        }).sort("created_at", -1)
        items = await cursor.to_list(length=500)
        return {"achievements": [serialize_doc(d) for d in items]}

    @staticmethod
    async def get_by_branch_public(branch_id: str, skip: int = 0, limit: int = 12):
        """Public endpoint: achievements for a branch (for branch detail page)."""
        db = get_db()
        cursor = db.student_achievements.find({
            "branch_id": branch_id,
            "is_deleted": False
        }).sort("created_at", -1).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)
        total = await db.student_achievements.count_documents({
            "branch_id": branch_id,
            "is_deleted": False
        })
        # Enrich with student names
        student_ids = list({a["student_id"] for a in items})
        users = await db.users.find({"id": {"$in": student_ids}}).to_list(length=len(student_ids))
        user_map = {u["id"]: u.get("full_name") or f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or "Student" for u in users}
        result = []
        for a in items:
            d = serialize_doc(a)
            d["student_name"] = user_map.get(a["student_id"], "Student")
            result.append(d)
        return {"achievements": result, "total": total }
