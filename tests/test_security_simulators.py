import pytest

from backend.main import app
from backend.simulator import SOAP, XSI


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("success", 201),
        ("bad_request", 400),
        ("unauthorized", 401),
        ("not_found", 404),
        ("conflict", 409),
        ("server_error", 500),
        ("timeout", 504),
    ],
)
def test_rest_controlled_responses(client, scenario, expected):
    response = client.post(
        "/simulator/cases", params={"scenario": scenario}, json={"case_id": "CASE-42", "status": "OPEN"}
    )
    assert response.status_code == expected


def test_case_idempotency_retrieval_and_conflict(client):
    payload = {"case_id": "CASE-42", "status": "OPEN"}
    assert client.post("/simulator/cases", json=payload).status_code == 201
    assert client.post("/simulator/cases", json=payload).json()["idempotent"]
    assert client.get("/simulator/cases/CASE-42").json()["status"] == "OPEN"
    assert client.post("/simulator/cases", json={**payload, "status": "CLOSED"}).status_code == 409
    assert client.get("/simulator/cases/MISSING").status_code == 404


def test_async_notification_accepted(client):
    response = client.post(
        "/simulator/notifications?asynchronous=true",
        json={"case_id": "42", "status": "OPEN", "recipient": "owner@example.test"},
    )
    assert response.status_code == 202 and response.json()["status"] == "QUEUED"


@pytest.mark.parametrize("datatype,expected", [("xsd:string", 200), ("xsd:int", 500)])
def test_soap_contract_and_fault(client, datatype, expected):
    xml = f'<s:Envelope xmlns:s="{SOAP}" xmlns:xsi="{XSI}"><s:Body><CreateCase><case_id xsi:type="{datatype}">42</case_id></CreateCase></s:Body></s:Envelope>'
    response = client.post("/simulator/soap", content=xml, headers={"Content-Type": "text/xml"})
    assert response.status_code == expected
    assert "Envelope" in response.text
    assert ("Fault" in response.text) == (expected == 500)


@pytest.mark.parametrize(
    "xml", ['<!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]><a>&x;</a>', "<broken", "<CreateCase/>"]
)
def test_unsafe_or_malformed_xml_is_rejected(client, xml):
    response = client.post("/simulator/soap", content=xml)
    assert response.status_code == 500
    assert "root:" not in response.text


def test_local_runner_timeout_and_soap_failure_evidence(client, records):
    for key, code in [("INT-002", 500), ("INT-005", 504)]:
        execution = client.post(f"/api/test-cases/{records[key]['id']}/execute", json={}).json()
        assert execution["status"] == "FAIL"
        assert execution["response_status"] == code
        assert execution["request_body"] and execution["response_body"]


def test_auth_csrf_roles_and_session_revocation(client, records):
    client.headers.pop("X-CSRF-Token")
    assert client.post(f"/api/test-cases/{records['INT-001']['id']}/execute", json={}).status_code == 403
    result = client.post("/api/auth/demo", json={"role": "viewer"}).json()
    client.headers["X-CSRF-Token"] = result["csrf_token"]
    assert client.post(f"/api/test-cases/{records['INT-001']['id']}/execute", json={}).status_code == 403
    assert client.get("/api/workspace").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/workspace").status_code == 401


def test_analyst_cannot_approve_change(client, records):
    result = client.post("/api/auth/demo", json={"role": "analyst"}).json()
    client.headers["X-CSRF-Token"] = result["csrf_token"]
    assert (
        client.post(
            f"/api/uat/{records['UAT-001']['id']}/approve",
            json={
                "stakeholder_id": records["STK-001"]["id"],
                "decision": "APPROVED",
                "comments": "This should be forbidden",
            },
        ).status_code
        == 403
    )


def test_origin_request_size_headers_and_no_arbitrary_endpoint(client, records):
    assert client.post("/api/auth/logout", headers={"Origin": "https://untrusted.example"}).status_code == 403
    assert client.post("/simulator/soap", content="x" * 262145).status_code == 413
    assert client.get("/api/health").headers["X-Content-Type-Options"] == "nosniff"
    assert (
        client.post(
            "/api/integrations",
            json={
                "key": "UNSAFE-API",
                "title": "Remote execution prohibited",
                "project_id": records["NS-CASE"]["id"],
                "source_system_id": records["SYS-001"]["id"],
                "target_system_id": records["SYS-002"]["id"],
                "endpoint": "https://example.com",
            },
        ).status_code
        == 422
    )


def test_openapi_has_typed_domain_schemas():
    schema = app.openapi()
    assert "RequirementInput" in schema["components"]["schemas"]
    assert "/api/test-cases/{entity_id}/execute" in schema["paths"]
