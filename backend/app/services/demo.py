"""Clearly-labelled fictional demo data for a hospital insurance desk. No real people, hospitals or insurers."""
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (Claim, ClaimDocument, Document, Empanelment, InsuredMember, MedicalRecord, Patient, Policy,
                        Reminder, User)
from app.services.documents.service import DocumentService
from app.services.rag.ingestion import ingest_document

POLICY_TEXT = [
    """DEMO DOCUMENT - FICTIONAL. Sample Mutual Health Insurance Co.
Family Health Shield - Policy Wording (Page 1)
Sum Insured: The Sum Insured under this policy is INR 10,00,000 per policy year on a family floater basis.
Policy period: twelve months from the policy start date. The policy may be renewed before the expiry date.""",
    """Waiting Periods (Page 2)
Pre-existing diseases are covered only after a waiting period of 36 months of continuous coverage.
Specified conditions such as cataract, hernia and joint replacement carry a waiting period of 24 months.
An initial waiting period of 30 days applies to all illnesses other than accidents.""",
    """Room Rent and Co-payment (Page 3)
Room rent is capped at 1 percent of the Sum Insured per day for a normal room and 2 percent per day for ICU.
A co-payment of 10 percent applies to every claim for insured members aged above 60 years.
Treatment at network hospitals may be availed on a cashless basis with prior authorisation.""",
    """Exclusions (Page 4)
The following are not covered: cosmetic surgery unless required after an accident, dental treatment unless caused by accident,
infertility treatment, self-inflicted injury, and experimental treatments. Expenses for non-medical items are excluded.""",
    """Benefits and Claims (Page 5)
Restoration benefit: the Sum Insured is restored once during the policy year if exhausted.
No-claim bonus: 10 percent increase of the Sum Insured for each claim-free year, up to a maximum of 50 percent.
Documents required for a reimbursement claim: duly filled claim form, original hospital bills and receipts,
discharge summary, investigation reports, prescriptions, and the policy number. Claims must be intimated within 48 hours of admission.""",
]


def _make_pdf(path, pages: list[str]) -> None:
    import pymupdf as fitz
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(50, 50, 545, 790), text, fontsize=11)
    doc.save(str(path))


