import uuid
from datetime import date

from pydantic import BaseModel, Field


class EligibilityRequest(BaseModel):
    policy_id: uuid.UUID | None = None            # None = check all of the patient's policies
    admission_date: date | None = None            # default: today
    estimated_amount: float | None = Field(default=None, ge=0)
    treatment: str | None = Field(default=None, max_length=300)
    is_emergency_or_accident: bool = False        # initial waiting period does not apply to accidents


class CheckOut(BaseModel):
    key: str
    label: str
    status: str   # pass | fail | warn | info | unknown
    detail: str
    source: str   # recorded_data | hospital_setup


class EligibilityOut(BaseModel):
    policy_id: uuid.UUID
    policy_name: str
    insurer: str
    verdict: str   # eligible_cashless | eligible_reimbursement | needs_review | not_eligible
    verdict_label: str
    checks: list[CheckOut]
    disclaimer: str
