import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

CLAIM_STATUSES = [
    "draft", "pre_auth_requested", "pre_auth_approved", "pre_auth_rejected", "submitted", "under_review",
    "additional_documents_required", "approved", "partially_approved", "rejected", "settled",
]
PENDING_STATUSES = {"pre_auth_requested", "submitted", "under_review", "additional_documents_required"}
CLEARED_STATUSES = {"approved", "partially_approved", "settled"}
REJECTED_STATUSES = {"rejected", "pre_auth_rejected"}


def clearance_of(status: str) -> str:
    """Plain-language outcome for hospital staff: cleared / pre_auth_cleared / pending / rejected / draft."""
    if status in CLEARED_STATUSES:
        return "cleared"
    if status == "pre_auth_approved":
        return "pre_auth_cleared"
    if status in REJECTED_STATUSES:
        return "rejected"
    return "draft" if status == "draft" else "pending"


class Claim(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "claims"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=True, index=True)
    claim_ref: Mapped[str] = mapped_column(String(50))
    insurer_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    patient_name: Mapped[str] = mapped_column(String(200))
    hospital_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hospitalization_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    discharge_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    claim_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    approved_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    claim_type: Mapped[str] = mapped_column(String(30), default="reimbursement")  # cashless|reimbursement
    submission_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    policy: Mapped["Policy"] = relationship("Policy", lazy="joined", viewonly=True)

    @property
    def clearance(self) -> str:
        return clearance_of(self.status)

    @property
    def insurer(self) -> str | None:
        return self.policy.insurer if self.policy else None


class ClaimDocument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "claim_documents"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
