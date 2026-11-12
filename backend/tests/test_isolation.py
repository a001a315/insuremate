"""One user must never see or touch another user's data."""
import uuid

from app.services.rag import vectorstore
from app.services.embeddings import get_embedding_provider
from tests.conftest import make_pdf, new_policy, upload, register


def test_cross_user_access_is_404_everywhere(client, auth_headers, other_headers):
    p = new_policy(client, auth_headers)
    c = client.post("/api/claims", json={"policy_id": p["id"], "patient_id": p["patient_id"]}, headers=auth_headers).json()
    d = upload(client, auth_headers, make_pdf(), policy_id=p["id"]).json()
    r = client.post("/api/records", json={"title": "t", "category": "other", "patient_id": p["patient_id"]}, headers=auth_headers).json()
    rem = client.post("/api/reminders", json={"title": "x", "due_date": "2027-01-01"}, headers=auth_headers).json()
    cv = client.post("/api/chat/conversations", json={}, headers=auth_headers).json()
    probes = [("get", f"/api/policies/{p['id']}"), ("patch", f"/api/policies/{p['id']}"), ("delete", f"/api/policies/{p['id']}"),
              ("get", f"/api/policies/{p['id']}/documents"), ("get", f"/api/claims/{c['id']}"),
              ("post", f"/api/claims/{c['id']}/status"), ("get", f"/api/claims/{c['id']}/activity"),
              ("get", f"/api/documents/{d['id']}"), ("get", f"/api/documents/{d['id']}/download"),
              ("get", f"/api/documents/{d['id']}/preview"), ("delete", f"/api/documents/{d['id']}"),
              ("post", f"/api/documents/{d['id']}/reindex"), ("get", f"/api/records/{r['id']}"),
              ("delete", f"/api/records/{r['id']}"), ("patch", f"/api/reminders/{rem['id']}"),
              ("delete", f"/api/reminders/{rem['id']}"), ("get", f"/api/chat/conversations/{cv['id']}/messages"),
              ("delete", f"/api/chat/conversations/{cv['id']}")]
    for method, url in probes:
        body = {"status": "submitted"} if url.endswith("/status") else {"name": "hacked"} if method == "patch" else None
        resp = getattr(client, method)(url, headers=other_headers, **({"json": body} if body else {}))
        assert resp.status_code == 404, f"{method} {url} -> {resp.status_code}"
    for url in ("/api/policies", "/api/claims", "/api/documents", "/api/records", "/api/reminders"):
        assert client.get(url, headers=other_headers).json() == []
    # still intact for the owner
    assert client.get(f"/api/policies/{p['id']}", headers=auth_headers).json()["name"] == "Family Health Shield"


def test_cannot_link_foreign_resources(client, auth_headers, other_headers):
    p = new_policy(client, auth_headers)
    d = upload(client, auth_headers, make_pdf(), policy_id=p["id"]).json()
    mine = new_policy(client, other_headers, policy_number="B-123456")
    c = client.post("/api/claims", json={"policy_id": mine["id"], "patient_id": mine["patient_id"]}, headers=other_headers).json()
    assert client.post(f"/api/claims/{c['id']}/documents", json={"document_id": d["id"]}, headers=other_headers).status_code == 404
    assert client.post("/api/records", json={"title": "t", "category": "other", "patient_id": p["patient_id"], "document_id": d["id"]},
                       headers=other_headers).status_code == 404
    assert upload(client, other_headers, make_pdf(), policy_id=p["id"]).status_code == 404


def test_retrieval_never_crosses_users(client, auth_headers, other_headers, fake_llm):
    from app.database.session import SessionLocal
    from app.services.rag.retrieval import retrieve
    from app.models import User
    p = new_policy(client, auth_headers)
    upload(client, auth_headers, make_pdf(), policy_id=p["id"])
    b_id = uuid.UUID(client.get("/api/auth/me", headers=other_headers).json()["id"])
    a_id = uuid.UUID(client.get("/api/auth/me", headers=auth_headers).json()["id"])
    qv = get_embedding_provider().embed_query("waiting period pre-existing diseases")
    assert vectorstore.query(a_id, qv, 5, None)             # owner finds it
    assert vectorstore.query(b_id, qv, 5, None) == []        # other user cannot, even with no policy filter
    assert vectorstore.query(b_id, qv, 5, [uuid.UUID(p["id"])]) == []   # ...nor by naming A's policy id
    with SessionLocal() as db:
        assert retrieve(db, b_id, "waiting period pre-existing diseases", None) == []
    cid = client.post("/api/chat/conversations", json={}, headers=other_headers).json()["id"]
    reply = client.post(f"/api/chat/conversations/{cid}/messages", json={"question": "What is the waiting period for pre-existing diseases?"},
                        headers=other_headers).json()
    assert reply["citations"] == [] and fake_llm.calls == []
    # asking about A's policy id explicitly is also refused
    r = client.post(f"/api/chat/conversations/{cid}/messages", json={"question": "waiting period?", "policy_id": p["id"]}, headers=other_headers)
    assert "couldn't find that policy" in r.json()["content"]
