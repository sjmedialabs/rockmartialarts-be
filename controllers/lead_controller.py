from fastapi import HTTPException, status
from datetime import datetime
from typing import Any, Dict, List, Optional
import os
import uuid

from models.lead_models import LeadCreate, LeadResponse
from utils.database import get_db
from utils.helpers import serialize_doc

# Must match Next.js default LEAD_CAPTURE_PLACEHOLDER_EMAIL (website popup, no email field)
_LEAD_EMAIL_PLACEHOLDER = (os.getenv("LEAD_EMAIL_PLACEHOLDER") or "website-popup@example.com").strip().lower()


class LeadController:
    @staticmethod
    async def create_lead(data: LeadCreate) -> LeadResponse:
        try:
            db = get_db()
            now = datetime.utcnow()
            email_raw = (data.email or "").strip().lower() if data.email else ""
            if email_raw == _LEAD_EMAIL_PLACEHOLDER:
                email_raw = ""
            doc: Dict[str, Any] = {
                "id": str(uuid.uuid4()),
                "name": data.name.strip(),
                "email": email_raw,
                "phone": data.phone.strip(),
                "course": (data.course or "").strip(),
                "source": (data.source or "").strip() or None,
                "branch_id": (data.branch_id or "").strip() or None,
                "branch_name": (data.branch_name or "").strip() or None,
                "created_at": now,
            }
            await db.leads.insert_one(doc)
            ser = serialize_doc(doc)
            return LeadResponse(
                id=ser["id"],
                name=ser["name"],
                email=ser["email"],
                phone=ser["phone"],
                course=ser.get("course", ""),
                source=ser.get("source"),
                branch_id=ser.get("branch_id"),
                branch_name=ser.get("branch_name"),
                created_at=ser.get("created_at", now),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save lead: {str(e)}",
            )

    @staticmethod
    async def list_leads(skip: int = 0, limit: int = 50, search: Optional[str] = None) -> Dict[str, Any]:
        try:
            db = get_db()
            q: Dict[str, Any] = {}
            if search and search.strip():
                s = search.strip()
                q = {
                    "$or": [
                        {"name": {"$regex": s, "$options": "i"}},
                        {"email": {"$regex": s, "$options": "i"}},
                        {"phone": {"$regex": s, "$options": "i"}},
                        {"course": {"$regex": s, "$options": "i"}},
                        {"branch_name": {"$regex": s, "$options": "i"}},
                        {"branch_id": {"$regex": s, "$options": "i"}},
                    ]
                }
            limit = min(max(limit, 1), 200)
            skip = max(skip, 0)
            cursor = db.leads.find(q).sort("created_at", -1).skip(skip).limit(limit)
            items: List[LeadResponse] = []
            for raw in await cursor.to_list(length=limit):
                ser = serialize_doc(raw)
                items.append(
                    LeadResponse(
                        id=ser["id"],
                        name=ser.get("name", ""),
                        email=ser.get("email") or "",
                        phone=ser.get("phone", ""),
                        course=ser.get("course", ""),
                        source=ser.get("source"),
                        branch_id=ser.get("branch_id"),
                        branch_name=ser.get("branch_name"),
                        created_at=ser.get("created_at", datetime.utcnow()),
                    )
                )
            total = await db.leads.count_documents(q)
            return {"leads": items, "total": total, "skip": skip, "limit": limit}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list leads: {str(e)}",
            )
