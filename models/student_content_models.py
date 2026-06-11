"""Marketing testimonials and showcase achievements (separate from enrollment-linked student_achievements)."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, Literal
import uuid


class CreatedByMeta(BaseModel):
    role: Literal["super_admin", "branch_manager"]
    user_id: str


class StudentTestimonialCreate(BaseModel):
    student_name: str = Field(..., min_length=1)
    student_photo: Optional[str] = None
    image: Optional[str] = Field(None, description="Image URL; stored with student_photo for compatibility")
    testimonial_text: str = Field(..., min_length=1)
    rating: Optional[float] = Field(None, ge=0, le=5)
    branch_id: Optional[str] = None
    is_global: bool = False
    status: Literal["active", "inactive"] = "active"
    display_order: int = 0


class StudentTestimonialUpdate(BaseModel):
    student_name: Optional[str] = Field(None, min_length=1)
    student_photo: Optional[str] = None
    image: Optional[str] = None
    testimonial_text: Optional[str] = Field(None, min_length=1)
    rating: Optional[float] = Field(None, ge=0, le=5)
    branch_id: Optional[str] = None
    is_global: Optional[bool] = None
    status: Optional[Literal["active", "inactive"]] = None
    display_order: Optional[int] = None


class StudentShowcaseAchievementCreate(BaseModel):
    student_name: str = Field(..., min_length=1)
    student_photo: Optional[str] = None
    achievement_title: str = Field(..., min_length=1)
    description: Optional[str] = None
    image: Optional[str] = None
    branch_id: Optional[str] = None
    course_id: Optional[str] = None
    is_global: bool = False
    status: Literal["active", "inactive"] = "active"
    display_order: int = 0


class StudentShowcaseAchievementUpdate(BaseModel):
    student_name: Optional[str] = Field(None, min_length=1)
    student_photo: Optional[str] = None
    achievement_title: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    image: Optional[str] = None
    branch_id: Optional[str] = None
    course_id: Optional[str] = None
    is_global: Optional[bool] = None
    status: Optional[Literal["active", "inactive"]] = None
    display_order: Optional[int] = None


def new_doc_id() -> str:
    return str(uuid.uuid4())


def stamp_created_by(current_user: dict) -> Dict[str, Any]:
    role = current_user.get("role") or ""
    if role == "super_admin":
        r = "super_admin"
    elif role == "branch_manager":
        r = "branch_manager"
    else:
        r = "branch_manager"
    return {"role": r, "user_id": current_user.get("id") or ""}
