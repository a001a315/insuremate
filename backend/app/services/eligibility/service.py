"""Deterministic eligibility pre-check for a patient at THIS hospital.

It only compares what the hospital has recorded (policy dates, waiting days, sum insured, claims already
booked, recorded exclusion text) with the hospital's own empanelment list. It never contacts an insurer or
TPA, and every result states that the insurer/TPA makes the final decision.
"""
import re
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models import Empanelment, Policy
from app.models.claim import CLEARED_STATUSES, PENDING_STATUSES
from app.repositories.entities import ClaimRepository, EmpanelmentRepository, PatientRepository, PolicyRepository
from app.schemas.eligibility import CheckOut, EligibilityOut, EligibilityRequest
from app.services.errors import NotFound
from app.services.rag.format import inr

DISCLAIMER = ("Advisory pre-check based only on the information recorded in this system. It is not an approval. "
              "The insurer/TPA makes the final decision; confirm with them before admission.")
VERDICT_LABELS = {
    "eligible_cashless": "Likely eligible for cashless treatment",
    "eligible_reimbursement": "Likely eligible, reimbursement route (no cashless at this hospital)",
    "needs_review": "Needs manual review",
    "not_eligible": "Not eligible based on recorded data",
}


def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


def _same(a: str | None, b: str | None) -> bool:
    a, b = _norm(a), _norm(b)
    return bool(a and b and (a == b or a in b or b in a))


def match_empanelment(policy: Policy, emps: list[Empanelment]) -> Empanelment | None:
    cands = [e for e in emps if _same(e.insurer, policy.insurer) or (policy.tpa_name and _same(e.tpa_name, policy.tpa_name))
             or (policy.tpa_name and _same(e.insurer, policy.tpa_name))]
    # Prefer an entry that is still valid and cashless-enabled.
    cands.sort(key=lambda e: (not e.cashless_enabled, e.valid_until is not None and e.valid_until < date.today()))
    return cands[0] if cands else None


def network_status(policy: Policy, emps: list[Empanelment], on: date | None = None) -> str:
    on = on or date.today()
    e = match_empanelment(policy, emps)
    if not e:
        return "not_empanelled"
    if e.valid_until and e.valid_until < on:
        return "expired"
    return "empanelled_cashless" if e.cashless_enabled else "empanelled_no_cashless"


def utilised_amount(claims, policy_id: uuid.UUID) -> float:
    total = 0.0
    for c in claims:
        if c.policy_id != policy_id:
            continue
        if c.status in CLEARED_STATUSES:
            total += float(c.approved_amount if c.approved_amount is not None else c.claim_amount or 0)
        elif c.status in PENDING_STATUSES or c.status == "pre_auth_approved":
            total += float(c.claim_amount or 0)
    return total


