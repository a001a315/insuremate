import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class Patient(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A patient of the hospital account (the tenant). Policies, claims and records hang off a patient."""
    __tablename__ = "patients"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    mrn: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)  # hospital UHID / MRN
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Empanelment(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Which insurers/TPAs this hospital has a network (cashless) arrangement with."""
    __tablename__ = "hospital_empanelments"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    insurer: Mapped[str] = mapped_column(String(200), index=True)
    tpa_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cashless_enabled: Mapped[bool] = mapped_column(default=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
