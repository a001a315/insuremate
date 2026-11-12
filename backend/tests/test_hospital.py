import uuid
from datetime import date, timedelta

from tests.conftest import make_pdf, new_patient, new_policy, upload


def d(n):
    return (date.today() + timedelta(days=n)).isoformat()


def empanel(client, h, insurer="Sample Mutual", **o):
    r = client.post("/api/hospital/empanelments", json={"insurer": insurer, **o}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def check(client, h, patient_id, **body):
    r = client.post(f"/api/patients/{patient_id}/eligibility", json=body, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def by_key(result):
    return {c["key"]: c for c in result["checks"]}


def test_patient_crud_and_list_summary(client, auth_headers):
    pt = new_patient(client, auth_headers, "Ravi Nair", mrn="MRN-1")
    p = new_policy(client, auth_headers, patient_id=pt["id"], start_date=d(-200), expiry_date=d(100))
    client.post("/api/claims", json={"policy_id": p["id"], "patient_id": pt["id"], "claim_amount": 1000, "status": "approved"}, headers=auth_headers)
    row = client.get("/api/patients?q=MRN-1", headers=auth_headers).json()[0]
    assert row["active_policies"] == 1 and row["latest_clearance"] == "cleared" and row["insurance_state"] == "active"
    assert client.get("/api/patients?q=nobody", headers=auth_headers).json() == []
    assert client.patch(f"/api/patients/{pt['id']}", json={"phone": "123"}, headers=auth_headers).json()["phone"] == "123"
    assert client.delete(f"/api/patients/{pt['id']}", headers=auth_headers).status_code == 204
    assert client.get("/api/policies", headers=auth_headers).json() == []
    assert client.get("/api/claims", headers=auth_headers).json() == []


def test_policy_and_claim_must_belong_to_a_real_matching_patient(client, auth_headers, other_headers):
    pt = new_patient(client, auth_headers, "A")
    other = new_patient(client, auth_headers, "B")
    p = new_policy(client, auth_headers, patient_id=pt["id"])
    base = {"policy_id": p["id"], "claim_amount": 10}
    assert client.post("/api/claims", json={**base, "patient_id": other["id"]}, headers=auth_headers).status_code == 422
    ok = client.post("/api/claims", json={**base, "patient_id": pt["id"]}, headers=auth_headers).json()
    assert ok["patient_name"] == "A" and ok["clearance"] == "draft" and ok["hospital_name"] == "Test City Hospital"
    # another hospital's patient is invisible
    foreign = new_patient(client, other_headers, "Z")
    r = client.post("/api/policies", json={"patient_id": foreign["id"], "name": "x", "insurer": "i", "policy_number": "1",
                                           "policyholder_name": "Z", "sum_insured": 1}, headers=auth_headers)
    assert r.status_code == 404
    assert client.get(f"/api/patients/{foreign['id']}", headers=auth_headers).status_code == 404
    assert client.post(f"/api/patients/{foreign['id']}/eligibility", json={}, headers=auth_headers).status_code == 404


def test_claim_clearance_and_rejection_reason(client, auth_headers):
    pt = new_patient(client, auth_headers)
    p = new_policy(client, auth_headers, patient_id=pt["id"])
    c = client.post("/api/claims", json={"policy_id": p["id"], "patient_id": pt["id"], "status": "pre_auth_requested"}, headers=auth_headers).json()
    assert c["clearance"] == "pending"
    c = client.post(f"/api/claims/{c['id']}/status", json={"status": "pre_auth_approved"}, headers=auth_headers).json()
    assert c["clearance"] == "pre_auth_cleared"
    c = client.post(f"/api/claims/{c['id']}/status", json={"status": "rejected", "rejection_reason": "Waiting period"}, headers=auth_headers).json()
    assert c["clearance"] == "rejected" and c["rejection_reason"] == "Waiting period"
    c = client.post(f"/api/claims/{c['id']}/status", json={"status": "approved", "approved_amount": 900, "insurer_reference": "R-1"}, headers=auth_headers).json()
    assert c["clearance"] == "cleared" and c["rejection_reason"] is None and c["insurer_reference"] == "R-1"


def test_empanelment_crud_and_policy_network_status(client, auth_headers):
    pt = new_patient(client, auth_headers)
    new_policy(client, auth_headers, patient_id=pt["id"], insurer="Sample Mutual Health Insurance Co.")
    assert client.get("/api/policies", headers=auth_headers).json()[0]["network_status"] == "not_empanelled"
    e = empanel(client, auth_headers, "Sample Mutual")
    assert client.get("/api/policies", headers=auth_headers).json()[0]["network_status"] == "empanelled_cashless"
    client.patch(f"/api/hospital/empanelments/{e['id']}", json={"cashless_enabled": False}, headers=auth_headers)
    assert client.get("/api/policies", headers=auth_headers).json()[0]["network_status"] == "empanelled_no_cashless"
    client.patch(f"/api/hospital/empanelments/{e['id']}", json={"cashless_enabled": True, "valid_until": d(-5)}, headers=auth_headers)
    assert client.get("/api/policies", headers=auth_headers).json()[0]["network_status"] == "expired"
    assert client.delete(f"/api/hospital/empanelments/{e['id']}", headers=auth_headers).status_code == 204
    assert client.patch("/api/hospital/profile", json={"hospital_name": "New Name"}, headers=auth_headers).json()["hospital_name"] == "New Name"


def test_eligible_cashless_when_everything_lines_up(client, auth_headers):
    pt = new_patient(client, auth_headers)
    new_policy(client, auth_headers, patient_id=pt["id"], start_date=d(-300), expiry_date=d(60))
    empanel(client, auth_headers)
    r = check(client, auth_headers, pt["id"], estimated_amount=200000)[0]
    assert r["verdict"] == "eligible_cashless" and "not an approval" in r["disclaimer"]
    k = by_key(r)
    assert k["network"]["status"] == "pass" and k["network"]["source"] == "hospital_setup"
    assert k["validity"]["status"] == "pass" and k["sum_insured"]["status"] == "pass"


def test_not_empanelled_means_reimbursement_only(client, auth_headers):
    pt = new_patient(client, auth_headers)
    new_policy(client, auth_headers, patient_id=pt["id"], start_date=d(-300), expiry_date=d(60))
    r = check(client, auth_headers, pt["id"])[0]
    assert r["verdict"] == "eligible_reimbursement" and by_key(r)["network"]["status"] == "warn"


def test_expired_policy_and_admission_outside_period(client, auth_headers):
    pt = new_patient(client, auth_headers)
    new_policy(client, auth_headers, patient_id=pt["id"], start_date=d(-400), expiry_date=d(-10))
    empanel(client, auth_headers)
    r = check(client, auth_headers, pt["id"])[0]
    assert r["verdict"] == "not_eligible" and by_key(r)["validity"]["status"] == "fail"
    # admission date inside the validity window passes even though today is past expiry
    r2 = check(client, auth_headers, pt["id"], admission_date=d(-100))[0]
    assert by_key(r2)["validity"]["status"] == "pass"


def test_initial_waiting_period_and_accident_exemption(client, auth_headers):
    pt = new_patient(client, auth_headers)
    new_policy(client, auth_headers, patient_id=pt["id"], start_date=d(-10), expiry_date=d(355), initial_waiting_days=30)
    empanel(client, auth_headers)
    r = check(client, auth_headers, pt["id"])[0]
    assert r["verdict"] == "not_eligible" and by_key(r)["initial_waiting"]["status"] == "fail"
    acc = check(client, auth_headers, pt["id"], is_emergency_or_accident=True)[0]
    assert by_key(acc)["initial_waiting"]["status"] == "info" and acc["verdict"] == "eligible_cashless"


def test_sum_insured_is_reduced_by_booked_claims(client, auth_headers):
    pt = new_patient(client, auth_headers)
    p = new_policy(client, auth_headers, patient_id=pt["id"], sum_insured=100000, start_date=d(-300), expiry_date=d(60))
    empanel(client, auth_headers)
    client.post("/api/claims", json={"policy_id": p["id"], "patient_id": pt["id"], "claim_amount": 70000, "status": "settled", "approved_amount": 60000}, headers=auth_headers)
    r = check(client, auth_headers, pt["id"], estimated_amount=50000)[0]
    assert by_key(r)["sum_insured"]["status"] == "warn" and "40,000" in by_key(r)["sum_insured"]["detail"]
    client.post("/api/claims", json={"policy_id": p["id"], "patient_id": pt["id"], "claim_amount": 40000, "status": "approved"}, headers=auth_headers)
    assert check(client, auth_headers, pt["id"])[0]["verdict"] == "not_eligible"


def test_treatment_keywords_against_recorded_exclusions_need_review(client, auth_headers):
    pt = new_patient(client, auth_headers)
    new_policy(client, auth_headers, patient_id=pt["id"], start_date=d(-300), expiry_date=d(60),
               details={"waiting_periods": {"value": "Cataract surgery: 24 months"}})
    empanel(client, auth_headers)
    r = check(client, auth_headers, pt["id"], treatment="Cataract surgery")[0]
    assert r["verdict"] == "needs_review" and "cataract" in by_key(r)["treatment"]["detail"].lower()
    ok = check(client, auth_headers, pt["id"], treatment="Appendectomy")[0]
    assert ok["verdict"] == "eligible_cashless"


def test_missing_dates_are_unknown_not_assumed(client, auth_headers):
    pt = new_patient(client, auth_headers)
    new_policy(client, auth_headers, patient_id=pt["id"], expiry_date=None)
    empanel(client, auth_headers)
    r = check(client, auth_headers, pt["id"])[0]
    assert r["verdict"] == "needs_review" and by_key(r)["validity"]["status"] == "unknown"


def test_documents_inherit_patient_and_filter(client, auth_headers):
    pt = new_patient(client, auth_headers)
    p = new_policy(client, auth_headers, patient_id=pt["id"])
    doc = upload(client, auth_headers, make_pdf(), policy_id=p["id"]).json()
    assert doc["patient_id"] == pt["id"]
    assert len(client.get(f"/api/documents?patient_id={pt['id']}", headers=auth_headers).json()) == 1
    other = new_patient(client, auth_headers, "Someone else")
    assert client.get(f"/api/documents?patient_id={other['id']}", headers=auth_headers).json() == []


def test_assistant_answers_eligibility_and_clearance_from_data(client, auth_headers, fake_llm):
    pt = new_patient(client, auth_headers, "Asha Verma")
    p = new_policy(client, auth_headers, patient_id=pt["id"], start_date=d(-300), expiry_date=d(60))
    empanel(client, auth_headers)
    client.post("/api/claims", json={"policy_id": p["id"], "patient_id": pt["id"], "claim_amount": 5000, "status": "rejected",
                                     "rejection_reason": "Documents missing"}, headers=auth_headers)
    cid = client.post("/api/chat/conversations", json={"patient_id": pt["id"]}, headers=auth_headers).json()["id"]
    ask = lambda q: client.post(f"/api/chat/conversations/{cid}/messages", json={"question": q, "patient_id": pt["id"]}, headers=auth_headers).json()["content"]
    e = ask("Is this patient eligible for cashless here?")
    assert "Likely eligible for cashless" in e and "insurer/TPA decides" in e
    s = ask("What is the claim status?")
    assert "Rejected" in s and "Documents missing" in s and "Asha Verma" in s
    assert fake_llm.calls == []


def test_pre_auth_follow_up_reminder_and_hospital_isolation(client, auth_headers, other_headers):
    from app.database.session import SessionLocal
    from app.models import Claim
    pt = new_patient(client, auth_headers)
    p = new_policy(client, auth_headers, patient_id=pt["id"])
    c = client.post("/api/claims", json={"policy_id": p["id"], "patient_id": pt["id"], "status": "pre_auth_requested"}, headers=auth_headers).json()
    with SessionLocal() as db:
        row = db.get(Claim, uuid.UUID(c["id"]))
        from datetime import datetime
        row.created_at = datetime.utcnow() - timedelta(days=3)
        db.commit()
    assert client.post("/api/reminders/run-checks", headers=auth_headers).json()["reminders_created"] == 1
    assert client.post("/api/reminders/run-checks", headers=auth_headers).json()["reminders_created"] == 0
    # the other hospital sees none of it
    for url in ("/api/patients", "/api/hospital/empanelments", "/api/claims", "/api/policies"):
        assert client.get(url, headers=other_headers).json() == []
    assert client.get("/api/dashboard", headers=other_headers).json()["summary"]["patients"] == 0


def test_demo_data_covers_every_hospital_scenario(client, auth_headers, fake_llm):
    r = client.post("/api/account/demo-data", headers=auth_headers).json()
    assert r["status"] == "loaded" and r["patients"] == 4
    pts = {p["full_name"]: p for p in client.get("/api/patients", headers=auth_headers).json()}
    assert all(n.startswith("[DEMO]") for n in pts)
    states = {n.split("] ")[1]: p["insurance_state"] for n, p in pts.items()}
    assert states["Asha Verma"] == "expiring_soon" and states["Meena Iyer"] == "active"
    kiran = pts["[DEMO] Kiran Shah"]
    k = check(client, auth_headers, kiran["id"])[0]
    assert k["verdict"] == "not_eligible" and by_key(k)["network"]["status"] == "warn"   # not empanelled + inside waiting period
    asha = check(client, auth_headers, pts["[DEMO] Asha Verma"]["id"])[0]
    assert asha["verdict"] == "eligible_cashless"
    sm = client.get("/api/dashboard", headers=auth_headers).json()["summary"]
    assert sm["rejected_claims"] == 1 and sm["cleared_claims"] == 1 and sm["pending_claims"] == 2
    # clearing the data leaves the account's own records alone: demo can be reloaded only once
    assert client.post("/api/account/demo-data", headers=auth_headers).json()["status"] == "already_loaded"
