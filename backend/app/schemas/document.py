import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

DOC_CATEGORIES = ["policy_document", "policy_schedule", "premium_receipt", "claim_form",
                  "hospital_bill", "discharge_summary", "medical_report", "other"]
INDEXED_CATEGORIES = {"policy_document", "policy_schedule"}


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    policy_id: uuid.UUID | None
    patient_id: uuid.UUID | None = None
    original_name: str
    mime_type: str
    size_bytes: int
    category: str
    index_status: str
    index_error: str | None
    page_count: int | None
    created_at: datetime
    indexed_at: datetime | None
