import uuid
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

M = TypeVar("M")


class OwnedRepository(Generic[M]):
    """Every query is scoped to the owning user. Soft-deleted rows are hidden."""

    model: type[M]

    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    def query(self):
        q = select(self.model).where(self.model.user_id == self.user_id)  # type: ignore[attr-defined]
        if hasattr(self.model, "deleted_at"):
            q = q.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return q

    def get(self, id: uuid.UUID) -> M | None:
        return self.db.scalar(self.query().where(self.model.id == id))  # type: ignore[attr-defined]

    def list(self) -> list[M]:
        return list(self.db.scalars(self.query()))

    def add(self, obj: M) -> M:
        obj.user_id = self.user_id  # type: ignore[attr-defined]
        self.db.add(obj)
        self.db.commit()
        return obj

    def save(self, obj: M) -> M:
        self.db.commit()
        return obj

    def delete(self, obj: M) -> None:
        from app.database.base import utcnow
        if hasattr(obj, "deleted_at"):
            obj.deleted_at = utcnow()  # type: ignore[attr-defined]
        else:
            self.db.delete(obj)
        self.db.commit()
