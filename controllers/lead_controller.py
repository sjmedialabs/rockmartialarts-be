from fastapi import HTTPException, status
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from models.lead_models import LeadCreate, LeadResponse
from utils.database import get_db
from utils.helpers import serialize_doc


class LeadController:
    @staticmethod
    async def create_lead(data: LeadCreate) -> LeadResponse:
        try:
            db = get_db()
            now = datetime.utcnow()
            doc: Dict[str, Any] = {
                "id": str(uuid.uuid4()),
                "name": data.name.strip(),
                "email": str(data.email).strip().lower(),
                "phone": data.phone.strip(),
                "course": (data.course or "").strip(),
                "source": (data.source or "").strip() or None,
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
                        email=ser.get("email", ""),
                        phone=ser.get("phone", ""),
                        course=ser.get("course", ""),
                        source=ser.get("source"),
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
