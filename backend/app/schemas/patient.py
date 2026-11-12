import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PatientBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    mrn: str | None = Field(default=None, max_length=50)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=5000)


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    mrn: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    phone: str | None = None
    notes: str | None = None


class PatientOut(PatientBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime


class PatientListOut(PatientOut):
    active_policies: int = 0
    open_claims: int = 0
    latest_claim_status: str | None = None
    latest_clearance: str | None = None
    insurance_state: str = "no_policy"  # active | expiring_soon | expired | no_policy
