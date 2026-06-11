"""
One-off migration: testimonial image alias, optional homepage_content seed.
Run from repo root: python3 scripts/migrate_feature_fields.py

Requires MONGO_URL / DB_NAME (or defaults).
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402


async def main():
    mongo_url = os.getenv("MONGO_URL") or os.getenv("MONGO_URI") or "mongodb://localhost:27017"
    db_name = os.getenv("DB_NAME", "marshalats")
    client = AsyncIOMotorClient(mongo_url, tlsInsecure=True)
    db = client[db_name]

    # Testimonials: copy student_photo -> image when image missing
    col = db["student_testimonials"]
    cursor = col.find({"$or": [{"image": {"$exists": False}}, {"image": None}, {"image": ""}]})
    n = 0
    async for doc in cursor:
        photo = doc.get("student_photo")
        if photo:
            await col.update_one({"id": doc["id"]}, {"$set": {"image": photo}})
            n += 1
    print(f"student_testimonials: synced image from student_photo on {n} documents")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
