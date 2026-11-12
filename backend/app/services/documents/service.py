import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import ClaimDocument, Document, MedicalRecord
from app.repositories.entities import ChunkRepository, DocumentRepository, PatientRepository, PolicyRepository
from app.schemas.document import DOC_CATEGORIES
from app.services.activity import log_activity
from app.services.errors import NotFound, ValidationFailed
from app.services.rag import vectorstore
from app.utils.files import MIME_BY_EXT, safe_display_name, sniff_mime


class DocumentService:
    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db, self.user_id = db, user_id
        self.repo = DocumentRepository(db, user_id)
        self.settings = get_settings()

    def user_dir(self) -> Path:
        d = Path(self.settings.upload_dir) / str(self.user_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get(self, doc_id: uuid.UUID) -> Document:
        d = self.repo.get(doc_id)
        if not d:
            raise NotFound("Document not found")
        return d

    def path_for(self, doc: Document) -> Path:
        return Path(self.settings.upload_dir) / str(doc.user_id) / doc.stored_name

    async def upload(self, file: UploadFile, category: str, policy_id: uuid.UUID | None,
                     patient_id: uuid.UUID | None = None) -> Document:
        s = self.settings
        if category not in DOC_CATEGORIES:
            raise ValidationFailed(f"Unknown category. Choose one of: {', '.join(DOC_CATEGORIES)}")
        if policy_id:
            policy = PolicyRepository(self.db, self.user_id).get(policy_id)
            if not policy:
                raise NotFound("Policy not found")
            if patient_id and policy.patient_id and policy.patient_id != patient_id:
                raise ValidationFailed("This policy belongs to a different patient")
            patient_id = patient_id or policy.patient_id  # a policy document belongs to the policy's patient
        if patient_id and not PatientRepository(self.db, self.user_id).get(patient_id):
            raise NotFound("Patient not found")
        name = safe_display_name(file.filename or "document")
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in s.allowed_extension_set:
            raise ValidationFailed(f"File type '.{ext}' is not allowed. Allowed: {', '.join(sorted(s.allowed_extension_set))}")
        limit = s.max_upload_mb * 1024 * 1024
        data = bytearray()
        while chunk := await file.read(1024 * 1024):
            data.extend(chunk)
            if len(data) > limit:
                raise ValidationFailed(f"File is larger than the {s.max_upload_mb} MB limit")
        if not data:
            raise ValidationFailed("The uploaded file is empty")
        mime = sniff_mime(bytes(data[:16]), bytes(data))
        if mime is None or mime != MIME_BY_EXT[ext]:
            raise ValidationFailed("The file content does not match its extension or is not a supported type")
        import hashlib
        stored = f"{uuid.uuid4().hex}.{ext}"
        (self.user_dir() / stored).write_bytes(bytes(data))
        doc = Document(original_name=name, stored_name=stored, mime_type=mime, size_bytes=len(data),
                       category=category, policy_id=policy_id, patient_id=patient_id, index_status="uploaded",
                       content_hash=hashlib.sha256(bytes(data)).hexdigest())
        self.repo.add(doc)
        log_activity(self.db, self.user_id, "document.uploaded", "document", doc.id, f"Document uploaded: {name}")
        return doc

    def _purge_index(self, doc: Document) -> None:
        vectorstore.delete_document(self.user_id, doc.id)
        chunks = ChunkRepository(self.db, self.user_id)
        for c in chunks.for_document(doc.id):
            self.db.delete(c)
        self.db.commit()

    def delete(self, doc_id: uuid.UUID) -> None:
        doc = self.get(doc_id)
        self._purge_index(doc)
        for link in self.db.scalars(select(ClaimDocument).where(ClaimDocument.document_id == doc.id,
                                                                  ClaimDocument.user_id == self.user_id)):
            self.db.delete(link)
        for rec in self.db.scalars(select(MedicalRecord).where(MedicalRecord.document_id == doc.id,
                                                                 MedicalRecord.user_id == self.user_id)):
            rec.document_id = None
        self.db.commit()
        self.path_for(doc).unlink(missing_ok=True)
        self.repo.delete(doc)
        log_activity(self.db, self.user_id, "document.deleted", "document", doc.id, f"Document deleted: {doc.original_name}")

    def delete_for_policy(self, policy_id: uuid.UUID) -> None:
        for d in self.repo.list_filtered(policy_id=policy_id):
            self.delete(d.id)
