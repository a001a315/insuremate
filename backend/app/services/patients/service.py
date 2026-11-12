import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Patient
from app.models.claim import PENDING_STATUSES, clearance_of
from app.repositories.entities import ClaimRepository, PatientRepository, PolicyRepository
from app.schemas.patient import PatientCreate, PatientListOut, PatientUpdate
from app.services.activity import log_activity
from app.services.errors import NotFound


def insurance_state(policies, today: date) -> str:
    live = [p for p in policies if p.status == "active"]
    if not live:
        return "expired" if any(p.status == "expired" or (p.expiry_date and p.expiry_date < today) for p in policies) else "no_policy"
    ok = [p for p in live if not p.expiry_date or p.expiry_date >= today]
    if not ok:
        return "expired"
    if any(p.expiry_date and p.expiry_date <= today + timedelta(days=30) for p in ok) and all(
            p.expiry_date and p.expiry_date <= today + timedelta(days=30) for p in ok):
        return "expiring_soon"
    return "active"


class PatientService:
    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db, self.user_id = db, user_id
        self.repo = PatientRepository(db, user_id)

    def get(self, patient_id: uuid.UUID) -> Patient:
        p = self.repo.get(patient_id)
        if not p:
            raise NotFound("Patient not found")
        return p

    def create(self, data: PatientCreate) -> Patient:
        p = self.repo.add(Patient(**data.model_dump()))
        log_activity(self.db, self.user_id, "patient.created", "patient", p.id, f"Patient registered: {p.full_name}")
        return p

    def update(self, patient_id: uuid.UUID, data: PatientUpdate) -> Patient:
        p = self.get(patient_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(p, k, v)
        return self.repo.save(p)

    def delete(self, patient_id: uuid.UUID) -> None:
        from app.services.claims.service import ClaimService
        from app.services.policy.service import PolicyService
        p = self.get(patient_id)
        for pol in PolicyRepository(self.db, self.user_id).list_filtered(include_archived=True, patient_id=p.id):
            PolicyService(self.db, self.user_id).delete(pol.id)
        for c in ClaimRepository(self.db, self.user_id).list_filtered(patient_id=p.id):
            ClaimService(self.db, self.user_id).delete(c.id)
        self.repo.delete(p)
        log_activity(self.db, self.user_id, "patient.deleted", "patient", p.id, f"Patient deleted: {p.full_name}")

    def list_with_summary(self, q: str | None = None) -> list[PatientListOut]:
        today = date.today()
        policies = PolicyRepository(self.db, self.user_id).list_filtered(include_archived=False)
        claims = ClaimRepository(self.db, self.user_id).list_filtered()
        out = []
        for p in self.repo.search(q):
            pols = [x for x in policies if x.patient_id == p.id]
            cl = [c for c in claims if c.patient_id == p.id]  # newest first
            latest = cl[0] if cl else None
            out.append(PatientListOut.model_validate({
                **{k: getattr(p, k) for k in ("id", "full_name", "mrn", "date_of_birth", "gender", "phone", "notes", "created_at")},
                "active_policies": sum(1 for x in pols if x.status == "active"),
                "open_claims": sum(1 for c in cl if c.status in PENDING_STATUSES),
                "latest_claim_status": latest.status if latest else None,
                "latest_clearance": clearance_of(latest.status) if latest else None,
                "insurance_state": insurance_state(pols, today),
            }))
        return out
