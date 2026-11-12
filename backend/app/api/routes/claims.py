import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import User
from app.repositories.entities import ActivityRepository
from app.schemas.claim import AttachIn, ClaimCreate, ClaimOut, ClaimUpdate, NoteIn, StatusChange
from app.schemas.document import DocumentOut
from app.services.claims.service import ClaimService

router = APIRouter(prefix="/claims", tags=["claims"])


def _svc(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ClaimService:
    return ClaimService(db, user.id)


@router.get("", response_model=list[ClaimOut])
def list_claims(status: str | None = None, policy_id: uuid.UUID | None = None,
                patient_id: uuid.UUID | None = None, svc: ClaimService = Depends(_svc)):
    return svc.list(status, policy_id, patient_id)


@router.post("", response_model=ClaimOut, status_code=201)
def create_claim(body: ClaimCreate, svc: ClaimService = Depends(_svc)):
    return svc.create(body)


@router.get("/{claim_id}", response_model=ClaimOut)
def get_claim(claim_id: uuid.UUID, svc: ClaimService = Depends(_svc)):
    return svc.get(claim_id)


@router.patch("/{claim_id}", response_model=ClaimOut)
def update_claim(claim_id: uuid.UUID, body: ClaimUpdate, svc: ClaimService = Depends(_svc)):
    return svc.update(claim_id, body)


@router.post("/{claim_id}/status", response_model=ClaimOut)
def change_status(claim_id: uuid.UUID, body: StatusChange, svc: ClaimService = Depends(_svc)):
    """Manual status update by the user. The app never contacts insurers."""
    return svc.change_status(claim_id, body)


@router.post("/{claim_id}/notes", status_code=204)
def add_note(claim_id: uuid.UUID, body: NoteIn, svc: ClaimService = Depends(_svc)):
    svc.add_note(claim_id, body.note)
    return Response(status_code=204)


@router.get("/{claim_id}/activity")
def claim_activity(claim_id: uuid.UUID, svc: ClaimService = Depends(_svc)):
    svc.get(claim_id)
    return [{"id": str(a.id), "action": a.action, "summary": a.summary, "meta": a.meta, "created_at": a.created_at.isoformat()}
            for a in ActivityRepository(svc.db, svc.user_id).recent(100, entity_id=claim_id)]


@router.get("/{claim_id}/documents", response_model=list[DocumentOut])
def claim_documents(claim_id: uuid.UUID, svc: ClaimService = Depends(_svc)):
    return svc.documents(claim_id)


@router.post("/{claim_id}/documents", status_code=status.HTTP_201_CREATED)
def attach_document(claim_id: uuid.UUID, body: AttachIn, svc: ClaimService = Depends(_svc)):
    svc.attach(claim_id, body.document_id)
    return {"ok": True}


@router.delete("/{claim_id}/documents/{document_id}", status_code=204)
def detach_document(claim_id: uuid.UUID, document_id: uuid.UUID, svc: ClaimService = Depends(_svc)):
    svc.detach(claim_id, document_id)
    return Response(status_code=204)


@router.delete("/{claim_id}", status_code=204)
def delete_claim(claim_id: uuid.UUID, svc: ClaimService = Depends(_svc)):
    svc.delete(claim_id)
    return Response(status_code=204)
