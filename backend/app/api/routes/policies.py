import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import User
from app.repositories.entities import ClaimRepository, DocumentRepository, EmpanelmentRepository, PatientRepository
from app.schemas.claim import ClaimOut
from app.schemas.common import mask_policy_number
from app.schemas.document import DocumentOut
from app.schemas.policy import PolicyCreate, PolicyListOut, PolicyOut, PolicyUpdate
from app.services.eligibility.service import network_status
from app.services.errors import ValidationFailed
from app.services.llm import get_llm_provider
from app.services.policy.service import PolicyService
from app.services.rag.prompt import DISCLAIMER, NO_INFO, SYSTEM_PROMPT, build_user_prompt
from app.services.rag.retrieval import retrieve

router = APIRouter(prefix="/policies", tags=["policies"])


def _svc(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> PolicyService:
    return PolicyService(db, user.id)


@router.get("", response_model=list[PolicyListOut])
def list_policies(include_archived: bool = False, patient_id: uuid.UUID | None = None, svc: PolicyService = Depends(_svc)):
    emps = EmpanelmentRepository(svc.db, svc.user_id).list_sorted()
    names = {p.id: p.full_name for p in PatientRepository(svc.db, svc.user_id).search()}
    return [PolicyListOut(masked_policy_number=mask_policy_number(p.policy_number), patient_name=names.get(p.patient_id),
                          network_status=network_status(p, emps), **{
        k: getattr(p, k) for k in ("id", "patient_id", "name", "insurer", "tpa_name", "policy_type", "sum_insured", "premium_amount",
                                   "premium_frequency", "expiry_date", "renewal_date", "status")})
        for p in svc.list(include_archived, patient_id)]


def _out(svc: PolicyService, p) -> PolicyOut:
    out = PolicyOut.model_validate(p)
    out.network_status = network_status(p, EmpanelmentRepository(svc.db, svc.user_id).list_sorted())
    return out


@router.post("", response_model=PolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(body: PolicyCreate, svc: PolicyService = Depends(_svc)):
    return _out(svc, svc.create(body))


@router.get("/{policy_id}", response_model=PolicyOut)
def get_policy(policy_id: uuid.UUID, svc: PolicyService = Depends(_svc)):
    return _out(svc, svc.get(policy_id))


@router.patch("/{policy_id}", response_model=PolicyOut)
def update_policy(policy_id: uuid.UUID, body: PolicyUpdate, svc: PolicyService = Depends(_svc)):
    return _out(svc, svc.update(policy_id, body))


@router.post("/{policy_id}/archive", response_model=PolicyOut)
def archive_policy(policy_id: uuid.UUID, svc: PolicyService = Depends(_svc)):
    return _out(svc, svc.archive(policy_id))


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(policy_id: uuid.UUID, svc: PolicyService = Depends(_svc)):
    svc.delete(policy_id)
    return Response(status_code=204)


@router.get("/{policy_id}/documents", response_model=list[DocumentOut])
def policy_documents(policy_id: uuid.UUID, svc: PolicyService = Depends(_svc)):
    svc.get(policy_id)
    return DocumentRepository(svc.db, svc.user_id).list_filtered(policy_id=policy_id)


@router.get("/{policy_id}/claims", response_model=list[ClaimOut])
def policy_claims(policy_id: uuid.UUID, svc: PolicyService = Depends(_svc)):
    svc.get(policy_id)
    return ClaimRepository(svc.db, svc.user_id).list_filtered(policy_id=policy_id)


@router.post("/{policy_id}/summary", response_model=PolicyOut)
def generate_summary(policy_id: uuid.UUID, svc: PolicyService = Depends(_svc)):
    """AI-generated summary grounded in this policy's indexed documents. Stored and labelled as AI-generated."""
    p = svc.get(policy_id)
    chunks = retrieve(svc.db, svc.user_id, "coverage benefits exclusions waiting period room rent co-payment sum insured",
                      [p.id], k=8, min_score=0.0)
    if not chunks:
        raise ValidationFailed("No indexed document text is available for this policy. Upload and index a policy document first.")
    q = "Summarise this policy: coverage, key benefits, exclusions, waiting periods, room rent and co-payment. Only state what the excerpts say."
    text = get_llm_provider().generate([{"role": "system", "content": SYSTEM_PROMPT},
                                        {"role": "user", "content": build_user_prompt(q, [p], chunks)}]).strip()
    if text.startswith(NO_INFO[:30]):
        raise ValidationFailed(NO_INFO)
    p.ai_summary = text + DISCLAIMER
    svc.repo.save(p)
    return _out(svc, p)
