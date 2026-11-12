import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import Money

DETAIL_KEYS = {"covered_conditions", "exclusions", "waiting_periods", "room_rent_limit", "copay",
               "network_hospitals", "restoration_benefit", "no_claim_bonus"}
Source = Literal["manual", "extracted", "ai_summary"]


class DetailField(BaseModel):
    value: str = Field(max_length=10000)
    source: Source = "manual"


class MemberIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    relationship_to_holder: str = Field(default="self", max_length=50)
    date_of_birth: date | None = None


class MemberOut(MemberIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class PolicyBase(BaseModel):
    patient_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    insurer: str = Field(min_length=1, max_length=200)
    policy_number: str = Field(min_length=1, max_length=100)
    policy_type: Literal["individual", "family_floater", "senior_citizen", "critical_illness", "top_up", "group"] = "individual"
    policyholder_name: str = Field(min_length=1, max_length=200)
    sum_insured: Money = Field(ge=0)
    premium_amount: Money = Field(default=Decimal(0), ge=0)
    premium_frequency: Literal["monthly", "quarterly", "half_yearly", "annual"] = "annual"
    tpa_name: str | None = Field(default=None, max_length=200)
    initial_waiting_days: int = Field(default=30, ge=0, le=3650)
    start_date: date | None = None
    expiry_date: date | None = None
    renewal_date: date | None = None
    nominee: dict[str, str] | None = None
    details: dict[str, DetailField] = Field(default_factory=dict)

    @field_validator("details")
    @classmethod
    def known_keys(cls, v):
        bad = set(v) - DETAIL_KEYS
        if bad:
            raise ValueError(f"Unknown detail fields: {sorted(bad)}")
        return v


class PolicyCreate(PolicyBase):
    members: list[MemberIn] = Field(default_factory=list)


class PolicyUpdate(BaseModel):
    """Partial update; only provided fields change, so documents need not be re-uploaded."""
    patient_id: uuid.UUID | None = None
    tpa_name: str | None = None
    initial_waiting_days: int | None = Field(default=None, ge=0, le=3650)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    insurer: str | None = Field(default=None, min_length=1, max_length=200)
    policy_number: str | None = Field(default=None, min_length=1, max_length=100)
    policy_type: str | None = None
    policyholder_name: str | None = None
    sum_insured: Money | None = Field(default=None, ge=0)
    premium_amount: Money | None = Field(default=None, ge=0)
    premium_frequency: Literal["monthly", "quarterly", "half_yearly", "annual"] | None = None
    start_date: date | None = None
    expiry_date: date | None = None
    renewal_date: date | None = None
    status: Literal["active", "expired"] | None = None
    nominee: dict[str, str] | None = None
    details: dict[str, DetailField] | None = None
    members: list[MemberIn] | None = None

    @field_validator("details")
    @classmethod
    def known_keys(cls, v):
        if v and set(v) - DETAIL_KEYS:
            raise ValueError("Unknown detail fields")
        return v


class PolicyListOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID | None = None
    patient_name: str | None = None
    tpa_name: str | None = None
    network_status: str = "unknown"  # empanelled_cashless | empanelled_no_cashless | not_empanelled | expired
    name: str
    insurer: str
    masked_policy_number: str
    policy_type: str
    sum_insured: Money
    premium_amount: Money
    premium_frequency: str
    expiry_date: date | None
    renewal_date: date | None
    status: str


class PolicyOut(PolicyBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    network_status: str = "unknown"
    status: str
    ai_summary: str | None
    members: list[MemberOut]
    created_at: datetime
    updated_at: datetime
