from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum
import uuid


class EnrollmentBranchChangeStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EnrollmentBranchChangeRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    enrollment_id: str
    student_id: str
    current_branch_id: str
    new_branch_id: str
    reason: str
    status: EnrollmentBranchChangeStatus = EnrollmentBranchChangeStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EnrollmentBranchChangeCreate(BaseModel):
    new_branch_id: str
    reason: Optional[str] = "Student requested branch change"
