"""
Keep a single active branch assignment per student across users + enrollments.
"""
from datetime import datetime
from typing import Optional


async def sync_student_branch_assignment(
    db,
    student_id: str,
    new_branch_id: str,
    *,
    old_branch_id: Optional[str] = None,
) -> None:
    """
    After an admin branch change or approved transfer:
    - Set users.branch_id (and nested branch fields)
    - Move all active enrollments to new_branch_id
    """
    if not new_branch_id:
        return

    now = datetime.utcnow()
    new_branch = await db.branches.find_one({"id": new_branch_id})
    user_set: dict = {
        "branch_id": new_branch_id,
        "updated_at": now,
    }
    if new_branch:
        user_set["branch.branch_id"] = new_branch_id
        location_id = new_branch.get("location_id")
        if location_id:
            user_set["branch.location_id"] = location_id

    await db.users.update_one({"id": student_id}, {"$set": user_set})

    await db.enrollments.update_many(
        {"student_id": student_id, "is_active": True},
        {"$set": {"branch_id": new_branch_id, "updated_at": now}},
    )


async def get_student_assigned_branch_id(db, student_id: str) -> Optional[str]:
    """Primary branch for an existing student (user record, then active enrollment)."""
    user = await db.users.find_one(
        {"id": student_id},
        {"branch_id": 1, "branch": 1},
    )
    if user:
        bid = user.get("branch_id") or (user.get("branch") or {}).get("branch_id")
        if bid:
            return str(bid)
    enr = await db.enrollments.find_one(
        {"student_id": student_id, "is_active": True},
        sort=[("updated_at", -1)],
    )
    if enr and enr.get("branch_id"):
        return str(enr["branch_id"])
    paid = await db.enrollments.find_one(
        {"student_id": student_id, "payment_status": "paid"},
        sort=[("updated_at", -1)],
    )
    if paid and paid.get("branch_id"):
        return str(paid["branch_id"])
    return None


async def count_students_for_branch(db, branch_id: str) -> int:
    """Distinct active students at a branch (enrollment source of truth)."""
    pipeline = [
        {"$match": {"branch_id": branch_id, "is_active": True}},
        {"$group": {"_id": "$student_id"}},
        {"$count": "unique_students"},
    ]
    result = await db.enrollments.aggregate(pipeline).to_list(1)
    return result[0]["unique_students"] if result else 0