def load_demo_data(db: Session, user: User) -> dict:
    if db.query(Patient).filter(Patient.user_id == user.id, Patient.full_name.like("[DEMO]%")).first():
        return {"status": "already_loaded"}
    today = date.today()
    if not user.hospital_name:
        user.hospital_name = "[DEMO] Sample City Hospital"
    uid = user.id

    # --- hospital setup: which insurers/TPAs this hospital works with
    db.add_all([
        Empanelment(user_id=uid, insurer="Sample Mutual Health Insurance Co.", tpa_name="Demo TPA Services", cashless_enabled=True,
                    valid_until=today + timedelta(days=300), notes="[DEMO] fictional empanelment"),
        Empanelment(user_id=uid, insurer="Fictional Assure General Insurance", cashless_enabled=True,
                    valid_until=today + timedelta(days=150), notes="[DEMO] fictional empanelment"),
        Empanelment(user_id=uid, insurer="Imaginary Shield Insurance", cashless_enabled=False,
                    notes="[DEMO] empanelled for reimbursement paperwork only"),
    ])

    # --- patients
    asha = Patient(user_id=uid, full_name="[DEMO] Asha Verma", mrn="MRN-DEMO-001", gender="female", date_of_birth=date(1981, 4, 12))
    ravi = Patient(user_id=uid, full_name="[DEMO] Ravi Nair", mrn="MRN-DEMO-002", gender="male", date_of_birth=date(1974, 9, 3))
    meena = Patient(user_id=uid, full_name="[DEMO] Meena Iyer", mrn="MRN-DEMO-003", gender="female", date_of_birth=date(1957, 1, 21))
    kiran = Patient(user_id=uid, full_name="[DEMO] Kiran Shah", mrn="MRN-DEMO-004", gender="male", date_of_birth=date(1995, 6, 30))
    db.add_all([asha, ravi, meena, kiran])
    db.flush()

    # --- policies
    p1 = Policy(user_id=uid, patient_id=asha.id, name="[DEMO] Family Health Shield", insurer="Sample Mutual Health Insurance Co.",
                tpa_name="Demo TPA Services", policy_number="DEMO-FHS-0012345", policy_type="family_floater",
                policyholder_name="Asha Verma", sum_insured=Decimal(1000000), premium_amount=Decimal(24500),
                start_date=today - timedelta(days=335), expiry_date=today + timedelta(days=28), renewal_date=today + timedelta(days=28),
                initial_waiting_days=30, status="active",
                details={"waiting_periods": {"value": "Pre-existing diseases: 36 months; specified conditions such as cataract, hernia, joint replacement: 24 months", "source": "manual"},
                         "exclusions": {"value": "Cosmetic surgery, dental treatment unless accidental, infertility treatment", "source": "manual"},
                         "room_rent_limit": {"value": "1% of sum insured per day (ICU 2%)", "source": "manual"}})
    p2 = Policy(user_id=uid, patient_id=ravi.id, name="[DEMO] Gold Cover", insurer="Fictional Assure General Insurance",
                policy_number="DEMO-GLD-5544332", policy_type="individual", policyholder_name="Ravi Nair",
                sum_insured=Decimal(500000), premium_amount=Decimal(12800), start_date=today - timedelta(days=400),
                expiry_date=today + timedelta(days=150), renewal_date=today + timedelta(days=150), initial_waiting_days=30, status="active",
                details={"copay": {"value": "10% on every claim", "source": "manual"}})
    p2old = Policy(user_id=uid, patient_id=ravi.id, name="[DEMO] Silver Cover (previous)", insurer="Fictional Assure General Insurance",
                   policy_number="DEMO-SLV-1100220", policy_type="individual", policyholder_name="Ravi Nair",
                   sum_insured=Decimal(300000), premium_amount=Decimal(9000), start_date=today - timedelta(days=760),
                   expiry_date=today - timedelta(days=60), renewal_date=today - timedelta(days=60), status="expired")
    p3 = Policy(user_id=uid, patient_id=meena.id, name="[DEMO] Senior Care", insurer="Imaginary Shield Insurance",
                policy_number="DEMO-SNR-9988776", policy_type="senior_citizen", policyholder_name="Meena Iyer",
                sum_insured=Decimal(600000), premium_amount=Decimal(31000), start_date=today - timedelta(days=120),
                expiry_date=today + timedelta(days=245), renewal_date=today + timedelta(days=245), initial_waiting_days=30, status="active",
                details={"copay": {"value": "20% for members above 60", "source": "manual"}})
    p4 = Policy(user_id=uid, patient_id=kiran.id, name="[DEMO] Basic Protect", insurer="Nowhere General Insurance (fictional)",
                policy_number="DEMO-BSC-4455667", policy_type="individual", policyholder_name="Kiran Shah",
                sum_insured=Decimal(300000), premium_amount=Decimal(6200), start_date=today - timedelta(days=10),
                expiry_date=today + timedelta(days=355), renewal_date=today + timedelta(days=355), initial_waiting_days=30, status="active")
    db.add_all([p1, p2, p2old, p3, p4])
    db.flush()

    # --- claims, covering each clearance state
    c_settled = Claim(user_id=uid, policy_id=p1.id, patient_id=asha.id, patient_name=asha.full_name, claim_ref="CLM-DEMO-0001",
                      hospital_name=user.hospital_name, claim_amount=Decimal(42000), approved_amount=Decimal(37800), claim_type="cashless",
                      hospitalization_date=today - timedelta(days=95), discharge_date=today - timedelta(days=92),
                      submission_date=today - timedelta(days=90), status="settled", insurer_reference="DEMO-INS-77120")
    c_docs = Claim(user_id=uid, policy_id=p1.id, patient_id=asha.id, patient_name=asha.full_name, claim_ref="CLM-DEMO-0002",
                   hospital_name=user.hospital_name, claim_amount=Decimal(185000), claim_type="reimbursement",
                   hospitalization_date=today - timedelta(days=40), discharge_date=today - timedelta(days=36),
                   submission_date=today - timedelta(days=30), status="additional_documents_required",
                   notes="Demo claim. Discharge summary requested by the insurer.")
    c_rej = Claim(user_id=uid, policy_id=p2.id, patient_id=ravi.id, patient_name=ravi.full_name, claim_ref="CLM-DEMO-0003",
                  hospital_name=user.hospital_name, claim_amount=Decimal(120000), claim_type="cashless",
                  hospitalization_date=today - timedelta(days=20), submission_date=today - timedelta(days=18), status="rejected",
                  rejection_reason="[DEMO] Treatment falls under a specified-condition waiting period")
    c_pre = Claim(user_id=uid, policy_id=p3.id, patient_id=meena.id, patient_name=meena.full_name, claim_ref="CLM-DEMO-0004",
                  hospital_name=user.hospital_name, claim_amount=Decimal(65000), claim_type="reimbursement", status="pre_auth_requested",
                  notes="Demo pre-authorisation request for a planned cataract procedure.")
    db.add_all([c_settled, c_docs, c_rej, c_pre])
    db.flush()
    db.add_all([
        MedicalRecord(user_id=uid, patient_id=asha.id, patient_name=asha.full_name, title="[DEMO] Discharge summary", category="discharge_summary",
                      provider=user.hospital_name, record_date=today - timedelta(days=36), claim_id=c_docs.id, policy_id=p1.id),
        MedicalRecord(user_id=uid, patient_id=ravi.id, patient_name=ravi.full_name, title="[DEMO] Orthopaedic consultation", category="consultation",
                      provider=user.hospital_name, record_date=today - timedelta(days=22), claim_id=c_rej.id, policy_id=p2.id),
        MedicalRecord(user_id=uid, patient_id=meena.id, patient_name=meena.full_name, title="[DEMO] Cataract consultation", category="consultation",
                      provider=user.hospital_name, record_date=today - timedelta(days=3), claim_id=c_pre.id, policy_id=p3.id),
    ])
    db.add(Reminder(user_id=uid, title="[DEMO] Ask Kiran Shah's insurer about cashless options", kind="custom", due_date=today + timedelta(days=2), policy_id=p4.id))
    db.commit()

    # fictional policy wording for Asha's policy, run through the real ingestion pipeline
    svc = DocumentService(db, uid)
    stored = f"{uuid.uuid4().hex}.pdf"
    path = svc.user_dir() / stored
    _make_pdf(path, POLICY_TEXT)
    doc = Document(user_id=uid, policy_id=p1.id, patient_id=asha.id, original_name="DEMO-Family-Health-Shield-Policy.pdf", stored_name=stored,
                   mime_type="application/pdf", size_bytes=path.stat().st_size, category="policy_document")
    db.add(doc)
    db.commit()
    db.add(ClaimDocument(user_id=uid, claim_id=c_docs.id, document_id=doc.id))
    db.commit()
    ingest_document(doc.id, uid)
    db.refresh(doc)
    return {"status": "loaded", "patients": 4, "policies": 5, "claims": 4, "empanelments": 3,
            "document_index_status": doc.index_status, "document_index_error": doc.index_error}
