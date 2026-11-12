import uuid

from sqlalchemy.orm import Session

from app.models import MedicalRecord
from app.repositories.entities import (ClaimRepository, DocumentRepository, MedicalRecordRepository, PatientRepository,
                                          PolicyRepository)
from app.schemas.medical_record import RecordCreate, RecordUpdate
from app.services.activity import log_activity
from app.services.errors import NotFound


class MedicalRecordService:
    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db, self.user_id = db, user_id
        self.repo = MedicalRecordRepository(db, user_id)

    def _check_links(self, claim_id, policy_id, document_id):
        if claim_id and not ClaimRepository(self.db, self.user_id).get(claim_id):
            raise NotFound("Claim not found")
        if policy_id and not PolicyRepository(self.db, self.user_id).get(policy_id):
            raise NotFound("Policy not found")
        if document_id and not DocumentRepository(self.db, self.user_id).get(document_id):
            raise NotFound("Document not found")

    def get(self, record_id: uuid.UUID) -> MedicalRecord:
        r = self.repo.get(record_id)
        if not r:
            raise NotFound("Record not found")
        return r

    def create(self, data: RecordCreate) -> MedicalRecord:
        self._check_links(data.claim_id, data.policy_id, data.document_id)
        patient = PatientRepository(self.db, self.user_id).get(data.patient_id)
        if not patient:
            raise NotFound("Patient not found")
        r = self.repo.add(MedicalRecord(**data.model_dump(), patient_name=patient.full_name))
        log_activity(self.db, self.user_id, "record.created", "medical_record", r.id, f"Medical record added ({r.category})")
        return r

    def update(self, record_id: uuid.UUID, data: RecordUpdate) -> MedicalRecord:
        r = self.get(record_id)
        changes = data.model_dump(exclude_unset=True)
        self._check_links(changes.get("claim_id"), changes.get("policy_id"), changes.get("document_id"))
        for k, v in changes.items():
            setattr(r, k, v)
        return self.repo.save(r)

    def delete(self, record_id: uuid.UUID) -> None:
        self.repo.delete(self.get(record_id))
