import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import SessionLocal, get_db
from app.models import Conversation, User
from app.repositories.entities import ConversationRepository, MessageRepository, PatientRepository, PolicyRepository
from app.services.llm import LLMUnavailable, get_llm_provider
from app.services.rag.chat import ChatService

router = APIRouter(prefix="/chat", tags=["assistant"])


class ConversationCreate(BaseModel):
    policy_id: uuid.UUID | None = None
    patient_id: uuid.UUID | None = None


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    policy_id: uuid.UUID | None = None  # None = all policies
    patient_id: uuid.UUID | None = None  # narrows to one patient's policies


def _conv(db: Session, user: User, cid: uuid.UUID) -> Conversation:
    c = ConversationRepository(db, user.id).get(cid)
    if not c:
        raise HTTPException(404, "Conversation not found")
    return c


def _msg_out(m):
    return {"id": str(m.id), "role": m.role, "content": m.content, "citations": m.citations or [],
            "created_at": m.created_at.isoformat()}


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [{"id": str(c.id), "title": c.title, "policy_id": str(c.policy_id) if c.policy_id else None,
             "updated_at": c.updated_at.isoformat()} for c in ConversationRepository(db, user.id).list_recent()]


@router.post("/conversations", status_code=201)
def create_conversation(body: ConversationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if body.policy_id and not PolicyRepository(db, user.id).get(body.policy_id):
        raise HTTPException(404, "Policy not found")
    if body.patient_id and not PatientRepository(db, user.id).get(body.patient_id):
        raise HTTPException(404, "Patient not found")
    c = ConversationRepository(db, user.id).add(Conversation(policy_id=body.policy_id, patient_id=body.patient_id))
    return {"id": str(c.id), "title": c.title, "policy_id": str(c.policy_id) if c.policy_id else None}


@router.get("/conversations/{cid}/messages")
def get_messages(cid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _conv(db, user, cid)
    return [_msg_out(m) for m in MessageRepository(db, user.id).for_conversation(cid)]


@router.delete("/conversations/{cid}", status_code=204)
def delete_conversation(cid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ConversationRepository(db, user.id).delete(_conv(db, user, cid))
    return Response(status_code=204)


@router.post("/conversations/{cid}/clear", status_code=204)
def clear_conversation(cid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _conv(db, user, cid)
    msgs = MessageRepository(db, user.id)
    for m in msgs.for_conversation(cid):
        db.delete(m)
    db.commit()
    return Response(status_code=204)


@router.post("/conversations/{cid}/messages")
def ask(cid: uuid.UUID, body: AskIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = _conv(db, user, cid)
    svc = ChatService(db, user.id, get_llm_provider())
    plan = svc.prepare(body.question, conv, body.policy_id, body.patient_id)
    try:
        answer = svc.complete(plan)
    except LLMUnavailable as e:
        raise HTTPException(503, str(e))
    return _msg_out(svc.save_turn(conv, body.question, answer, plan.citations))


@router.post("/conversations/{cid}/messages/stream")
def ask_stream(cid: uuid.UUID, body: AskIn, user: User = Depends(get_current_user)):
    """Server-sent events: `token` events while generating, then one `done` event with the saved message."""
    def events():
        with SessionLocal() as db:
            conv = ConversationRepository(db, user.id).get(cid)
            if not conv:
                yield f"event: error\ndata: {json.dumps({'detail': 'Conversation not found'})}\n\n"
                return
            svc = ChatService(db, user.id, get_llm_provider())
            plan = svc.prepare(body.question, conv, body.policy_id, body.patient_id)
            parts: list[str] = []
            try:
                for tok in svc.stream(plan):
                    parts.append(tok)
                    yield f"event: token\ndata: {json.dumps(tok)}\n\n"
            except LLMUnavailable as e:
                yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
                return
            saved = svc.save_turn(conv, body.question, "".join(parts), plan.citations)
            yield f"event: done\ndata: {json.dumps(_msg_out(saved))}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
