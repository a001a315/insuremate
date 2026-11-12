import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import User
from app.schemas.auth import UserOut
from app.schemas.hospital import EmpanelmentIn, EmpanelmentOut, EmpanelmentUpdate, HospitalProfile
from app.services.hospital.service import HospitalService

router = APIRouter(prefix="/hospital", tags=["hospital"])


def _svc(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> HospitalService:
    return HospitalService(db, user)


@router.patch("/profile", response_model=UserOut)
def update_profile(body: HospitalProfile, svc: HospitalService = Depends(_svc)):
    return svc.update_profile(body)


@router.get("/empanelments", response_model=list[EmpanelmentOut])
def list_empanelments(svc: HospitalService = Depends(_svc)):
    return svc.repo.list_sorted()


@router.post("/empanelments", response_model=EmpanelmentOut, status_code=201)
def add_empanelment(body: EmpanelmentIn, svc: HospitalService = Depends(_svc)):
    return svc.add(body)


@router.patch("/empanelments/{eid}", response_model=EmpanelmentOut)
def update_empanelment(eid: uuid.UUID, body: EmpanelmentUpdate, svc: HospitalService = Depends(_svc)):
    return svc.update(eid, body)


@router.delete("/empanelments/{eid}", status_code=204)
def delete_empanelment(eid: uuid.UUID, svc: HospitalService = Depends(_svc)):
    svc.delete(eid)
    return Response(status_code=204)
