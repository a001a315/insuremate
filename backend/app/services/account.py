import shutil
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (ActivityLog, Claim, ClaimDocument, Conversation, Document, DocumentChunk, Empanelment,
                        InsuredMember, MedicalRecord, Message, Notification, Patient, Policy, Reminder, User)
from app.services.rag import vectorstore


def delete_account(db: Session, user: User) -> None:
    """Permanently removes all of the user's rows, uploaded files and vectors."""
    for doc_id in db.scalars(select(Document.id).where(Document.user_id == user.id)):
        vectorstore.delete_document(user.id, doc_id)
    shutil.rmtree(Path(get_settings().upload_dir) / str(user.id), ignore_errors=True)
    for model in (Message, Conversation, Notification, Reminder, ClaimDocument, MedicalRecord, Claim,
                  DocumentChunk, Document, InsuredMember, Policy, Patient, Empanelment, ActivityLog):
        db.execute(delete(model).where(model.user_id == user.id))
    db.execute(delete(User).where(User.id == user.id))
    db.commit()
