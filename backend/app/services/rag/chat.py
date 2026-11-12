"""Assistant orchestration: scope → intent → (recorded-data answer | retrieval + LLM) → citations."""
import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models import Claim, Conversation, Message, Policy
from app.models.claim import CLEARED_STATUSES, PENDING_STATUSES, REJECTED_STATUSES, clearance_of
from app.repositories.entities import (ClaimRepository, ConversationRepository, MedicalRecordRepository,
                                       MessageRepository, PatientRepository, PolicyRepository)
from app.schemas.eligibility import EligibilityRequest
from app.services.eligibility.service import EligibilityService
from app.services.llm import LLMProvider
from app.services.rag.format import fmt_date, inr
from app.services.rag.prompt import (DETAIL_LABELS, DISCLAIMER, NO_INFO, SOURCE_LABEL, SYSTEM_PROMPT,
                                     build_user_prompt)
from app.services.rag.retrieval import retrieve

PENDING = PENDING_STATUSES
CLEARANCE_LABEL = {"cleared": "Cleared", "pre_auth_cleared": "Pre-auth cleared", "pending": "Pending", "rejected": "Rejected", "draft": "Draft"}
ALL_WORDS = re.compile(r"\b(all|both|each|every|across|compare|comparison|my policies|my insurance policies)\b", re.I)


@dataclass
class Plan:
    header: str = ""
    text: str | None = None          # final text when no LLM is needed
    messages: list[dict] | None = None  # LLM messages when generation is needed
    citations: list[dict] = field(default_factory=list)
    scope_policy_ids: list[uuid.UUID] = field(default_factory=list)
    patient_ids: list[uuid.UUID] = field(default_factory=list)
    disclaimer: bool = True


def _intent(q: str) -> str:
    ql = q.lower()
    if re.search(r"\b(eligib\w*|empanel\w*|cashless|accepted here|valid here)\b", ql):
        return "eligibility"
    if re.search(r"\bcompar", ql):
        return "compare"
    if re.search(r"medical records?|records?\b.*\bclaim|claim\b.*\brecords?", ql) and "claim" in ql:
        return "records_for_claim"
    if re.search(r"\bclaims?\b|\b(cleared|clearance|rejected|approved|pre-?auth\w*)\b", ql) and re.search(r"\b(status|pending|progress|stand|where|cleared|clearance|rejected|approved|pre-?auth\w*)\b", ql):
        return "claims_status"
    if re.search(r"\b(expir\w*|renew\w*|valid until|end date|due date)\b", ql) and not re.search(r"waiting|exclusion", ql):
        return "expiry"
    if re.search(r"\b(total|overall)\b.*\b(coverage|cover|sum insured)\b|\bsum insured\b|how much .*\b(covered|coverage)\b", ql):
        return "coverage"
    if re.search(r"\bsummar", ql):
        return "summary"
    return "rag"


