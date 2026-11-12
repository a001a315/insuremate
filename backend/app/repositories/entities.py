import uuid
from datetime import date

from sqlalchemy import or_, select

from app.models import (ActivityLog, Empanelment, Patient, Claim, ClaimDocument, Conversation, Document, DocumentChunk, MedicalRecord,
                        Message, Notification, Policy, Reminder)
from app.repositories.base import OwnedRepository


class PatientRepository(OwnedRepository[Patient]):
    model = Patient

    def search(self, q: str | None = None) -> list[Patient]:
        stmt = self.query().order_by(Patient.full_name)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Patient.full_name.ilike(like), Patient.mrn.ilike(like), Patient.phone.ilike(like)))
        return list(self.db.scalars(stmt))


class EmpanelmentRepository(OwnedRepository[Empanelment]):
    model = Empanelment

    def list_sorted(self) -> list[Empanelment]:
        return list(self.db.scalars(self.query().order_by(Empanelment.insurer)))


class PolicyRepository(OwnedRepository[Policy]):
    model = Policy

    def list_filtered(self, include_archived: bool = False, patient_id: uuid.UUID | None = None) -> list[Policy]:
        q = self.query().order_by(Policy.expiry_date.is_(None), Policy.expiry_date)
        if not include_archived:
            q = q.where(Policy.status != "archived")
        if patient_id:
            q = q.where(Policy.patient_id == patient_id)
        return list(self.db.scalars(q))


class ClaimRepository(OwnedRepository[Claim]):
    model = Claim

    def list_filtered(self, status: str | None = None, policy_id: uuid.UUID | None = None,
                      patient_id: uuid.UUID | None = None) -> list[Claim]:
        q = self.query().order_by(Claim.created_at.desc())
        if patient_id:
            q = q.where(Claim.patient_id == patient_id)
        if status:
            q = q.where(Claim.status == status)
        if policy_id:
            q = q.where(Claim.policy_id == policy_id)
        return list(self.db.scalars(q))


class ClaimDocumentRepository(OwnedRepository[ClaimDocument]):
    model = ClaimDocument

    def for_claim(self, claim_id: uuid.UUID) -> list[ClaimDocument]:
        return list(self.db.scalars(self.query().where(ClaimDocument.claim_id == claim_id)))


class DocumentRepository(OwnedRepository[Document]):
    model = Document

    def list_filtered(self, q: str | None = None, category: str | None = None, policy_id: uuid.UUID | None = None,
                      patient_id: uuid.UUID | None = None):
        stmt = self.query().order_by(Document.created_at.desc())
        if patient_id:
            stmt = stmt.where(Document.patient_id == patient_id)
        if q:
            stmt = stmt.where(Document.original_name.ilike(f"%{q}%"))
        if category:
            stmt = stmt.where(Document.category == category)
        if policy_id:
            stmt = stmt.where(Document.policy_id == policy_id)
        return list(self.db.scalars(stmt))


class ChunkRepository(OwnedRepository[DocumentChunk]):
    model = DocumentChunk

    def for_document(self, document_id: uuid.UUID) -> list[DocumentChunk]:
        return list(self.db.scalars(self.query().where(DocumentChunk.document_id == document_id)
                                    .order_by(DocumentChunk.chunk_index)))


class MedicalRecordRepository(OwnedRepository[MedicalRecord]):
    model = MedicalRecord

    def search(self, q=None, category=None, date_from: date | None = None, date_to: date | None = None,
               claim_id=None, policy_id=None, patient_id=None) -> list[MedicalRecord]:
        stmt = self.query().order_by(MedicalRecord.record_date.desc().nulls_last(), MedicalRecord.created_at.desc())
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(MedicalRecord.title.ilike(like), MedicalRecord.patient_name.ilike(like),
                                  MedicalRecord.provider.ilike(like), MedicalRecord.notes.ilike(like)))
        if category:
            stmt = stmt.where(MedicalRecord.category == category)
        if date_from:
            stmt = stmt.where(MedicalRecord.record_date >= date_from)
        if date_to:
            stmt = stmt.where(MedicalRecord.record_date <= date_to)
        if patient_id:
            stmt = stmt.where(MedicalRecord.patient_id == patient_id)
        if claim_id:
            stmt = stmt.where(MedicalRecord.claim_id == claim_id)
        if policy_id:
            stmt = stmt.where(MedicalRecord.policy_id == policy_id)
        return list(self.db.scalars(stmt))


class ReminderRepository(OwnedRepository[Reminder]):
    model = Reminder


class NotificationRepository(OwnedRepository[Notification]):
    model = Notification

    def recent(self, limit: int = 50) -> list[Notification]:
        return list(self.db.scalars(self.query().order_by(Notification.created_at.desc()).limit(limit)))


class ActivityRepository(OwnedRepository[ActivityLog]):
    model = ActivityLog

    def recent(self, limit: int = 20, entity_id: uuid.UUID | None = None) -> list[ActivityLog]:
        q = self.query().order_by(ActivityLog.created_at.desc()).limit(limit)
        if entity_id:
            q = q.where(ActivityLog.entity_id == entity_id)
        return list(self.db.scalars(q))


class ConversationRepository(OwnedRepository[Conversation]):
    model = Conversation

    def list_recent(self) -> list[Conversation]:
        return list(self.db.scalars(self.query().order_by(Conversation.updated_at.desc())))


class MessageRepository(OwnedRepository[Message]):
    model = Message

    def for_conversation(self, conversation_id: uuid.UUID) -> list[Message]:
        return list(self.db.scalars(self.query().where(Message.conversation_id == conversation_id)
                                    .order_by(Message.created_at, Message.id)))
