"""
One-time repair script for payment/enrollment linkage.

Repairs:
1) Backfill payments.enrollment_id from razorpay_order_id when missing.
2) Mark enrollments.payment_status='paid' when latest linked payment succeeded.

Run:
  python3 scripts/sync_enrollment_payment_status.py
"""

import asyncio
import os
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    mongo_url = os.getenv("MONGO_URL") or os.getenv("MONGO_URI") or "mongodb://localhost:27017"
    db_name = os.getenv("DB_NAME", "marshalats")
    client = AsyncIOMotorClient(mongo_url, tlsInsecure=True)
    db = client.get_database(db_name)

    now = datetime.utcnow()
    repaired_payment_links = 0
    updated_enrollments = 0

    # 1) Backfill missing enrollment_id by matching order_id on enrollments.
    async for p in db.payments.find(
        {
            "$or": [{"enrollment_id": {"$exists": False}}, {"enrollment_id": None}, {"enrollment_id": ""}],
            "razorpay_order_id": {"$exists": True, "$ne": None},
        }
    ):
        student_id = p.get("student_id") or p.get("user_id")
        order_id = p.get("razorpay_order_id")
        if not student_id or not order_id:
            continue
        enrollment = await db.enrollments.find_one(
            {"student_id": student_id, "razorpay_last_order_id": order_id},
            {"id": 1, "course_id": 1},
        )
        if not enrollment:
            continue
        res = await db.payments.update_one(
            {"_id": p["_id"]},
            {
                "$set": {
                    "enrollment_id": enrollment["id"],
                    "course_id": enrollment.get("course_id"),
                    "updated_at": now,
                }
            },
        )
        if res.modified_count:
            repaired_payment_links += 1

    # 2) For each enrollment with a successful payment, mark enrollment as paid.
    # success = payment_status=paid OR status=success
    pipeline = [
        {
            "$match": {
                "enrollment_id": {"$exists": True, "$ne": None, "$ne": ""},
                "$or": [{"payment_status": "paid"}, {"status": "success"}],
            }
        },
        {"$sort": {"created_at": -1}},
        {
            "$group": {
                "_id": "$enrollment_id",
                "latest_payment_id": {"$first": "$id"},
                "latest_created_at": {"$first": "$created_at"},
            }
        },
    ]
    rows = await db.payments.aggregate(pipeline).to_list(length=None)
    for row in rows:
        enrollment_id = row.get("_id")
        if not enrollment_id:
            continue
        upd = await db.enrollments.update_one(
            {"id": enrollment_id},
            {"$set": {"payment_status": "paid", "updated_at": now}},
        )
        if upd.modified_count:
            updated_enrollments += 1

    print("repair complete")
    print(f"payments linked by order_id: {repaired_payment_links}")
    print(f"enrollments marked paid: {updated_enrollments}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())

