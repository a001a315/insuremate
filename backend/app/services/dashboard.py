import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.claim import CLEARED_STATUSES, PENDING_STATUSES, REJECTED_STATUSES, clearance_of
from app.repositories.entities import (ActivityRepository, ClaimRepository, DocumentRepository, EmpanelmentRepository,
                                       PatientRepository, PolicyRepository)
from app.services.eligibility.service import network_status
from app.services.rag.format import inr

EXPIRY_DAYS = 30


def _amount(c) -> float:
    return float(c.approved_amount if c.approved_amount is not None else c.claim_amount or 0)


def build_dashboard(db: Session, user_id: uuid.UUID) -> dict:
    today = date.today()
    patients = PatientRepository(db, user_id).search()
    names = {p.id: p.full_name for p in patients}
    policies = [p for p in PolicyRepository(db, user_id).list() if p.status != "archived"]
    active = [p for p in policies if p.status == "active" and (not p.expiry_date or p.expiry_date >= today)]
    claims = ClaimRepository(db, user_id).list_filtered()
    emps = EmpanelmentRepository(db, user_id).list_sorted()
    expiring = sorted([p for p in active if p.expiry_date and p.expiry_date <= today + timedelta(days=EXPIRY_DAYS)],
                      key=lambda p: p.expiry_date)
    docs = DocumentRepository(db, user_id).list_filtered()[:5]
    activity = ActivityRepository(db, user_id).recent(15)

    pending = [c for c in claims if c.status in PENDING_STATUSES]
    rejected = [c for c in claims if c.status in REJECTED_STATUSES]
    cleared = [c for c in claims if c.status in CLEARED_STATUSES]
    by_status: dict[str, int] = {}
    for c in claims:
        by_status[c.status] = by_status.get(c.status, 0) + 1

    insights = []  # each one is derived from stored data; nothing is invented
    for p in expiring:
        insights.append({"kind": "expiry", "text": f"{names.get(p.patient_id, 'A patient')}'s policy {p.name} expires in {(p.expiry_date - today).days} days.",
                         "policy_id": str(p.id), "patient_id": str(p.patient_id) if p.patient_id else None})
    for c in rejected:
        insights.append({"kind": "claim", "text": f"Claim {c.claim_ref} for {c.patient_name} is marked {c.status.replace('_', ' ')}"
                         + (f": {c.rejection_reason}" if c.rejection_reason else "."), "claim_id": str(c.id)})
    for c in claims:
        if c.status == "additional_documents_required":
            insights.append({"kind": "claim", "text": f"Claim {c.claim_ref} for {c.patient_name} is waiting for additional documents.", "claim_id": str(c.id)})
    outside = sorted({p.insurer for p in active if network_status(p, emps) == "not_empanelled"})
    for insurer in outside:
        n = sum(1 for p in active if p.insurer == insurer)
        insights.append({"kind": "network", "text": f"{n} active polic{'y' if n == 1 else 'ies'} from {insurer} {'is' if n == 1 else 'are'} not in your empanelment list, so cashless is unlikely."})
    no_policy = [p for p in patients if not any(x.patient_id == p.id for x in active)]
    if no_policy:
        insights.append({"kind": "coverage", "text": f"{len(no_policy)} patient(s) have no active policy recorded: {', '.join(p.full_name for p in no_policy[:5])}."})

    def pol_row(p):
        return {"id": str(p.id), "name": p.name, "insurer": p.insurer, "patient_id": str(p.patient_id) if p.patient_id else None,
                "patient_name": names.get(p.patient_id), "expiry_date": p.expiry_date.isoformat() if p.expiry_date else None,
                "days_left": (p.expiry_date - today).days if p.expiry_date else None, "network_status": network_status(p, emps)}

    return {
        "summary": {
            "patients": len(patients),
            "active_policies": len(active),
            "expiring_policies": len(expiring),
            "pending_claims": len(pending),
            "rejected_claims": len(rejected),
            "cleared_claims": len(cleared),
            "amount_pending": float(sum(float(c.claim_amount or 0) for c in pending)),
            "amount_approved": float(sum(_amount(c) for c in cleared)),
            "amount_pending_display": inr(sum(float(c.claim_amount or 0) for c in pending)),
            "amount_approved_display": inr(sum(_amount(c) for c in cleared)),
            "empanelled_insurers": len(emps),
        },
        "claims_by_status": [{"status": k, "count": v} for k, v in sorted(by_status.items(), key=lambda kv: -kv[1])],
        "expiring": [pol_row(p) for p in expiring],
        "recent_claims": [{"id": str(c.id), "claim_ref": c.claim_ref, "patient_id": str(c.patient_id) if c.patient_id else None,
                           "patient_name": c.patient_name, "insurer": c.insurer, "claim_amount": float(c.claim_amount or 0),
                           "status": c.status, "clearance": clearance_of(c.status)} for c in claims[:6]],
        "recent_documents": [{"id": str(d.id), "name": d.original_name, "category": d.category,
                              "index_status": d.index_status, "created_at": d.created_at.isoformat()} for d in docs],
        "activity": [{"id": str(a.id), "action": a.action, "summary": a.summary, "created_at": a.created_at.isoformat()} for a in activity],
        "insights": insights,
    }
