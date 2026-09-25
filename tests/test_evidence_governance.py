import base64

from conftest import create, update


def test_mapping_change_invalidates_test_and_release_evidence(client, records):
    test = records["INT-007"]
    execution = client.post(f"/api/test-cases/{test['id']}/execute", json={}).json()
    assert execution["status"] == "PASS"
    assert execution["contract_fingerprint"]
    analytics_url = f"/api/analytics?project_id={test['project_id']}"
    assert client.get(analytics_url).json()["passing_integration_tests"] == 1
    integration = client.get(f"/api/integrations/{test['integration_id']}").json()
    mapping = integration["mappings"][0]
    payload = {
        k: mapping[k]
        for k in ["source_field", "target_field", "datatype", "transformation", "required", "validation_rule"]
    }
    assert (
        client.patch(
            f"/api/mappings/{mapping['id']}", json={**payload, "transformation": "uppercase"}
        ).status_code
        == 200
    )
    row = client.get(f"/api/test-cases/{test['id']}").json()
    assert row["executions"][0]["current_contract"] is False
    workspace = client.get("/api/workspace").json()
    assert next(a for a in workspace["items"] if a["id"] == test["id"])["effective_test_status"] == "NOT_RUN"
    assert client.get(analytics_url).json()["passing_integration_tests"] == 0
    # Retesting the new contract restores current evidence.
    assert client.post(f"/api/test-cases/{test['id']}/execute", json={}).json()["status"] == "PASS"
    assert client.get(f"/api/test-cases/{test['id']}").json()["executions"][0]["current_contract"]
    assert client.get(analytics_url).json()["passing_integration_tests"] == 1


def test_payload_change_requires_fresh_execution(client, records):
    test = records["INT-007"]
    client.post(f"/api/test-cases/{test['id']}/execute", json={})
    update(
        client, test, payload={"case_id": "NEW-ID", "status": "ACCEPTED", "recipient": "owner@example.test"}
    )
    assert client.get(f"/api/test-cases/{test['id']}").json()["executions"][0]["current_contract"] is False


def test_evidence_attachment_round_trip_integrity_and_validation(client, records):
    execution = client.post(f"/api/test-cases/{records['INT-007']['id']}/execute", json={}).json()
    content = b"Fictional operator evidence: string case identifier verified."
    payload = {
        "filename": "verification.txt",
        "media_type": "text/plain",
        "content_base64": base64.b64encode(content).decode(),
    }
    response = client.post(f"/api/test-executions/{execution['id']}/attachments", json=payload)
    assert response.status_code == 201
    attachment = response.json()
    assert len(attachment["sha256"]) == 64
    assert client.get(f"/api/attachments?execution_id={execution['id']}").json()[0]["id"] == attachment["id"]
    download = client.get(f"/api/attachments/{attachment['id']}/download")
    assert download.content == content
    assert download.headers["content-disposition"].startswith("attachment;")
    assert download.headers["x-content-type-options"] == "nosniff"
    assert (
        client.post(
            f"/api/test-executions/{execution['id']}/attachments", json={**payload, "media_type": "image/png"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/test-executions/{execution['id']}/attachments", json={**payload, "media_type": "text/html"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/test-executions/{execution['id']}/attachments", json={**payload, "content_base64": "%%%"}
        ).status_code
        == 422
    )


def test_uat_attachment_links_to_persisted_acceptance_result(client, records):
    result = client.post(
        f"/api/uat-scenarios/{records['UAT-S001']['id']}/results",
        json={"status": "PASS", "evidence": "Fictional acceptance evidence from case operator"},
    ).json()
    payload = {
        "filename": "acceptance.txt",
        "media_type": "text/plain",
        "content_base64": base64.b64encode(b"Accepted by fictional operator").decode(),
    }
    assert client.post(f"/api/uat-results/{result['id']}/attachments", json=payload).status_code == 201
    assert len(client.get(f"/api/attachments?uat_result_id={result['id']}").json()) == 1


def test_demo_reset_preserves_other_projects_and_recreates_real_evidence(client, records):
    other = create(client, "projects", key="PRESERVE-ME", title="User-created project")
    assert client.post("/api/admin/reset-demo", json={"confirmation": "wrong"}).status_code == 422
    response = client.post("/api/admin/reset-demo", json={"confirmation": "RESET NORTHSTAR DEMO"})
    assert response.status_code == 200, response.text
    workspace = client.get("/api/workspace").json()
    lookup = {a["key"]: a for a in workspace["items"]}
    assert lookup["PRESERVE-ME"]["id"] == other["id"]
    assert lookup["REL-001"]["status"] == "COMPLETED"
    assert lookup["REL-002"]["readiness_status"] == "NOT READY"
    assert len(workspace["executions"]) >= 24
    assert sum(a["kind"] == "incidents" for a in workspace["items"]) >= 5
    assert any(a["action"] == "demo_reset" for a in client.get("/api/audit?limit=500").json())


def test_testers_cannot_change_system_state(client, records):
    session = client.post("/api/auth/demo", json={"role": "tester"}).json()
    client.headers["X-CSRF-Token"] = session["csrf_token"]
    assert (
        client.post(
            f"/api/systems/{records['SYS-001']['id']}/transition", json={"status": "RETIRED"}
        ).status_code
        == 403
    )