class ChatService:
    def __init__(self, db: Session, user_id: uuid.UUID, llm: LLMProvider):
        self.db, self.user_id, self.llm = db, user_id, llm
        self.policies = PolicyRepository(db, user_id)
        self.patients = PatientRepository(db, user_id)
        self._patient_ids: list[uuid.UUID] = []

    # ---------- scope ----------
    def _active(self) -> list[Policy]:
        return [p for p in self.policies.list() if p.status != "archived"]

    def _scope(self, question: str, policy_id: uuid.UUID | None, intent: str,
               patient_id: uuid.UUID | None = None) -> tuple[list[Policy], str | None]:
        """Returns (policies, clarification). Clarification is set when we must ask which patient/policy."""
        self._patient_ids = []
        if policy_id:
            p = self.policies.get(policy_id)
            if p and p.patient_id:
                self._patient_ids = [p.patient_id]
            return ([p] if p else []), (None if p else "I couldn't find that policy.")
        ql = question.lower()
        everyone = self.patients.search()
        if patient_id:
            chosen = [x for x in everyone if x.id == patient_id]
            if not chosen:
                return [], "I couldn't find that patient."
        else:
            chosen = [x for x in everyone if x.full_name.lower() in ql]
        active = self._active()
        if chosen:
            self._patient_ids = [x.id for x in chosen]
            active = [p for p in active if p.patient_id in set(self._patient_ids)]
            if not active and intent not in {"claims_status", "records_for_claim"}:
                return [], f"No policy is recorded for {', '.join(x.full_name for x in chosen)}. Add the patient's policy first."
        if len(active) <= 1:
            return active, None
        matched = [p for p in active if p.name.lower() in ql or p.insurer.lower() in ql
                   or (len(p.policy_number) >= 4 and p.policy_number[-4:].lower() in ql)]
        if len(matched) == 1:
            return matched, None
        hospital_wide = {"expiry", "coverage", "claims_status", "records_for_claim", "compare"}
        if matched or ALL_WORDS.search(question) or (intent in hospital_wide) or (chosen and intent == "eligibility"):
            return (matched or active), None
        names = "\n".join(f"- {p.name} ({p.insurer})" for p in active[:15])
        return [], f"More than one policy could apply. Which patient or policy do you mean?\n\n{names}\n\nSelect a patient or policy above the chat box, or mention the patient's name."

    # ---------- deterministic answers from recorded data ----------
    @staticmethod
    def _rec(p: Policy) -> dict:
        return {"type": "recorded_data", "label": f"{p.name} · recorded policy information", "policy_id": str(p.id)}

    def _expiry(self, ps):
        lines = [f"- **{p.name}** ({p.insurer}): expiry {fmt_date(p.expiry_date)}, renewal {fmt_date(p.renewal_date)}" for p in ps]
        return "From the dates **you recorded**:\n\n" + "\n".join(lines)

    def _coverage(self, ps):
        lines = [f"- **{p.name}** ({p.insurer}): {inr(p.sum_insured)}" for p in ps]
        total = sum(float(p.sum_insured or 0) for p in ps)
        tail = f"\n\n**Total across these policies: {inr(total)}**" if len(ps) > 1 else ""
        return "From the sum insured **you recorded**:\n\n" + "\n".join(lines) + tail

    def _claims(self, ps, question: str = ""):
        ids = {p.id for p in ps}
        pids = set(self._patient_ids)
        claims = [c for c in ClaimRepository(self.db, self.user_id).list_filtered()
                  if c.policy_id in ids or (c.patient_id in pids)]
        ql = question.lower()
        if "pending" in ql:
            claims = [c for c in claims if c.clearance == "pending"]
        elif "reject" in ql:
            claims = [c for c in claims if c.clearance == "rejected"]
        elif re.search(r"\bcleared|approved|settled\b", ql):
            claims = [c for c in claims if c.clearance in {"cleared", "pre_auth_cleared"}]
        if not claims:
            return "No matching claims are recorded."
        lines = []
        for c in claims[:25]:
            extra = f" — reason noted: {c.rejection_reason}" if c.rejection_reason else ""
            lines.append(f"- **{c.claim_ref}** · {c.patient_name} · {inr(c.claim_amount)} · **{CLEARANCE_LABEL[c.clearance]}** ({c.status.replace('_', ' ')}){extra}")
        return ("Claim clearance, with statuses **as your team recorded them** (this app does not check with insurers):\n\n"
                + "\n".join(lines))

    def _eligibility(self, ps: list[Policy], question: str) -> str:
        if len(self._patient_ids) != 1:
            return "Eligibility checks are done for one patient at a time. Select a patient above the chat box or mention the patient's name."
        results = EligibilityService(self.db, self.user_id).check_patient(
            self._patient_ids[0], EligibilityRequest(policy_id=ps[0].id if len(ps) == 1 else None))
        ICON = {"pass": "✅", "fail": "❌", "warn": "⚠️", "info": "ℹ️", "unknown": "❔"}
        out = []
        for r in results:
            out.append(f"**{r.policy_name}** ({r.insurer}) — **{r.verdict_label}**\n" + "\n".join(f"- {ICON[c.status]} {c.label}: {c.detail}" for c in r.checks))
        return ("Eligibility pre-check at this hospital, using **recorded data and your empanelment list** (admission date assumed today):\n\n"
                + "\n\n".join(out) + "\n\n*Advisory only; the insurer/TPA decides.*")

    def _records_for_claim(self, question: str):
        claims = ClaimRepository(self.db, self.user_id).list_filtered()
        ref = re.search(r"CLM-[A-Z0-9-]+", question.upper())
        claim: Claim | None = next((c for c in claims if ref and c.claim_ref.upper() == ref.group(0)), None)
        if not claim:
            if not claims:
                return "You have no claims recorded yet."
            opts = "\n".join(f"- {c.claim_ref} ({c.patient_name})" for c in claims[:10])
            return f"Which claim do you mean? Mention its ID, for example:\n\n{opts}"
        recs = MedicalRecordRepository(self.db, self.user_id).search(claim_id=claim.id)
        if not recs:
            return f"No medical records are linked to claim **{claim.claim_ref}**."
        lines = [f"- {r.title} · {r.category.replace('_', ' ')} · {fmt_date(r.record_date)}" for r in recs]
        return f"Medical records linked to claim **{claim.claim_ref}**:\n\n" + "\n".join(lines)

    def _table(self, ps: list[Policy]) -> str:
        head = "| | " + " | ".join(p.name for p in ps) + " |\n|---|" + "---|" * len(ps)
        rows = [("Insurer", [p.insurer for p in ps]), ("Type", [p.policy_type.replace("_", " ") for p in ps]),
                ("Sum insured", [inr(p.sum_insured) for p in ps]),
                ("Premium", [f"{inr(p.premium_amount)} / {p.premium_frequency.replace('_', ' ')}" for p in ps]),
                ("Expiry", [fmt_date(p.expiry_date) for p in ps])]
        for k, label in DETAIL_LABELS.items():
            vals = []
            for p in ps:
                f = (p.details or {}).get(k)
                vals.append(f"{f['value'][:120]} *({SOURCE_LABEL.get(f.get('source'), '?')})*" if f and f.get("value") else "Not recorded")
            rows.append((label, vals))
        return head + "\n" + "\n".join(f"| {l} | " + " | ".join(v.replace('|', '/').replace('\n', ' ') for v in vals) + " |" for l, vals in rows)

    # ---------- planning ----------
    def prepare(self, question: str, conv: Conversation, policy_id: uuid.UUID | None,
                patient_id: uuid.UUID | None = None) -> Plan:
        intent = _intent(question)
        ps, clarify = self._scope(question, policy_id, intent, patient_id)
        if clarify:
            return Plan(text=clarify, disclaimer=False)
        if not ps and intent == "claims_status" and self._patient_ids:
            return Plan(text=self._claims([], question), patient_ids=self._patient_ids)
        if not ps:
            return Plan(text="No policies are recorded yet. Register a patient, add their policy and upload the policy document to get started.", disclaimer=False)
        pnames = {x.id: x.full_name for x in self.patients.search()}
        who = sorted({pnames[p.patient_id] for p in ps if p.patient_id in pnames})
        plan = Plan(scope_policy_ids=[p.id for p in ps], patient_ids=self._patient_ids,
                    header=(f"**Patient:** {', '.join(who)}\n" if len(who) == 1 else "") + "**Policy:** " + ", ".join(p.name for p in ps) + "\n\n")
        plan.citations = [self._rec(p) for p in ps]
        if intent == "eligibility":
            plan.text = self._eligibility(ps, question)
        elif intent == "expiry":
            plan.text = self._expiry(ps)
        elif intent == "coverage":
            plan.text = self._coverage(ps)
        elif intent == "claims_status":
            plan.text = self._claims(ps, question)
        elif intent == "records_for_claim":
            plan.header, plan.text, plan.citations = "", self._records_for_claim(question), []
        elif intent == "compare":
            plan.text = (self._table(ps) if len(ps) > 1 else
                         "You need at least two policies to compare. Add another policy first.")
            if len(ps) > 1:
                plan.text += "\n\nValues come from the fields recorded in the app; clauses may differ in the original documents."
        else:
            chunks = retrieve(self.db, self.user_id, question, [p.id for p in ps])
            if not chunks:
                if intent == "summary":
                    plan.text = ("I have no indexed document text for this policy, so this summary uses only the "
                                 "information you recorded:\n\n" + self._table(ps))
                else:
                    return Plan(text=NO_INFO, scope_policy_ids=plan.scope_policy_ids, header=plan.header, disclaimer=False)
            else:
                history = [{"role": m.role, "content": m.content[:1500]}
                           for m in MessageRepository(self.db, self.user_id).for_conversation(conv.id)[-6:]]
                plan.messages = ([{"role": "system", "content": SYSTEM_PROMPT}] + history +
                                 [{"role": "user", "content": build_user_prompt(question, ps, chunks)}])
                plan.citations += [{"type": "document", "document_id": str(c.document_id), "document_name": c.document_name,
                                    "page_number": c.page_number, "excerpt": c.text[:300], "score": round(c.score, 3),
                                    "policy_id": str(c.policy_id) if c.policy_id else None} for c in chunks]
                plan.citations = plan.citations[len(ps):]  # document sources only for RAG answers
        return plan

    # ---------- execution ----------
    def complete(self, plan: Plan) -> str:
        body = plan.text if plan.messages is None else self.llm.generate(plan.messages).strip()
        return self._wrap(plan, body)

    def stream(self, plan: Plan) -> Iterator[str]:
        if plan.messages is None:
            yield self._wrap(plan, plan.text or "")
            return
        if plan.header:
            yield plan.header
        yield from self.llm.stream(plan.messages)
        if plan.disclaimer:
            yield DISCLAIMER

    @staticmethod
    def _wrap(plan: Plan, body: str) -> str:
        return plan.header + body + (DISCLAIMER if plan.disclaimer else "")

    # ---------- persistence ----------
    def save_turn(self, conv: Conversation, question: str, answer: str, citations: list[dict]) -> Message:
        msgs = MessageRepository(self.db, self.user_id)
        msgs.add(Message(conversation_id=conv.id, role="user", content=question))
        reply = msgs.add(Message(conversation_id=conv.id, role="assistant", content=answer, citations=citations))
        if conv.title == "New conversation":
            conv.title = question[:60]
        ConversationRepository(self.db, self.user_id).save(conv)
        return reply
