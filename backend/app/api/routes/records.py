import uuid
from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import User
from app.schemas.medical_record import RecordCreate, RecordOut, RecordUpdate
from app.services.medical_records.service import MedicalRecordService

router = APIRouter(prefix="/records", tags=["medical records"])


def _svc(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> MedicalRecordService:
    return MedicalRecordService(db, user.id)


@router.get("", response_model=list[RecordOut])
def list_records(q: str | None = None, category: str | None = None, date_from: date | None = None,
                 date_to: date | None = None, claim_id: uuid.UUID | None = None, policy_id: uuid.UUID | None = None,
                 patient_id: uuid.UUID | None = None, svc: MedicalRecordService = Depends(_svc)):
    """Newest first, which doubles as the chronological medical history."""
    return svc.repo.search(q, category, date_from, date_to, claim_id, policy_id, patient_id)


@router.post("", response_model=RecordOut, status_code=201)
def create_record(body: RecordCreate, svc: MedicalRecordService = Depends(_svc)):
    return svc.create(body)


@router.get("/{record_id}", response_model=RecordOut)
def get_record(record_id: uuid.UUID, svc: MedicalRecordService = Depends(_svc)):
    return svc.get(record_id)


@router.patch("/{record_id}", response_model=RecordOut)
def update_record(record_id: uuid.UUID, body: RecordUpdate, svc: MedicalRecordService = Depends(_svc)):
    return svc.update(record_id, body)


@router.delete("/{record_id}", status_code=204)
def delete_record(record_id: uuid.UUID, svc: MedicalRecordService = Depends(_svc)):
    svc.delete(record_id)
    return Response(status_code=204)
