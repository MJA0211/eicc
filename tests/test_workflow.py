from conftest import connect, create, move, update


def test_complete_business_need_to_release_workflow(client):
    project = create(
        client, "projects", key="DEMO-E2E", title="Notification lifecycle verification", organization_id=1
    )
    p = {"project_id": project["id"]}
    parent = None
    reqs = []
    for key, kind in [("E2E-BR", "BUSINESS"), ("E2E-FR", "FUNCTIONAL"), ("E2E-TR", "TECHNICAL")]:
        req = create(
            client,
            "requirements",
            key=key,
            title=f"{kind} notification acceptance",
            type=kind,
            acceptance_criteria="A case status change produces a notification preserving a string case ID.",
            **p,
        )
        if parent:
            connect(client, parent, req, "DECOMPOSES")
        reqs.append(req)
        parent = req
    source = create(client, "systems", key="E2E-SRC", title="Case intake", **p)
    target = create(client, "systems", key="E2E-TGT", title="Notification service", **p)
    integration = create(
        client,
        "integrations",
        key="E2E-API",
        title="Notify after status change",
        source_system_id=source["id"],
        target_system_id=target["id"],
        **p,
    )
    connect(client, reqs[-1], integration)
    mapping_payload = {
        "source_field": "case_id",
        "target_field": "case_id",
        "datatype": "string",
        "transformation": "identity",
        "required": True,
        "validation_rule": "non_empty",
    }
    mapping = client.post(f"/api/integrations/{integration['id']}/mappings", json=mapping_payload).json()
    for field in ["status", "recipient"]:
        assert (
            client.post(
                f"/api/integrations/{integration['id']}/mappings",
                json={"source_field": field, "target_field": field},
            ).status_code
            == 201
        )
    risk = create(
        client,
        "risks",
        key="E2E-RISK",
        title="Notification schema drift",
        mitigation="Validate the mapping with a contract test",
        probability=3,
        impact=3,
        **p,
    )
    connect(client, risk, integration)
    dep = create(
        client,
        "dependencies",
        key="E2E-DEP",
        title="Notification contract approved",
        source_id=integration["id"],
        target_id=target["id"],
        impact="Required before notification release",
        **p,
    )
    move(client, dep, "SATISFIED")
    plan = create(
        client,
        "test-plans",
        key="E2E-PLAN",
        title="Notification qualification",
        scope="Case identifier mapping and notification response",
        **p,
    )
    test = create(
        client,
        "test-cases",
        key="E2E-TEST",
        title="Preserve string identifier",
        test_plan_id=plan["id"],
        requirement_id=reqs[-1]["id"],
        integration_id=integration["id"],
        payload={"case_id": 42, "status": "ACCEPTED", "recipient": "owner@example.test"},
        priority="CRITICAL",
        **p,
    )
    failed = client.post(f"/api/test-cases/{test['id']}/execute", json={}).json()
    assert failed["status"] == "FAIL"
    assert failed["response_status"] == 422
    assert '"case_id": 42' in failed["request_body"]
    defect = client.post(f"/api/test-executions/{failed['id']}/defect").json()
    assert client.post(f"/api/test-executions/{failed['id']}/defect").json()["id"] == defect["id"]
    move(client, defect, "ASSIGNED")
    move(client, defect, "IN_PROGRESS")
    update(
        client,
        defect,
        root_cause="Integer source ID was forwarded without serialization",
        resolution="Map the identifier using to_string and verify a passing retest",
    )
    assert (
        client.post(f"/api/incidents/{defect['id']}/transition", json={"status": "RESOLVED"}).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/mappings/{mapping['id']}", json={**mapping_payload, "transformation": "to_string"}
        ).status_code
        == 200
    )
    retest = client.post(f"/api/test-cases/{test['id']}/execute", json={}).json()
    assert retest["status"] == "PASS"
    assert '"case_id": "42"' in retest["request_body"]
    move(client, defect, "RESOLVED")
    move(client, defect, "CLOSED")
    for req in reqs:
        for status in ["IN_REVIEW", "APPROVED", "IMPLEMENTING", "COMPLETE"]:
            move(client, req, status)
    stakeholder = create(client, "stakeholders", key="E2E-OWNER", title="Fictional acceptance owner", **p)
    uat = create(client, "uat", key="E2E-UAT", title="Notification business acceptance", **p)
    scenario = create(
        client,
        "uat-scenarios",
        key="E2E-SCENARIO",
        title="Case owner receives a status notification",
        session_id=uat["id"],
        requirement_id=reqs[-1]["id"],
        steps="Submit a case and inspect the notification response",
        expected_result="The notification contains the original case identifier",
        **p,
    )
    move(client, uat, "READY")
    move(client, uat, "IN_PROGRESS")
    approval = {
        "stakeholder_id": stakeholder["id"],
        "decision": "APPROVED",
        "comments": "Verified the business acceptance criteria against retained evidence",
    }
    assert client.post(f"/api/uat/{uat['id']}/approve", json=approval).status_code == 409
    assert (
        client.post(
            f"/api/uat-scenarios/{scenario['id']}/results",
            json={
                "status": "PASS",
                "evidence": f"Fictional automated demonstration: passing local execution {retest['id']} preserved string case ID 42.",
            },
        ).status_code
        == 201
    )
    move(client, uat, "PASSED")
    assert client.post(f"/api/uat/{uat['id']}/approve", json=approval).status_code == 201
    change = create(
        client,
        "changes",
        key="E2E-CHANGE",
        title="Approve identifier mapping correction",
        reason="Resolve the demonstrated schema validation failure",
        **p,
    )
    connect(client, change, reqs[-1])
    release = create(
        client,
        "releases",
        key="E2E-REL",
        title="Notification mapping release",
        version="1.0.0",
        rollback_plan="Restore the previous mapping revision and suspend notification delivery until reconciled.",
        deployment_notes="Apply the approved mapping revision, execute qualification and retain UAT sign-off.",
        **p,
    )
    connect(client, release, reqs[0], "CONTAINS")
    connect(client, release, change, "CONTAINS")
    assert client.get(f"/api/releases/{release['id']}/readiness").json()["status"] == "NOT READY"
    move(client, change, "SUBMITTED")
    move(client, change, "ANALYSIS")
    assert (
        client.post(
            f"/api/changes/{change['id']}/transition", json={"status": "PENDING_APPROVAL"}
        ).status_code
        == 409
    )
    assert client.post(f"/api/changes/{change['id']}/analyze").status_code == 200
    for status in ["PENDING_APPROVAL", "APPROVED", "IMPLEMENTING", "VALIDATION", "COMPLETED"]:
        move(client, change, status)
    gates = client.get(f"/api/releases/{release['id']}/readiness").json()
    assert gates["status"] == "READY", gates
    for status in ["PLANNED", "READY", "DEPLOYED", "COMPLETED"]:
        move(client, release, status)
    matrix = client.get("/api/traceability", params={"project_id": project["id"]}).json()
    assert matrix["metrics"]["passing"] == 3
    row = next(r for r in matrix["rows"] if r["key"] == "E2E-BR")
    assert {
        "systems",
        "integrations",
        "test-cases",
        "incidents",
        "uat",
        "releases",
        "changes",
        "risks",
        "dependencies",
    } <= {a["kind"] for a in row["related"]}
    document = client.post(
        "/api/reports", json={"project_id": project["id"], "document_type": "Release Notes"}
    ).json()
    exported = client.get(f"/api/documents/{document['id']}/export")
    assert "E2E-REL" in exported.text and "READY" in exported.text
    timeline = client.get(f"/api/incidents/{defect['id']}").json()["timeline"]
    assert len(timeline) >= 6
    update(
        client,
        reqs[-1],
        acceptance_criteria="Updated acceptance criterion requires renewed stakeholder review",
    )
    assert client.get(f"/api/uat/{uat['id']}").json()["acceptance"]["stale_approval"]
    assert client.get(f"/api/releases/{release['id']}/readiness").json()["status"] == "NOT READY"
