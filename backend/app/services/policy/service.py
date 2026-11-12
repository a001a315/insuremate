import uuid

from sqlalchemy.orm import Session

from app.models import InsuredMember, Policy
from app.repositories.entities import ClaimRepository, PatientRepository, PolicyRepository
from app.schemas.policy import PolicyCreate, PolicyUpdate
from app.services.activity import log_activity
from app.services.errors import NotFound


class PolicyService:
    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db, self.user_id = db, user_id
        self.repo = PolicyRepository(db, user_id)

    def get(self, policy_id: uuid.UUID) -> Policy:
        p = self.repo.get(policy_id)
        if not p:
            raise NotFound("Policy not found")
        return p

    def list(self, include_archived: bool = False, patient_id: uuid.UUID | None = None) -> list[Policy]:
        return self.repo.list_filtered(include_archived, patient_id)

    def _require_patient(self, patient_id: uuid.UUID) -> None:
        if not PatientRepository(self.db, self.user_id).get(patient_id):
            raise NotFound("Patient not found")

    def create(self, data: PolicyCreate) -> Policy:
        self._require_patient(data.patient_id)
        payload = data.model_dump(exclude={"members", "details"})
        payload["renewal_date"] = data.renewal_date or data.expiry_date
        p = Policy(**payload, details={k: v.model_dump() for k, v in data.details.items()})
        p.members = [InsuredMember(user_id=self.user_id, **m.model_dump()) for m in data.members]
        self.repo.add(p)
        log_activity(self.db, self.user_id, "policy.created", "policy", p.id, f"Policy added: {p.name}")
        return p

    def update(self, policy_id: uuid.UUID, data: PolicyUpdate) -> Policy:
        p = self.get(policy_id)
        changes = data.model_dump(exclude_unset=True)
        if changes.get("patient_id"):
            self._require_patient(changes["patient_id"])
        members = changes.pop("members", None)
        details = changes.pop("details", None)
        for k, v in changes.items():
            setattr(p, k, v)
        if details is not None:
            merged = dict(p.details or {})
            merged.update({k: dict(v) for k, v in details.items()})
            p.details = merged  # reassign so the JSON change is tracked
        if members is not None:
            p.members.clear()
            p.members.extend(InsuredMember(user_id=self.user_id, **m) for m in members)
        self.repo.save(p)
        log_activity(self.db, self.user_id, "policy.updated", "policy", p.id, f"Policy updated: {p.name}")
        return p

    def archive(self, policy_id: uuid.UUID) -> Policy:
        p = self.get(policy_id)
        p.status = "archived"
        self.repo.save(p)
        log_activity(self.db, self.user_id, "policy.archived", "policy", p.id, f"Policy archived: {p.name}")
        return p

    def delete(self, policy_id: uuid.UUID) -> None:
        from app.services.documents.service import DocumentService
        p = self.get(policy_id)
        # Remove indexed material for documents attached to this policy before the policy disappears.
        DocumentService(self.db, self.user_id).delete_for_policy(p.id)
        claims = ClaimRepository(self.db, self.user_id)
        for c in claims.list_filtered(policy_id=p.id):
            claims.delete(c)
        self.repo.delete(p)
        log_activity(self.db, self.user_id, "policy.deleted", "policy", p.id, f"Policy deleted: {p.name}")
