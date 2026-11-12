import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["discharge_summary", "prescription", "diagnostic_report", "lab_report",
                   "medical_bill", "consultation", "surgery", "other"]


class RecordBase(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    category: Category
    patient_id: uuid.UUID
    provider: str | None = Field(default=None, max_length=200)
    record_date: date | None = None
    claim_id: uuid.UUID | None = None
    policy_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)


class RecordCreate(RecordBase):
    pass


class RecordUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    category: Category | None = None
    provider: str | None = None
    record_date: date | None = None
    claim_id: uuid.UUID | None = None
    policy_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    notes: str | None = None


class RecordOut(RecordBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    patient_name: str
    created_at: datetime
