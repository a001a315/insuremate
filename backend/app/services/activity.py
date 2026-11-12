import uuid

from sqlalchemy.orm import Session

from app.models.activity import ActivityLog


def log_activity(db: Session, user_id: uuid.UUID, action: str, entity_type: str,
                 entity_id: uuid.UUID | None, summary: str, meta: dict | None = None) -> None:
    """Metadata-only audit trail. Never pass medical content or document text."""
    db.add(ActivityLog(user_id=user_id, action=action, entity_type=entity_type,
                       entity_id=entity_id, summary=summary[:300], meta=meta))
    db.commit()
