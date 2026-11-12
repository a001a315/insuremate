import secrets
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models import Claim, ClaimDocument
from app.models.claim import REJECTED_STATUSES
from app.repositories.entities import (ClaimDocumentRepository, ClaimRepository, DocumentRepository, PatientRepository,
                                          PolicyRepository)
from app.schemas.claim import ClaimCreate, ClaimUpdate, StatusChange
from app.services.activity import log_activity
from app.services.errors import NotFound, ValidationFailed


class ClaimService:
    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db, self.user_id = db, user_id
        self.repo = ClaimRepository(db, user_id)

    def get(self, claim_id: uuid.UUID) -> Claim:
        c = self.repo.get(claim_id)
        if not c:
            raise NotFound("Claim not found")
        return c

    def list(self, status=None, policy_id=None, patient_id=None):
        return self.repo.list_filtered(status, policy_id, patient_id)

    def create(self, data: ClaimCreate) -> Claim:
        policy = PolicyRepository(self.db, self.user_id).get(data.policy_id)
        if not policy:
            raise NotFound("Policy not found")
        patient = PatientRepository(self.db, self.user_id).get(data.patient_id)
        if not patient:
            raise NotFound("Patient not found")
        if policy.patient_id != patient.id:
            raise ValidationFailed("This policy is not recorded against the selected patient")
        values = data.model_dump(exclude={"claim_ref"})
        values["patient_name"] = patient.full_name
        if not values.get("hospital_name"):
            from app.models import User
            u = self.db.get(User, self.user_id)
            values["hospital_name"] = u.hospital_name or None
        ref = data.claim_ref or f"CLM-{date.today().year}-{secrets.token_hex(3).upper()}"
        if data.status != "draft" and not values.get("submission_date"):
            values["submission_date"] = date.today()
        c = Claim(**values, claim_ref=ref)
        self.repo.add(c)
        log_activity(self.db, self.user_id, "claim.created", "claim", c.id, f"Claim {c.claim_ref} created ({c.status})")
        return c

    def update(self, claim_id: uuid.UUID, data: ClaimUpdate) -> Claim:
        c = self.get(claim_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(c, k, v)
        if c.hospitalization_date and c.discharge_date and c.discharge_date < c.hospitalization_date:
            raise ValidationFailed("Discharge date cannot be before hospitalization date")
        self.repo.save(c)
        log_activity(self.db, self.user_id, "claim.updated", "claim", c.id, f"Claim {c.claim_ref} updated")
        return c

    def change_status(self, claim_id: uuid.UUID, data: StatusChange) -> Claim:
        c = self.get(claim_id)
        old = c.status
        c.status = data.status
        if data.approved_amount is not None:
            c.approved_amount = data.approved_amount
        if data.status == "submitted" and not c.submission_date:
            c.submission_date = date.today()
        if data.insurer_reference:
            c.insurer_reference = data.insurer_reference
        if data.status in REJECTED_STATUSES:
            c.rejection_reason = data.rejection_reason or c.rejection_reason
        elif data.status not in REJECTED_STATUSES:
            c.rejection_reason = None
        self.repo.save(c)
        log_activity(self.db, self.user_id, "claim.status_changed", "claim", c.id,
                     f"Claim {c.claim_ref}: {old.replace('_', ' ')} → {data.status.replace('_', ' ')} (manually updated by you)",
                     {"from": old, "to": data.status, "note": data.note})
        return c

    def add_note(self, claim_id: uuid.UUID, note: str) -> None:
        c = self.get(claim_id)
        log_activity(self.db, self.user_id, "claim.note_added", "claim", c.id, note[:300], {"note": note})

    def delete(self, claim_id: uuid.UUID) -> None:
        c = self.get(claim_id)
        self.repo.delete(c)
        log_activity(self.db, self.user_id, "claim.deleted", "claim", c.id, f"Claim {c.claim_ref} deleted")

    # documents
    def attach(self, claim_id: uuid.UUID, document_id: uuid.UUID) -> ClaimDocument:
        c = self.get(claim_id)
        doc = DocumentRepository(self.db, self.user_id).get(document_id)
        if not doc:
            raise NotFound("Document not found")
        cdr = ClaimDocumentRepository(self.db, self.user_id)
        existing = next((x for x in cdr.for_claim(c.id) if x.document_id == doc.id), None)
        if existing:
            return existing
        link = cdr.add(ClaimDocument(claim_id=c.id, document_id=doc.id))
        log_activity(self.db, self.user_id, "claim.document_attached", "claim", c.id,
                     f"Document attached to claim {c.claim_ref}: {doc.original_name}")
        return link

    def detach(self, claim_id: uuid.UUID, document_id: uuid.UUID) -> None:
        self.get(claim_id)
        cdr = ClaimDocumentRepository(self.db, self.user_id)
        for link in cdr.for_claim(claim_id):
            if link.document_id == document_id:
                cdr.delete(link)
                return
        raise NotFound("Document is not attached to this claim")

    def documents(self, claim_id: uuid.UUID):
        self.get(claim_id)
        docs = DocumentRepository(self.db, self.user_id)
        out = []
        for link in ClaimDocumentRepository(self.db, self.user_id).for_claim(claim_id):
            d = docs.get(link.document_id)
            if d:
                out.append(d)
        return out
