import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import Money

ClaimStatus = Literal["draft", "pre_auth_requested", "pre_auth_approved", "pre_auth_rejected", "submitted", "under_review", "additional_documents_required",
                      "approved", "partially_approved", "rejected", "settled"]


class ClaimBase(BaseModel):
    policy_id: uuid.UUID
    patient_id: uuid.UUID
    hospital_name: str | None = Field(default=None, max_length=200)
    hospitalization_date: date | None = None
    discharge_date: date | None = None
    claim_amount: Money = Field(default=Decimal(0), ge=0)
    claim_type: Literal["cashless", "reimbursement"] = "reimbursement"
    submission_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def dates_ordered(self):
        if self.hospitalization_date and self.discharge_date and self.discharge_date < self.hospitalization_date:
            raise ValueError("Discharge date cannot be before hospitalization date")
        return self


class ClaimCreate(ClaimBase):
    insurer_reference: str | None = Field(default=None, max_length=100)
    rejection_reason: str | None = Field(default=None, max_length=2000)
    approved_amount: Money | None = Field(default=None, ge=0)
    claim_ref: str | None = Field(default=None, max_length=50)
    status: ClaimStatus = "draft"


class ClaimUpdate(BaseModel):
    insurer_reference: str | None = Field(default=None, max_length=100)
    rejection_reason: str | None = Field(default=None, max_length=2000)
    hospital_name: str | None = None
    hospitalization_date: date | None = None
    discharge_date: date | None = None
    claim_amount: Money | None = Field(default=None, ge=0)
    approved_amount: Money | None = Field(default=None, ge=0)
    claim_type: Literal["cashless", "reimbursement"] | None = None
    submission_date: date | None = None
    notes: str | None = None


class StatusChange(BaseModel):
    status: ClaimStatus
    rejection_reason: str | None = Field(default=None, max_length=2000)
    insurer_reference: str | None = Field(default=None, max_length=100)
    approved_amount: Money | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=1000)


class NoteIn(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class AttachIn(BaseModel):
    document_id: uuid.UUID


class ClaimOut(ClaimBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    claim_ref: str
    patient_name: str
    insurer_reference: str | None = None
    rejection_reason: str | None = None
    clearance: str = "pending"
    insurer: str | None = None
    status: str
    approved_amount: Money | None
    created_at: datetime
    updated_at: datetime
