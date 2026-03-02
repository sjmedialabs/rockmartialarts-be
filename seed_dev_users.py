#!/usr/bin/env python3
"""
Seed script to create development login users for the Marshal Arts LMS.
Run from project root: python3 seed_dev_users.py
Requires: MONGO_URL and DB_NAME in .env (or set in environment).

Creates:
- Super Admin: admin@marshalats.com / admin123
- Branch Manager: branchmanager@test.com / TestPass123
- Student: student@test.com / testpass123
"""

import asyncio
import os
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from utils.auth import hash_password

# Load .env from backend directory
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Credentials to create (email, password, role)
SUPERADMIN_EMAIL = "admin@marshalats.com"
SUPERADMIN_PASSWORD = "admin123"
BRANCH_MANAGER_EMAIL = "branchmanager@test.com"
BRANCH_MANAGER_PASSWORD = "TestPass123"
STUDENT_EMAIL = "student@test.com"
STUDENT_PASSWORD = "testpass123"


async def seed():
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "marshalats")

    print(f"Connecting to MongoDB (db: {db_name})...")
    # Match server.py: allow insecure TLS for Atlas if needed (e.g. macOS cert issues)
    client = AsyncIOMotorClient(mongo_url, tlsAllowInvalidCertificates=True)
    db = client[db_name]

    created = []

    # 1. Super Admin (create or reset password so login works)
    existing_superadmin = await db.superadmins.find_one({"email": SUPERADMIN_EMAIL})
    if existing_superadmin:
        await db.superadmins.update_one(
            {"email": SUPERADMIN_EMAIL},
            {"$set": {"password_hash": hash_password(SUPERADMIN_PASSWORD), "updated_at": datetime.utcnow()}},
        )
        print(f"  Super Admin exists, password reset to: {SUPERADMIN_PASSWORD}")
    else:
        admin_id = str(uuid.uuid4())
        await db.superadmins.insert_one({
            "id": admin_id,
            "full_name": "Super Administrator",
            "email": SUPERADMIN_EMAIL,
            "phone": "+1234567890",
            "password_hash": hash_password(SUPERADMIN_PASSWORD),
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        created.append("Super Admin")
        print(f"  Created Super Admin: {SUPERADMIN_EMAIL} / {SUPERADMIN_PASSWORD}")

    # 2. Branch Manager (minimal document for login)
    existing_bm = await db.branch_managers.find_one({"email": BRANCH_MANAGER_EMAIL})
    bm_pw_hash = hash_password(BRANCH_MANAGER_PASSWORD)
    if existing_bm:
        await db.branch_managers.update_one(
            {"email": BRANCH_MANAGER_EMAIL},
            {"$set": {"password_hash": bm_pw_hash, "updated_at": datetime.utcnow()}},
        )
        print(f"  Branch Manager password reset: {BRANCH_MANAGER_EMAIL} / {BRANCH_MANAGER_PASSWORD}")
    else:
        bm_id = str(uuid.uuid4())
        await db.branch_managers.insert_one({
            "id": bm_id,
            "email": BRANCH_MANAGER_EMAIL,
            "phone": "+1234567891",
            "first_name": "Branch",
            "last_name": "Manager",
            "full_name": "Branch Manager",
            "password_hash": bm_pw_hash,
            "is_active": True,
            "personal_info": {
                "first_name": "Branch",
                "last_name": "Manager",
                "gender": "Other",
                "date_of_birth": "1990-01-01",
            },
            "contact_info": {
                "email": BRANCH_MANAGER_EMAIL,
                "country_code": "+1",
                "phone": "1234567891",
            },
            "address_info": {
                "address": "123 Test St",
                "city": "Test City",
                "state": "TS",
                "country": "India",
            },
            "professional_info": {
                "designation": "Branch Manager",
                "education_qualification": "B.Com",
                "professional_experience": "2 years",
                "certifications": [],
            },
            "branch_assignment": None,
            "emergency_contact": None,
            "notes": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        created.append("Branch Manager")
        print(f"  Created Branch Manager: {BRANCH_MANAGER_EMAIL} / {BRANCH_MANAGER_PASSWORD}")

    # 3. Student (user in users collection)
    existing_user = await db.users.find_one({"email": STUDENT_EMAIL})
    pw_hash = hash_password(STUDENT_PASSWORD)
    if existing_user:
        await db.users.update_one(
            {"email": STUDENT_EMAIL},
            {"$set": {"password": pw_hash, "updated_at": datetime.utcnow()}},
        )
        print(f"  Student password reset: {STUDENT_EMAIL} / {STUDENT_PASSWORD}")
    else:
        user_id = str(uuid.uuid4())
        await db.users.insert_one({
            "id": user_id,
            "email": STUDENT_EMAIL,
            "phone": "+1234567892",
            "first_name": "Test",
            "last_name": "Student",
            "full_name": "Test Student",
            "role": "student",
            "password": pw_hash,
            "is_active": True,
            "date_of_birth": None,
            "gender": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        created.append("Student")
        print(f"  Created Student: {STUDENT_EMAIL} / {STUDENT_PASSWORD}")

    client.close()

    if created:
        print(f"\nDone. Created: {', '.join(created)}.")
    else:
        print("\nNo new users created (all already exist).")

    print("\n--- Login credentials ---")
    print("Super Admin:    ", "http://localhost:3022/superadmin/login", "->", SUPERADMIN_EMAIL, "/", SUPERADMIN_PASSWORD)
    print("Branch Manager: ", "http://localhost:3022/branch-manager/login", "->", BRANCH_MANAGER_EMAIL, "/", BRANCH_MANAGER_PASSWORD)
    print("Student:        ", "http://localhost:3022/login", "->", STUDENT_EMAIL, "/", STUDENT_PASSWORD)


if __name__ == "__main__":
    asyncio.run(seed())
