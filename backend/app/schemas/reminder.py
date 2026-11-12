import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReminderBase(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    kind: Literal["renewal", "premium", "claim_documents", "claim_followup", "preauth_followup", "custom"] = "custom"
    due_date: date
    policy_id: uuid.UUID | None = None
    claim_id: uuid.UUID | None = None


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    due_date: date | None = None
    is_completed: bool | None = None


class ReminderOut(ReminderBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    is_completed: bool
    is_auto: bool


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    body: str | None
    is_read: bool
    created_at: datetime
