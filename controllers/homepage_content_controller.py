from datetime import datetime
from typing import Any, Dict

from fastapi import HTTPException

from models.homepage_content_models import HomepageAboutUpdate
from utils.database import get_db
from utils.helpers import serialize_doc

COLLECTION = "homepage_content"
DOC_ID = "site"


def _default_about() -> Dict[str, Any]:
    return {
        "title": "",
        "subtitle": "",
        "content": "",
        "image": "",
    }


async def get_public() -> Dict[str, Any]:
    db = get_db()
    doc = await db[COLLECTION].find_one({"id": DOC_ID})
    if not doc:
        return {"about": _default_about()}
    about = doc.get("about") or {}
    merged = {**_default_about(), **{k: v for k, v in about.items() if v is not None}}
    return {"about": merged}


async def update_about(data: HomepageAboutUpdate, current_user: dict) -> Dict[str, Any]:
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admin can update homepage content")
    db = get_db()
    now = datetime.utcnow()
    patch = data.dict(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    existing = await db[COLLECTION].find_one({"id": DOC_ID})
    about = {**_default_about(), **((existing or {}).get("about") or {})}
    about.update(patch)

    await db[COLLECTION].update_one(
        {"id": DOC_ID},
        {
            "$set": {
                "id": DOC_ID,
                "about": about,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    saved = await db[COLLECTION].find_one({"id": DOC_ID})
    return serialize_doc(saved or {"id": DOC_ID, "about": about})
