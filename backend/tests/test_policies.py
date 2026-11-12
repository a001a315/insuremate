from tests.conftest import new_policy


def test_policy_crud_and_masking(client, auth_headers):
    p = new_policy(client, auth_headers, details={"room_rent_limit": {"value": "1% per day"}},
                   members=[{"name": "Asha Demo"}])
    assert p["sum_insured"] == 1000000 and p["details"]["room_rent_limit"]["source"] == "manual"
    lst = client.get("/api/policies", headers=auth_headers).json()
    assert lst[0]["masked_policy_number"].endswith("4567") and "POL-1" not in lst[0]["masked_policy_number"]
    assert "policy_number" not in lst[0]
    got = client.get(f"/api/policies/{p['id']}", headers=auth_headers).json()
    assert got["policy_number"] == "POL-1234567" and len(got["members"]) == 1


def test_partial_update_keeps_other_fields_and_source(client, auth_headers):
    p = new_policy(client, auth_headers, details={"exclusions": {"value": "cosmetic", "source": "extracted"}})
    r = client.patch(f"/api/policies/{p['id']}", json={"premium_amount": 25000,
                     "details": {"copay": {"value": "10%"}}}, headers=auth_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["premium_amount"] == 25000 and d["name"] == "Family Health Shield"
    assert d["details"]["exclusions"]["source"] == "extracted"   # extracted vs manual stays distinguishable
    assert d["details"]["copay"]["source"] == "manual"


def test_validation(client, auth_headers):
    r = client.post("/api/policies", json={"name": "", "insurer": "x", "policy_number": "1", "policyholder_name": "a",
                                           "sum_insured": -5}, headers=auth_headers)
    assert r.status_code == 422
    r = client.post("/api/policies", json={"name": "n", "insurer": "x", "policy_number": "1", "policyholder_name": "a",
                                           "sum_insured": 1, "details": {"bogus": {"value": "x"}}}, headers=auth_headers)
    assert r.status_code == 422


def test_archive_hides_from_default_list_and_delete(client, auth_headers):
    p = new_policy(client, auth_headers)
    assert client.post(f"/api/policies/{p['id']}/archive", headers=auth_headers).json()["status"] == "archived"
    assert client.get("/api/policies", headers=auth_headers).json() == []
    assert len(client.get("/api/policies?include_archived=true", headers=auth_headers).json()) == 1
    assert client.delete(f"/api/policies/{p['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/policies/{p['id']}", headers=auth_headers).status_code == 404


def test_requires_auth(client):
    assert client.get("/api/policies").status_code == 401


def test_deleting_policy_removes_its_claims(client, auth_headers):
    p = new_policy(client, auth_headers)
    client.post("/api/claims", json={"policy_id": p["id"], "patient_id": p["patient_id"]}, headers=auth_headers)
    client.delete(f"/api/policies/{p['id']}", headers=auth_headers)
    assert client.get("/api/claims", headers=auth_headers).json() == []
