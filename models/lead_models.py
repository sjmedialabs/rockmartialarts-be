from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional
import uuid


class LeadCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field(..., min_length=5, max_length=32)
    course: str = Field(default="", max_length=300)
    source: Optional[str] = Field(default=None, max_length=80)

    class Config:
        extra = "ignore"


class LeadResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    course: str
    source: Optional[str] = None
    created_at: datetime
