from tests.conftest import make_pdf, new_policy, upload


def claim_body(pid, patient_id, **o):
    b = {"policy_id": pid, "patient_id": patient_id, "hospital_name": "Sample Hospital", "claim_amount": 50000}
    b.update(o)
    return b


def test_claim_lifecycle_timeline_and_notes(client, auth_headers):
    p = new_policy(client, auth_headers)
    c = client.post("/api/claims", json=claim_body(p["id"], p["patient_id"]), headers=auth_headers).json()
    assert c["status"] == "draft" and c["claim_ref"].startswith("CLM-")
    r = client.post(f"/api/claims/{c['id']}/status", json={"status": "submitted"}, headers=auth_headers).json()
    assert r["status"] == "submitted" and r["submission_date"]
    r = client.post(f"/api/claims/{c['id']}/status", json={"status": "partially_approved", "approved_amount": 40000,
                    "note": "after call"}, headers=auth_headers).json()
    assert r["approved_amount"] == 40000
    client.post(f"/api/claims/{c['id']}/notes", json={"note": "Called insurer"}, headers=auth_headers)
    acts = client.get(f"/api/claims/{c['id']}/activity", headers=auth_headers).json()
    kinds = [a["action"] for a in acts]
    assert "claim.status_changed" in kinds and "claim.note_added" in kinds
    assert any("manually updated" in a["summary"] for a in acts)  # never implies insurer sync


def test_claim_validation_and_policy_ownership(client, auth_headers, other_headers):
    p = new_policy(client, auth_headers)
    bad = client.post("/api/claims", json=claim_body(p["id"], p["patient_id"], hospitalization_date="2026-05-10",
                      discharge_date="2026-05-01"), headers=auth_headers)
    assert bad.status_code == 422
    assert client.post("/api/claims", json=claim_body(p["id"], p["patient_id"]), headers=other_headers).status_code == 404
    assert client.post("/api/claims", json=claim_body(p["id"], p["patient_id"], status="bogus"), headers=auth_headers).status_code == 422


def test_attach_documents_to_claim(client, auth_headers):
    p = new_policy(client, auth_headers)
    c = client.post("/api/claims", json=claim_body(p["id"], p["patient_id"]), headers=auth_headers).json()
    d = upload(client, auth_headers, make_pdf(), category="hospital_bill").json()
    assert client.post(f"/api/claims/{c['id']}/documents", json={"document_id": d["id"]}, headers=auth_headers).status_code == 201
    client.post(f"/api/claims/{c['id']}/documents", json={"document_id": d["id"]}, headers=auth_headers)  # idempotent
    docs = client.get(f"/api/claims/{c['id']}/documents", headers=auth_headers).json()
    assert [x["id"] for x in docs] == [d["id"]]
    assert client.delete(f"/api/claims/{c['id']}/documents/{d['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/claims/{c['id']}/documents", headers=auth_headers).json() == []


def test_medical_records_filters_and_links(client, auth_headers):
    p = new_policy(client, auth_headers)
    c = client.post("/api/claims", json=claim_body(p["id"], p["patient_id"]), headers=auth_headers).json()
    base = {"patient_id": p["patient_id"], "claim_id": c["id"], "policy_id": p["id"]}
    client.post("/api/records", json={**base, "title": "Discharge summary", "category": "discharge_summary",
                                      "record_date": "2026-04-02"}, headers=auth_headers)
    client.post("/api/records", json={"title": "Blood test", "category": "lab_report", "patient_id": p["patient_id"],
                                      "record_date": "2025-01-10"}, headers=auth_headers)
    allr = client.get("/api/records", headers=auth_headers).json()
    assert [r["title"] for r in allr] == ["Discharge summary", "Blood test"]  # newest first
    assert len(client.get("/api/records?category=lab_report", headers=auth_headers).json()) == 1
    assert len(client.get("/api/records?q=discharge", headers=auth_headers).json()) == 1
    assert len(client.get("/api/records?date_from=2026-01-01", headers=auth_headers).json()) == 1
    assert len(client.get(f"/api/records?claim_id={c['id']}", headers=auth_headers).json()) == 1
    bad = client.post("/api/records", json={"title": "x", "category": "nope", "patient_id": p["patient_id"]}, headers=auth_headers)
    assert bad.status_code == 422
