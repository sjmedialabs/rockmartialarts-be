from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class LeadCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    # Website popup may capture phone + branch only
    email: Optional[str] = Field(default=None, max_length=200)
    phone: str = Field(..., min_length=5, max_length=32)
    course: str = Field(default="", max_length=300)
    source: Optional[str] = Field(default=None, max_length=80)
    branch_id: Optional[str] = Field(default=None, max_length=64)
    branch_name: Optional[str] = Field(default=None, max_length=200)

    class Config:
        extra = "ignore"


class LeadResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    course: str
    source: Optional[str] = None
    branch_id: Optional[str] = None
    branch_name: Optional[str] = None
    created_at: datetime
