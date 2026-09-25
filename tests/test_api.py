import pytest
from conftest import connect, create, move
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend import models as m


def test_seed_meets_domain_minimums(client):
    items = client.get("/api/workspace").json()["items"]
    assert sum(a["kind"] == "systems" for a in items) >= 6
    assert sum(a["kind"] == "integrations" for a in items) >= 6
    assert sum(a.get("type") == "BUSINESS" for a in items) >= 8
    assert sum(a.get("type") == "FUNCTIONAL" for a in items) >= 12
    assert sum(a.get("type") == "TECHNICAL" for a in items) >= 8
    for kind, count in [
        ("test-cases", 20),
        ("risks", 6),
        ("dependencies", 6),
        ("uat-scenarios", 5),
        ("changes", 3),
        ("releases", 2),
    ]:
        assert sum(a["kind"] == kind for a in items) >= count


@pytest.mark.parametrize("kind", list(m.MODELS))
def test_catalog_list_and_detail(client, kind):
    response = client.get(f"/api/{kind}")
    assert response.status_code == 200
    for item in response.json()["items"][:1]:
        detail = client.get(f"/api/{kind}/{item['id']}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["key"] == item["key"]


def test_crud_validation_and_optimistic_concurrency(client, records):
    payload = {
        "key": "REQ-NEW",
        "title": "New acceptance requirement",
        "acceptance_criteria": "A valid notification contains a case ID",
        "project_id": records["NS-CASE"]["id"],
    }
    item = create(client, "requirements", **payload)
    assert client.post("/api/requirements", json=payload).status_code == 409
    assert (
        client.patch(f"/api/requirements/{item['id']}", json={"title": "An updated requirement"}).status_code
        == 428
    )
    assert (
        client.patch(
            f"/api/requirements/{item['id']}",
            json={"title": "An updated requirement"},
            headers={"If-Match": "1"},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/requirements/{item['id']}", json={"title": "A stale overwrite"}, headers={"If-Match": "1"}
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/requirements/{item['id']}", json={"status": "COMPLETE"}, headers={"If-Match": "2"}
        ).status_code
        == 422
    )
    assert client.delete(f"/api/requirements/{item['id']}").status_code == 200
    assert client.get(f"/api/requirements/{item['id']}").status_code == 404


def test_cross_project_references_and_cycles_rejected(client, records):
    project = create(client, "projects", key="OTHER-PROJECT", title="Other project")
    assert (
        client.post(
            "/api/test-cases",
            json={
                "key": "BAD-REF",
                "title": "Invalid references",
                "project_id": project["id"],
                "test_plan_id": records["TP-001"]["id"],
                "requirement_id": records["TR-001"]["id"],
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/links",
            json={
                "source_id": records["TR-001"]["id"],
                "target_id": records["BR-001"]["id"],
                "relation": "DECOMPOSES",
            },
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/links",
            json={
                "source_id": records["BR-001"]["id"],
                "target_id": records["BR-001"]["id"],
                "relation": "RELATES",
            },
        ).status_code
        == 422
    )


def test_no_status_shortcuts_and_blank_release_not_ready(client, records):
    assert (
        client.post(
            f"/api/requirements/{records['BR-001']['id']}/transition", json={"status": "APPROVED"}
        ).status_code
        == 409
    )
    release = create(
        client,
        "releases",
        key="EMPTY-REL",
        title="Empty scope release",
        version="0.0.1",
        project_id=records["NS-CASE"]["id"],
    )
    move(client, release, "PLANNED")
    gates = client.get(f"/api/releases/{release['id']}/readiness").json()
    assert gates["status"] == "NOT READY"
    assert (
        client.post(f"/api/releases/{release['id']}/transition", json={"status": "READY"}).status_code == 409
    )


def test_traceability_uses_links_and_filters(client, records):
    pid = records["NS-CASE"]["id"]
    data = client.get(
        "/api/traceability",
        params={
            "project_id": pid,
            "requirement": "BR-001",
            "integration_id": records["NOTIFY-API-002"]["id"],
        },
    ).json()
    assert len(data["rows"]) == 1
    assert data["rows"][0]["test_count"] > 0
    assert (
        client.get("/api/traceability", params={"project_id": pid, "test_status": "PASS"}).json()["rows"]
        == []
    )
    impact = client.get(f"/api/impact/{records['NOTIFY-API-002']['id']}").json()
    assert impact["counts"]["requirements"] >= 1
    assert impact["counts"]["test-cases"] >= 1


def test_dashboard_metrics_change_after_actual_execution(client, records):
    pid = records["NS-CASE"]["id"]
    before = client.get("/api/analytics", params={"project_id": pid}).json()
    execution = client.post(f"/api/test-cases/{records['INT-007']['id']}/execute", json={}).json()
    assert execution["status"] == "PASS"
    after = client.get("/api/analytics", params={"project_id": pid}).json()
    assert after["test_results"]["PASS"] == before["test_results"]["PASS"] + 1
    assert after["test_results"]["NOT_RUN"] == before["test_results"]["NOT_RUN"] - 1


def test_uat_requires_evidence_and_records_explicit_override(client, records):
    uat = records["UAT-001"]
    data = {
        "stakeholder_id": records["STK-001"]["id"],
        "decision": "APPROVED",
        "comments": "Acceptance reviewed by fictional stakeholder",
    }
    assert client.post(f"/api/uat/{uat['id']}/approve", json=data).status_code == 409
    assert (
        client.post(
            f"/api/uat-scenarios/{records['UAT-S001']['id']}/results", json={"status": "PASS", "evidence": ""}
        ).status_code
        == 422
    )
    response = client.post(
        f"/api/uat/{uat['id']}/approve",
        json={
            **data,
            "override_reason": "Fictional risk acceptance: remaining criteria are explicitly waived for this exercise.",
        },
    )
    assert response.status_code == 201
    assert response.json()["override_reason"]


def test_change_analysis_stales_after_relationship_change(client, records):
    change = records["CHG-001"]
    move(client, change, "SUBMITTED")
    move(client, change, "ANALYSIS")
    assert client.post(f"/api/changes/{change['id']}/analyze").status_code == 200
    connect(client, change, records["NFR-001"])
    assert (
        client.post(
            f"/api/changes/{change['id']}/transition", json={"status": "PENDING_APPROVAL"}
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "document_type",
    [
        "Business Requirements Document",
        "Functional Requirements Document",
        "Integration Specification",
        "Test Plan",
        "UAT Plan",
        "Release Notes",
        "Training Guide",
        "Project Status Report",
    ],
)
def test_reports_are_versioned_real_data_snapshots(client, records, document_type):
    response = client.post(
        "/api/reports", json={"project_id": records["NS-CASE"]["id"], "document_type": document_type}
    )
    assert response.status_code == 201
    doc = response.json()
    assert "Northstar" in doc["content"] and "NS-CASE" in doc["content"]
    export = client.get(f"/api/documents/{doc['id']}/export")
    assert export.text == doc["content"]
    second = client.post(
        "/api/reports", json={"project_id": records["NS-CASE"]["id"], "document_type": document_type}
    ).json()
    assert second["version"] == doc["version"] + 1


def test_database_foreign_keys_and_risk_constraints(database):
    with database() as db:
        db.add(m.ArtifactLink(source_id=999999, target_id=999998, relation="AFFECTS"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        risk = db.scalar(select(m.Risk))
        risk.probability = 9
        with pytest.raises(IntegrityError):
            db.commit()


def test_search_treats_sql_and_wildcards_as_text(client):
    assert client.get("/api/search", params={"q": "%' OR 1=1 --"}).json() == []
    assert client.get("/api/search", params={"q": "legacy"}).json()
