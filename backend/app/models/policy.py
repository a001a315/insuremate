import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import JSON, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class Policy(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "policies"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    insurer: Mapped[str] = mapped_column(String(200))
    policy_number: Mapped[str] = mapped_column(String(100))
    policy_type: Mapped[str] = mapped_column(String(50), default="individual")
    policyholder_name: Mapped[str] = mapped_column(String(200))
    sum_insured: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    premium_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    premium_frequency: Mapped[str] = mapped_column(String(20), default="annual")
    tpa_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    initial_waiting_days: Mapped[int] = mapped_column(Integer, default=30)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    renewal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active|expired|archived
    nominee: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Each detail field is {"value": ..., "source": "manual"|"extracted"|"ai_summary"}
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    members: Mapped[list["InsuredMember"]] = relationship(back_populates="policy", cascade="all, delete-orphan")


class InsuredMember(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "insured_members"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    relationship_to_holder: Mapped[str] = mapped_column(String(50), default="self")
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)

    policy: Mapped[Policy] = relationship(back_populates="members")
