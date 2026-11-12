import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class HospitalProfile(BaseModel):
    hospital_name: str = Field(min_length=1, max_length=200)
    hospital_city: str | None = Field(default=None, max_length=100)


class EmpanelmentIn(BaseModel):
    insurer: str = Field(min_length=1, max_length=200)
    tpa_name: str | None = Field(default=None, max_length=200)
    cashless_enabled: bool = True
    valid_until: date | None = None
    notes: str | None = Field(default=None, max_length=1000)


class EmpanelmentUpdate(BaseModel):
    insurer: str | None = Field(default=None, min_length=1, max_length=200)
    tpa_name: str | None = None
    cashless_enabled: bool | None = None
    valid_until: date | None = None
    notes: str | None = None


class EmpanelmentOut(EmpanelmentIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
