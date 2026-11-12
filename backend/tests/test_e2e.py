from tests.conftest import make_pdf


def test_full_user_journey(client, fake_llm):
    # 1. register  2. log in
    client.post("/api/auth/register", json={"email": "e2e@example.com", "full_name": "E2E User", "password": "journey-pass-1",
                                                    "hospital_name": "E2E Hospital"})
    tok = client.post("/api/auth/login", json={"email": "e2e@example.com", "password": "journey-pass-1"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    # 3. register a patient and create their policy
    pt = client.post("/api/patients", json={"full_name": "E2E Patient"}, headers=h).json()
    p = client.post("/api/policies", json={"patient_id": pt["id"], "name": "Family Health Shield", "insurer": "Sample Mutual", "policy_number": "POL-1234567",
                                           "policyholder_name": "E2E User", "sum_insured": 1000000}, headers=h).json()
    # 4. upload an insurance document
    up = client.post("/api/documents", files={"file": ("policy.pdf", make_pdf(), "application/pdf")},
                     data={"category": "policy_document", "policy_id": p["id"]}, headers=h)
    assert up.status_code == 201
    # 5. wait for indexing (background task completes before the TestClient returns; poll defensively)
    for _ in range(20):
        d = client.get(f"/api/documents/{up.json()['id']}", headers=h).json()
        if d["index_status"] in ("indexed", "failed"):
            break
    assert d["index_status"] == "indexed"
    # 6. ask a question about the document  7. verify a source citation
    cid = client.post("/api/chat/conversations", json={"policy_id": p["id"]}, headers=h).json()["id"]
    reply = client.post(f"/api/chat/conversations/{cid}/messages",
                        json={"question": "What is the waiting period for pre-existing diseases?", "policy_id": p["id"]}, headers=h).json()
    assert reply["citations"] and reply["citations"][0]["document_name"] == "policy.pdf"
    assert reply["citations"][0]["page_number"] == 2
