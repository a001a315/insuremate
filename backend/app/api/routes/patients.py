import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import User
from app.schemas.eligibility import EligibilityOut, EligibilityRequest
from app.schemas.patient import PatientCreate, PatientListOut, PatientOut, PatientUpdate
from app.services.eligibility.service import EligibilityService
from app.services.patients.service import PatientService

router = APIRouter(prefix="/patients", tags=["patients"])


def _svc(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> PatientService:
    return PatientService(db, user.id)


@router.get("", response_model=list[PatientListOut])
def list_patients(q: str | None = None, svc: PatientService = Depends(_svc)):
    return svc.list_with_summary(q)


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(body: PatientCreate, svc: PatientService = Depends(_svc)):
    return svc.create(body)


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: uuid.UUID, svc: PatientService = Depends(_svc)):
    return svc.get(patient_id)


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: uuid.UUID, body: PatientUpdate, svc: PatientService = Depends(_svc)):
    return svc.update(patient_id, body)


@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: uuid.UUID, svc: PatientService = Depends(_svc)):
    svc.delete(patient_id)
    return Response(status_code=204)


@router.post("/{patient_id}/eligibility", response_model=list[EligibilityOut])
def check_eligibility(patient_id: uuid.UUID, body: EligibilityRequest, svc: PatientService = Depends(_svc)):
    """Advisory pre-check of each of the patient's policies against this hospital's empanelment list."""
    return EligibilityService(svc.db, svc.user_id).check_patient(patient_id, body)
