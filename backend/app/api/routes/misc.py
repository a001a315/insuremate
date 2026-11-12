import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import verify_password
from app.database.session import get_db
from app.models import Document, User
from app.schemas.reminder import NotificationOut, ReminderCreate, ReminderOut, ReminderUpdate
from app.repositories.entities import NotificationRepository
from app.services.account import delete_account
from app.services.dashboard import build_dashboard
from app.services.demo import load_demo_data
from app.services.embeddings import get_embedding_provider
from app.services.llm import get_llm_provider
from app.services.rag import vectorstore
from app.services.reminders.service import ReminderService

router = APIRouter(tags=["misc"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return build_dashboard(db, user.id)


# ---- reminders & notifications
def _rem(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ReminderService:
    return ReminderService(db, user.id)


@router.get("/reminders", response_model=list[ReminderOut])
def list_reminders(svc: ReminderService = Depends(_rem)):
    return svc.list()


@router.post("/reminders", response_model=ReminderOut, status_code=201)
def create_reminder(body: ReminderCreate, svc: ReminderService = Depends(_rem)):
    return svc.create(body)


@router.patch("/reminders/{rid}", response_model=ReminderOut)
def update_reminder(rid: uuid.UUID, body: ReminderUpdate, svc: ReminderService = Depends(_rem)):
    return svc.update(rid, body)


@router.delete("/reminders/{rid}", status_code=204)
def delete_reminder(rid: uuid.UUID, svc: ReminderService = Depends(_rem)):
    svc.delete(rid)
    return Response(status_code=204)


@router.post("/reminders/run-checks")
def run_checks(svc: ReminderService = Depends(_rem)):
    return svc.run_checks()


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = NotificationRepository(db, user.id).recent()
    return {"unread": sum(not n.is_read for n in items), "items": [NotificationOut.model_validate(n) for n in items]}


@router.post("/notifications/{nid}/read", status_code=204)
def mark_read(nid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.database.base import utcnow
    repo = NotificationRepository(db, user.id)
    n = repo.get(nid)
    if not n:
        raise HTTPException(404, "Notification not found")
    n.is_read, n.read_at = True, utcnow()
    repo.save(n)
    return Response(status_code=204)


@router.post("/notifications/read-all", status_code=204)
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.database.base import utcnow
    repo = NotificationRepository(db, user.id)
    for n in repo.list():
        n.is_read, n.read_at = True, utcnow()
    db.commit()
    return Response(status_code=204)


# ---- AI status
@router.get("/ai/status")
def ai_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = get_settings()
    rows = db.execute(select(Document.index_status, func.count()).where(
        Document.user_id == user.id, Document.deleted_at.is_(None)).group_by(Document.index_status)).all()
    return {"llm": get_llm_provider().health(), "embedding_model": get_embedding_provider().name,
            "vector_store": vectorstore.stats(), "chunk_size": s.chunk_size, "chunk_overlap": s.chunk_overlap,
            "documents_by_status": {k: v for k, v in rows}}


# ---- account
class DeleteAccount(BaseModel):
    password: str


@router.post("/account/demo-data")
def demo_data(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return load_demo_data(db, user)


@router.post("/account/delete", status_code=204)
def delete_my_account(body: DeleteAccount, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(403, "Incorrect password")
    delete_account(db, user)
    return Response(status_code=204)