class EligibilityService:
    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db, self.user_id = db, user_id

    def check_patient(self, patient_id: uuid.UUID, req: EligibilityRequest) -> list[EligibilityOut]:
        if not PatientRepository(self.db, self.user_id).get(patient_id):
            raise NotFound("Patient not found")
        policies = [p for p in PolicyRepository(self.db, self.user_id).list_filtered(include_archived=False, patient_id=patient_id)]
        if req.policy_id:
            policies = [p for p in policies if p.id == req.policy_id]
            if not policies:
                raise NotFound("Policy not found for this patient")
        emps = EmpanelmentRepository(self.db, self.user_id).list_sorted()
        claims = ClaimRepository(self.db, self.user_id).list_filtered()
        return [self.check_policy(p, emps, claims, req) for p in policies]

    def check_policy(self, p: Policy, emps, claims, req: EligibilityRequest) -> EligibilityOut:
        on = req.admission_date or date.today()
        checks: list[CheckOut] = []
        add = lambda key, label, status, detail, source="recorded_data": checks.append(CheckOut(key=key, label=label, status=status, detail=detail, source=source))

        # 1. Policy validity on the admission date
        if p.status != "active":
            add("validity", "Policy status", "fail", f"Policy is recorded as {p.status}.")
        elif p.expiry_date and on > p.expiry_date:
            add("validity", "Policy active on admission date", "fail", f"Policy expired on {p.expiry_date:%d %b %Y}, before the admission date {on:%d %b %Y}.")
        elif p.start_date and on < p.start_date:
            add("validity", "Policy active on admission date", "fail", f"Policy starts on {p.start_date:%d %b %Y}, after the admission date.")
        elif not p.expiry_date:
            add("validity", "Policy active on admission date", "unknown", "No expiry date is recorded for this policy.")
        else:
            add("validity", "Policy active on admission date", "pass", f"Valid until {p.expiry_date:%d %b %Y}.")

        # 2. Initial waiting period
        if p.start_date and p.initial_waiting_days:
            elapsed = (on - p.start_date).days
            if req.is_emergency_or_accident:
                add("initial_waiting", "Initial waiting period", "info",
                    f"{p.initial_waiting_days}-day initial waiting period is normally waived for accidents; confirm with the insurer.")
            elif elapsed < p.initial_waiting_days:
                add("initial_waiting", "Initial waiting period", "fail",
                    f"Only {max(elapsed, 0)} days since policy start; recorded initial waiting period is {p.initial_waiting_days} days.")
            else:
                add("initial_waiting", "Initial waiting period", "pass", f"{elapsed} days since policy start (waiting period {p.initial_waiting_days} days).")
        elif not p.start_date:
            add("initial_waiting", "Initial waiting period", "unknown", "No policy start date is recorded, so the waiting period could not be checked.")

        # 3. Network / empanelment at this hospital
        e = match_empanelment(p, emps)
        ns = network_status(p, emps, on)
        who = f"{p.insurer}" + (f" / TPA {p.tpa_name}" if p.tpa_name else "")
        if ns == "empanelled_cashless":
            add("network", "Network at this hospital", "pass", f"{e.insurer} is empanelled with this hospital for cashless treatment.", "hospital_setup")
        elif ns == "empanelled_no_cashless":
            add("network", "Network at this hospital", "warn", f"{e.insurer} is empanelled but cashless is switched off in the hospital setup; reimbursement route.", "hospital_setup")
        elif ns == "expired":
            add("network", "Network at this hospital", "warn", f"Empanelment with {e.insurer} is recorded as valid only until {e.valid_until:%d %b %Y}; confirm it was renewed.", "hospital_setup")
        else:
            add("network", "Network at this hospital", "warn", f"{who} is not in this hospital's empanelment list. Cashless is unlikely; treat as reimbursement.", "hospital_setup")

        # 4. Sum insured vs already booked claims
        used = utilised_amount(claims, p.id)
        remaining = float(p.sum_insured or 0) - used
        if float(p.sum_insured or 0) <= 0:
            add("sum_insured", "Remaining sum insured", "unknown", "No sum insured is recorded.")
        elif remaining <= 0:
            add("sum_insured", "Remaining sum insured", "fail", f"Recorded claims ({inr(used)}) have used up the sum insured ({inr(p.sum_insured)}).")
        elif req.estimated_amount and req.estimated_amount > remaining:
            add("sum_insured", "Remaining sum insured", "warn", f"Estimate {inr(req.estimated_amount)} exceeds the remaining {inr(remaining)}; the patient may need to pay the balance.")
        else:
            tail = f" Estimate {inr(req.estimated_amount)} fits." if req.estimated_amount else ""
            add("sum_insured", "Remaining sum insured", "pass", f"{inr(remaining)} remaining of {inr(p.sum_insured)} (booked claims: {inr(used)}).{tail}")

        # 5. Recorded exclusions / waiting-period text vs treatment
        details = p.details or {}
        if req.treatment:
            words = {w for w in re.findall(r"[a-z]{4,}", req.treatment.lower())}
            hits = []
            for key, label in (("exclusions", "exclusions"), ("waiting_periods", "waiting periods")):
                text = ((details.get(key) or {}).get("value") or "").lower()
                found = sorted(w for w in words if w in text)
                if found:
                    hits.append(f"recorded {label} mention '{', '.join(found)}'")
            if hits:
                add("treatment", "Treatment vs recorded terms", "warn", "; ".join(hits).capitalize() + ". Verify the exact clause with the insurer.")
            elif details.get("exclusions") or details.get("waiting_periods"):
                add("treatment", "Treatment vs recorded terms", "pass", "No match with the recorded exclusion / waiting-period text (this is a keyword check, not a clause review).")
            else:
                add("treatment", "Treatment vs recorded terms", "unknown", "No exclusions or waiting periods are recorded for this policy.")

        # 6. Advisories
        if (details.get("room_rent_limit") or {}).get("value"):
            add("room_rent", "Room rent limit", "info", f"Recorded: {details['room_rent_limit']['value']}. Room choice can reduce the payable amount.")
        if (details.get("copay") or {}).get("value"):
            add("copay", "Co-payment", "info", f"Recorded: {details['copay']['value']}. Patient pays this share.")

        statuses = {c.key: c.status for c in checks}
        if "fail" in statuses.values():
            verdict = "not_eligible"
        elif "warn" == statuses.get("treatment") or "unknown" in (statuses.get("validity"), statuses.get("initial_waiting")):
            verdict = "needs_review"
        elif ns == "empanelled_cashless":
            verdict = "eligible_cashless"
        else:
            verdict = "eligible_reimbursement"
        return EligibilityOut(policy_id=p.id, policy_name=p.name, insurer=p.insurer, verdict=verdict,
                              verdict_label=VERDICT_LABELS[verdict], checks=checks, disclaimer=DISCLAIMER)
