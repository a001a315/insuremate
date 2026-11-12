import uuid

from sqlalchemy.orm import Session

from app.models import Empanelment, User
from app.repositories.entities import EmpanelmentRepository
from app.schemas.hospital import EmpanelmentIn, EmpanelmentUpdate, HospitalProfile
from app.services.errors import NotFound


class HospitalService:
    def __init__(self, db: Session, user: User):
        self.db, self.user = db, user
        self.repo = EmpanelmentRepository(db, user.id)

    def update_profile(self, data: HospitalProfile) -> User:
        self.user.hospital_name, self.user.hospital_city = data.hospital_name.strip(), data.hospital_city
        self.db.commit()
        return self.user

    def get(self, eid: uuid.UUID) -> Empanelment:
        e = self.repo.get(eid)
        if not e:
            raise NotFound("Empanelment not found")
        return e

    def add(self, data: EmpanelmentIn) -> Empanelment:
        return self.repo.add(Empanelment(**data.model_dump()))

    def update(self, eid: uuid.UUID, data: EmpanelmentUpdate) -> Empanelment:
        e = self.get(eid)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(e, k, v)
        return self.repo.save(e)

    def delete(self, eid: uuid.UUID) -> None:
        self.repo.delete(self.get(eid))
