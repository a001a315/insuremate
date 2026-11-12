from datetime import date, timedelta

from tests.conftest import make_pdf, new_policy, upload


def soon(days):
    return (date.today() + timedelta(days=days)).isoformat()


def test_reminder_crud(client, auth_headers):
    r = client.post("/api/reminders", json={"title": "Pay premium", "kind": "premium", "due_date": soon(5)}, headers=auth_headers).json()
    assert client.patch(f"/api/reminders/{r['id']}", json={"title": "Pay premium now"}, headers=auth_headers).json()["title"] == "Pay premium now"
    done = client.patch(f"/api/reminders/{r['id']}", json={"is_completed": True}, headers=auth_headers).json()
    assert done["is_completed"]
    assert client.delete(f"/api/reminders/{r['id']}", headers=auth_headers).status_code == 204
    assert client.get("/api/reminders", headers=auth_headers).json() == []


def test_auto_reminders_and_notifications_are_idempotent(client, auth_headers):
    p = new_policy(client, auth_headers, expiry_date=soon(10))
    client.post("/api/claims", json={"policy_id": p["id"], "patient_id": p["patient_id"], "status": "additional_documents_required"}, headers=auth_headers)
    first = client.post("/api/reminders/run-checks", headers=auth_headers).json()
    assert first["reminders_created"] == 2 and first["notifications_created"] == 1   # claim-docs is due today
    second = client.post("/api/reminders/run-checks", headers=auth_headers).json()
    assert second == {"reminders_created": 0, "notifications_created": 0}
    kinds = {r["kind"] for r in client.get("/api/reminders", headers=auth_headers).json()}
    assert kinds == {"renewal", "claim_documents"}
    n = client.get("/api/notifications", headers=auth_headers).json()
    assert n["unread"] == 1
    client.post(f"/api/notifications/{n['items'][0]['id']}/read", headers=auth_headers)
    assert client.get("/api/notifications", headers=auth_headers).json()["unread"] == 0


def test_far_future_policy_gets_no_renewal_reminder(client, auth_headers):
    new_policy(client, auth_headers, expiry_date=soon(200))
    assert client.post("/api/reminders/run-checks", headers=auth_headers).json()["reminders_created"] == 0


def test_dashboard_numbers_and_insights_only_from_data(client, auth_headers):
    empty = client.get("/api/dashboard", headers=auth_headers).json()
    assert empty["summary"]["active_policies"] == 0 and empty["insights"] == []
    p = new_policy(client, auth_headers, expiry_date=soon(20), details={"room_rent_limit": {"value": "1% per day"}})
    new_policy(client, auth_headers, name="B", policy_number="B-1234567", sum_insured=500000, expiry_date=soon(300))
    client.post("/api/claims", json={"policy_id": p["id"], "patient_id": p["patient_id"], "status": "submitted"}, headers=auth_headers)
    d = client.get("/api/dashboard", headers=auth_headers).json()
    sm = d["summary"]
    assert (sm["active_policies"], sm["patients"], sm["expiring_policies"], sm["pending_claims"]) == (2, 2, 1, 1)
    assert sm["amount_pending"] == 0.0 and sm["rejected_claims"] == 0
    texts = " ".join(i["text"] for i in d["insights"])
    assert "expires in 20 days" in texts and "Asha Demo" in texts
    assert d["expiring"][0]["days_left"] == 20 and d["expiring"][0]["patient_name"] == "Asha Demo"
    assert d["activity"] and d["recent_claims"][0]["status"] == "submitted" and d["recent_claims"][0]["clearance"] == "pending"
    assert {"status": "submitted", "count": 1} in d["claims_by_status"]


def test_account_deletion_removes_everything(client, auth_headers, other_headers):
    from app.database.session import SessionLocal
    from app.models import Document, Policy, User
    from app.services.rag import vectorstore
    p = new_policy(client, auth_headers)
    upload(client, auth_headers, make_pdf(), policy_id=p["id"])
    q = new_policy(client, other_headers, policy_number="B-1234567")
    upload(client, other_headers, make_pdf(), policy_id=q["id"])
    assert client.post("/api/account/delete", json={"password": "wrong"}, headers=auth_headers).status_code == 403
    assert client.post("/api/account/delete", json={"password": "correct-horse-1"}, headers=auth_headers).status_code == 204
    assert client.get("/api/auth/me", headers=auth_headers).status_code == 401
    with SessionLocal() as db:
        assert db.query(User).count() == 1 and db.query(Policy).count() == 1 and db.query(Document).count() == 1
    assert vectorstore.stats()["vectors"] == 3   # only the other user's vectors remain
    assert client.get("/api/policies", headers=other_headers).status_code == 200


def test_demo_data_loads_and_indexes(client, auth_headers, fake_llm):
    r = client.post("/api/account/demo-data", headers=auth_headers).json()
    assert r["status"] == "loaded" and r["document_index_status"] == "indexed"
    assert client.post("/api/account/demo-data", headers=auth_headers).json()["status"] == "already_loaded"
    names = [p["name"] for p in client.get("/api/policies", headers=auth_headers).json()]
    assert all(n.startswith("[DEMO]") for n in names)
