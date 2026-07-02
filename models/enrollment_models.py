from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid
from enum import Enum

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class BeneficiaryInfo(BaseModel):
    beneficiary_type: str = "self"  # "self" | "family" | "friend" | "other"
    beneficiary_name: Optional[str] = None
    beneficiary_phone: Optional[str] = None
    beneficiary_relationship: Optional[str] = None

class Enrollment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    course_id: str
    branch_id: str
    enrollment_date: datetime = Field(default_factory=datetime.utcnow)
    start_date: datetime
    end_date: datetime
    fee_amount: float
    admission_fee: float = 500.0
    payment_status: PaymentStatus = PaymentStatus.PENDING
    next_due_date: Optional[datetime] = None
    is_active: bool = True
    duration_id: Optional[str] = None
    batch_ref: Optional[str] = None
    beneficiary: Optional[BeneficiaryInfo] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class EnrollmentCreate(BaseModel):
    student_id: str
    course_id: str
    branch_id: str
    start_date: datetime
    fee_amount: float
    admission_fee: float = 500.0
    duration_id: Optional[str] = None
    beneficiary: Optional[BeneficiaryInfo] = None
