"""Deterministic fictional artifacts; execution evidence is created through real simulator requests."""

from datetime import date

from sqlalchemy import delete, select

from backend import models as m
from backend.auth import password_hash
from backend.config import settings
from backend.db import SessionLocal
from backend.services import audit

PROJECT_KEY = "NS-CASE"


def ensure_organization(db):
    organization = db.scalar(
        select(m.Organization).where(m.Organization.name == "Northstar Enterprise Services")
    )
    if not organization:
        organization = m.Organization(
            name="Northstar Enterprise Services",
            description="A fictional enterprise used for an integration analysis portfolio.",
        )
        db.add(organization)
        db.flush()
    return organization


def seed(db):
    if db.scalar(select(m.Project).where(m.Project.key == PROJECT_KEY)):
        return False
    organization = ensure_organization(db)
    project = m.Project(
        key=PROJECT_KEY,
        title="Case Intake & Notification Modernization",
        organization_id=organization.id,
        description="Replace manual re-entry with validated case intake, legacy record creation and timely status notifications.",
        status="ACTIVE",
        owner="Jordan Lee",
        start_date=date(2026, 8, 3),
        target_date=date(2026, 10, 16),
        priority="HIGH",
    )
    db.add(project)
    db.flush()

    def add(cls, key, title, **kwargs):
        obj = cls(
            key=key, title=title, project_id=project.id, owner=kwargs.pop("owner", "Jordan Lee"), **kwargs
        )
        db.add(obj)
        db.flush()
        return obj

    def link(source, target, relation="AFFECTS"):
        db.add(m.ArtifactLink(source_id=source.id, target_id=target.id, relation=relation))

    stakeholders = [
        add(
            m.Stakeholder,
            f"STK-{i:03}",
            name,
            status="APPROVED",
            role=role,
            department=department,
            contact=name.lower().replace(" ", ".") + "@northstar.example.test",
        )
        for i, (name, role, department) in enumerate(
            [
                ("Morgan Ellis", "Business sponsor", "Operations"),
                ("Jordan Lee", "Business systems analyst", "Technology"),
                ("Avery Chen", "Integration engineer", "Engineering"),
                ("Riley Brooks", "UAT lead", "Case Services"),
            ],
            1,
        )
    ]
    process = add(
        m.BusinessProcess,
        "PROC-001",
        "From intake to notification",
        status="APPROVED",
        current_state="Operators re-enter case data in three systems and email status changes manually.",
        future_state="Validate once, create a legacy record, store documents, and notify the case owner with an auditable correlation ID.",
        steps=[
            "Submit case",
            "Validate fields",
            "Create legacy record",
            "Store documents",
            "Send notification",
            "Update reporting",
            "Complete",
        ],
    )
    names = [
        ("Case Intake System", "React / Python", "Internal application"),
        ("Legacy Records System", "SOAP 1.1 / XML", "Legacy platform"),
        ("Document Management", "REST / object storage", "Content service"),
        ("Notification Service", "REST / event queue", "Messaging service"),
        ("Identity & Access", "OAuth2 / OIDC", "Security service"),
        ("Reporting Warehouse", "PostgreSQL / batch", "Analytics platform"),
        ("External Partner Gateway", "REST / JSON", "Partner boundary"),
    ]
    systems = [
        add(
            m.System,
            f"SYS-{i:03}",
            name,
            status="ACTIVE",
            technology=tech,
            system_type=typ,
            description=f"Fictional {name.lower()} in the Northstar case workflow.",
            owner="Avery Chen",
        )
        for i, (name, tech, typ) in enumerate(names, 1)
    ]
    business_titles = [
        "Notify users when a case changes status",
        "Create a single validated case record",
        "Keep documents attached to the correct case",
        "Authorize access by business role",
        "Provide an auditable intake history",
        "Publish operational reporting",
        "Exchange cases with approved partners",
        "Preserve legacy record compatibility",
    ]
    business = [
        add(
            m.Requirement,
            f"BR-{i:03}",
            title,
            type="BUSINESS",
            status="IMPLEMENTING" if i < 3 else "APPROVED",
            description=f"Business need: {title.lower()} across the case-intake lifecycle.",
            acceptance_criteria=f"Given an authorized case operator, when the workflow completes, then {title.lower()} with a stored correlation identifier.",
            source="Fictional operations discovery workshop · 2026-08-05",
        )
        for i, title in enumerate(business_titles, 1)
    ]
    functional_titles = [
        "Dispatch a notification after a status transition",
        "Validate mandatory intake fields",
        "Attach uploaded documents by case ID",
        "Check user role before intake submission",
        "Record every case status transition",
        "Send accepted cases to the reporting queue",
        "Validate inbound partner payloads",
        "Create records using the legacy SOAP action",
        "Prevent duplicate notification delivery",
        "Return actionable validation errors",
        "Preserve document metadata",
        "Display accessible status feedback",
    ]
    functional = [
        add(
            m.Requirement,
            f"FR-{i:03}",
            title,
            type="FUNCTIONAL",
            status="IMPLEMENTING" if i < 3 else "APPROVED",
            acceptance_criteria=f"Given valid input, {title.lower()}; reject malformed input and retain an audit record.",
        )
        for i, title in enumerate(functional_titles, 1)
    ]
    technical_titles = [
        "Map notification case_id and recipient fields",
        "Serialize legacy case_id as xsd:string",
        "Validate document reference schema",
        "Reject expired access tokens",
        "Propagate the correlation identifier",
        "Queue warehouse events asynchronously",
        "Handle downstream partner errors",
        "Preserve the legacy response contract",
    ]
    technical = [
        add(
            m.Requirement,
            f"TR-{i:03}",
            title,
            type="TECHNICAL",
            status="COMPLETE" if i == 8 else "IMPLEMENTING",
            acceptance_criteria=f"The local contract test proves: {title.lower()}. Invalid payloads produce a controlled error.",
        )
        for i, title in enumerate(technical_titles, 1)
    ]
    for i, requirement in enumerate(functional):
        link(business[i % 8], requirement, "DECOMPOSES")
    for i, requirement in enumerate(technical):
        link(functional[i], requirement, "DECOMPOSES")
    for i, title in enumerate(
        [
            "Respond within the agreed simulator deadline",
            "Expose keyboard-accessible workflows",
            "Prevent cross-project traceability links",
            "Retain immutable execution evidence",
        ],
        1,
    ):
        req = add(
            m.Requirement,
            f"NFR-{i:03}",
            title,
            type="NON_FUNCTIONAL",
            status="IN_REVIEW",
            acceptance_criteria=f"Automated verification demonstrates: {title.lower()}.",
        )
        link(req, systems[0])
    link(process, business[0], "DOCUMENTS")
    integration_specs = [
        (
            "NOTIFY-API-002",
            "Case status notification",
            0,
            3,
            "REST",
            "/simulator/notifications",
            "POST",
            "JSON",
            "SYNCHRONOUS",
        ),
        (
            "CASE-API-001",
            "Legacy case creation",
            0,
            1,
            "SOAP",
            "/simulator/soap",
            "CreateCase",
            "XML",
            "SYNCHRONOUS",
        ),
        (
            "DOC-API-003",
            "Document association",
            0,
            2,
            "REST",
            "/simulator/cases",
            "POST",
            "JSON",
            "SYNCHRONOUS",
        ),
        (
            "AUTH-API-004",
            "Authorized intake submission",
            4,
            0,
            "REST",
            "/simulator/cases",
            "POST",
            "JSON",
            "SYNCHRONOUS",
        ),
        (
            "REPORT-API-005",
            "Operational reporting event",
            0,
            5,
            "REST",
            "/simulator/notifications",
            "POST",
            "JSON",
            "ASYNCHRONOUS",
        ),
        (
            "PARTNER-API-006",
            "Partner case exchange",
            6,
            0,
            "REST",
            "/simulator/cases",
            "POST",
            "JSON",
            "SYNCHRONOUS",
        ),
        (
            "LEGACY-API-007",
            "Legacy contract baseline",
            0,
            1,
            "SOAP",
            "/simulator/soap",
            "CreateCase",
            "XML",
            "SYNCHRONOUS",
        ),
    ]
    integrations = []
    for i, (key, title, src, tgt, protocol, endpoint, method, fmt, mode) in enumerate(integration_specs):
        integration = add(
            m.Integration,
            key,
            title,
            status="DEGRADED" if i < 2 else "ACTIVE",
            source_system_id=systems[src].id,
            target_system_id=systems[tgt].id,
            protocol=protocol,
            endpoint=endpoint,
            method=method,
            data_format=fmt,
            mode=mode,
            authentication_type="Mutual TLS (design only; locally simulated)"
            if protocol == "SOAP"
            else "OAuth2 (locally simulated)",
            description="Controlled local protocol demonstration; no external system is contacted.",
            owner="Avery Chen",
            request_format='<CreateCase><case_id xsi:type="xsd:string">NS-1001</case_id></CreateCase>'
            if protocol == "SOAP"
            else '{"case_id":"NS-1001","status":"ACCEPTED","recipient":"owner@example.test"}',
            response_format="<CreateCaseResponse><case_id>NS-1001</case_id><status>CREATED</status></CreateCaseResponse>"
            if protocol == "SOAP"
            else '{"case_id":"NS-1001","status":"DELIVERED"}',
        )
        integrations.append(integration)
        link(technical[7 if i == 6 else i], integration)
        for field in ["case_id", "status", "recipient"]:
            db.add(
                m.FieldMapping(
                    integration_id=integration.id,
                    source_field=field,
                    target_field="case_status" if i == 5 and field == "status" else field,
                    transformation="identity"
                    if i == 1
                    else ("to_string" if field == "case_id" else "identity"),
                    datatype="string",
                    required=True,
                    validation_rule="non_empty",
                )
            )
    plan = add(
        m.TestPlan,
        "TP-001",
        "Case modernization · integration qualification",
        status="APPROVED",
        scope="REST, SOAP, negative responses, identity boundaries, mapping and asynchronous acceptance.",
        objectives="Prove stored acceptance criteria with reproducible local exchanges.",
    )
    tests = []
    titles = [
        "Notification token is rejected",
        "Legacy integer identifier fails schema validation",
        "Downstream document service returns an error",
        "Intake authentication is rejected",
        "Reporting service exceeds the deadline",
        "Partner mapping omits required status",
    ]
    for i in range(24):
        index = i % 7
        integration = integrations[index]
        requirement = technical[7 if index == 6 else index]
        scenario = (
            ["unauthorized", "success", "server_error", "unauthorized", "timeout", "success"][i]
            if i < 6
            else "success"
        )
        payload = {
            "case_id": 1042 if index == 1 else f"NS-{1000 + i}",
            "status": "ACCEPTED",
            "recipient": "case.owner@example.test",
        }
        if i == 5:
            payload["recipient"] = "invalid-address"
        test = add(
            m.TestCase,
            f"INT-{i + 1:03}",
            titles[i] if i < 6 else f"{integration.title}: contract verification {i + 1:02}",
            status="APPROVED",
            test_plan_id=plan.id,
            requirement_id=requirement.id,
            integration_id=integration.id,
            priority="CRITICAL" if i in {0, 1} else "HIGH",
            payload=payload,
            scenario=scenario,
            expected_status=200
            if integration.protocol == "SOAP"
            else (202 if integration.mode == "ASYNCHRONOUS" else 201),
            expected_result="Response status matches the contract; case_id is a string and status is present.",
            steps="1. Apply stored field mappings.\n2. Send the request to the local integration simulator.\n3. Inspect status and response schema.\n4. Retain request and response evidence.",
        )
        tests.append(test)
    risks = []
    for i, (title, mitigation) in enumerate(
        [
            ("Legacy identifier contract mismatch", "Validate xsd:string conversion before qualification."),
            (
                "Notification delivery interruption",
                "Use controlled retry and idempotency tests before release.",
            ),
            ("Identity token expiry during intake", "Test invalid and expired authentication responses."),
            ("Document metadata inconsistency", "Compare case identifiers at the mapping boundary."),
            ("Reporting queue delay", "Verify accepted status and capture timeout evidence."),
            ("Partner schema drift", "Version the inbound contract and review field mappings."),
        ],
        1,
    ):
        risk = add(
            m.Risk,
            f"RSK-{i:03}",
            title,
            status="OPEN",
            probability=4 if i < 3 else 3,
            impact=5 if i < 3 else 3,
            mitigation=mitigation,
        )
        link(risk, integrations[(i - 1) % 6])
        risks.append(risk)
    for i, integration in enumerate(integrations[:6], 1):
        add(
            m.Dependency,
            f"DEP-{i:03}",
            f"{integration.title} contract approval",
            status="BLOCKED" if i == 2 else "SATISFIED",
            source_id=integration.id,
            target_id=systems[1 if i == 2 else 0].id,
            impact="Qualification cannot complete until the service contract and mapping are agreed.",
        )
    current_uat = add(
        m.UATSession,
        "UAT-001",
        "Case operations acceptance",
        status="IN_PROGRESS",
        coordinator="Riley Brooks",
        start_date=date(2026, 9, 14),
        end_date=date(2026, 9, 25),
    )
    for i, req in enumerate(technical[:5], 1):
        add(
            m.UATScenario,
            f"UAT-S{i:03}",
            f"Operator verifies {req.title.lower()}",
            status="READY",
            session_id=current_uat.id,
            requirement_id=req.id,
            steps="Submit a fictional case, inspect the status and compare the result with the acceptance criteria.",
            expected_result=req.acceptance_criteria,
        )
    baseline_uat = add(
        m.UATSession,
        "UAT-002",
        "Legacy baseline acceptance",
        status="IN_PROGRESS",
        coordinator="Riley Brooks",
    )
    add(
        m.UATScenario,
        "UAT-S006",
        "Legacy baseline preserves a string identifier",
        status="READY",
        session_id=baseline_uat.id,
        requirement_id=technical[7].id,
        steps="Submit a string identifier and inspect the legacy response.",
        expected_result="The response preserves the string identifier.",
    )
    changes = []
    for i, (title, integration) in enumerate(
        [
            ("Correct notification field contract", integrations[0]),
            ("Serialize legacy identifiers as strings", integrations[1]),
            ("Harden partner response handling", integrations[5]),
        ],
        1,
    ):
        change = add(
            m.ChangeRequest,
            f"CHG-{i:03}",
            title,
            status="DRAFT",
            reason="Resolve a demonstrated integration contract failure before deployment.",
            impact="Review stored relationships and execute impacted tests.",
            risk="Regression at the consumer boundary",
        )
        link(change, integration)
        changes.append(change)
    historical = add(
        m.Release,
        "REL-001",
        "Legacy compatibility baseline",
        version="1.0.0",
        status="PLANNED",
        target_date=date(2026, 8, 28),
        deployment_notes="Deploy the versioned legacy contract fixture; run qualification and record evidence.",
        rollback_plan="Restore the previous contract version and replay the saved qualification payloads.",
    )
    link(historical, technical[7], "CONTAINS")
    current = add(
        m.Release,
        "REL-002",
        "Case modernization pilot",
        version="1.1.0",
        status="PLANNED",
        target_date=date(2026, 10, 16),
        deployment_notes="Deploy approved mappings, validate local contracts, complete UAT and review the readiness gates.",
        rollback_plan="Restore the last approved mapping revision; pause notification delivery and reconcile affected case identifiers.",
    )
    for req in business[:2]:
        link(current, req, "CONTAINS")
    for change in changes[:2]:
        link(current, change, "CONTAINS")
    training = add(
        m.TrainingMaterial,
        "TRN-001",
        "Case operator quick start",
        status="APPROVED",
        audience="Case operations and service desk",
        content="# Case operator quick start\n\n1. Submit a fictional case with all mandatory fields.\n2. Check validation messages before resubmitting.\n3. Confirm the legacy case identifier.\n4. Review notification status.\n5. Record failures with the correlation ID and captured evidence.\n\nUse only fictional .test recipients in the simulator.",
    )
    link(training, technical[0], "DOCUMENTS")
    for stakeholder in stakeholders:
        link(stakeholder, business[0], "RELATES")
    audit(db, "Demo seed", "demo_project_created", project)
    db.commit()
    return True


def reset_northstar(db):
    project = db.scalar(select(m.Project).where(m.Project.key == PROJECT_KEY))
    if not project:
        return
    ids = list(db.scalars(select(m.Artifact.id).where(m.Artifact.project_id == project.id)))
    db.execute(delete(m.TestExecution).where(m.TestExecution.test_case_id.in_(ids)))
    db.execute(delete(m.UATApproval).where(m.UATApproval.session_id.in_(ids)))
    db.execute(delete(m.UATResult).where(m.UATResult.scenario_id.in_(ids)))
    db.execute(
        delete(m.ArtifactLink).where(m.ArtifactLink.source_id.in_(ids) | m.ArtifactLink.target_id.in_(ids))
    )
    for kind in [
        "uat-scenarios",
        "test-cases",
        "dependencies",
        "risks",
        "integrations",
        "requirements",
        "test-plans",
        "uat",
        "systems",
        "incidents",
        "changes",
        "releases",
        "training",
        "documents",
        "processes",
        "stakeholders",
    ]:
        for obj in db.scalars(select(m.MODELS[kind]).where(m.MODELS[kind].project_id == project.id)):
            db.delete(obj)
        db.flush()
    db.delete(project)
    db.flush()


def populate_evidence(client):
    login = client.post("/api/auth/demo", json={"role": "admin"})
    if login.status_code != 200:
        raise RuntimeError("Demo evidence requires enabled demo mode")
    headers = {"X-CSRF-Token": login.json()["csrf_token"]}
    workspace = client.get("/api/workspace").json()["items"]
    lookup = {a["key"]: a for a in workspace}

    def post(url, payload=None):
        response = client.post(url, json=payload or {}, headers=headers)
        if response.status_code >= 400:
            raise RuntimeError(f"Evidence initialization failed: {url}: {response.text}")
        return response.json()

    for test in [
        a for a in workspace if a["kind"] == "test-cases" and a["project_id"] == lookup[PROJECT_KEY]["id"]
    ]:
        execution = post(f"/api/test-cases/{test['id']}/execute")
        if execution["status"] == "FAIL":
            post(f"/api/test-executions/{execution['id']}/defect")
    baseline = lookup["UAT-S006"]
    post(
        f"/api/uat-scenarios/{baseline['id']}/results",
        {
            "status": "PASS",
            "evidence": "Fictional seeded acceptance record: local baseline contract executions preserve a string case identifier.",
            "comments": "Illustrative portfolio acceptance; not an actual enterprise stakeholder decision.",
        },
    )
    post(
        f"/api/uat/{lookup['UAT-002']['id']}/approve",
        {
            "stakeholder_id": lookup["STK-001"]["id"],
            "decision": "APPROVED",
            "comments": "Fictional seeded stakeholder sign-off for the verified local legacy baseline.",
        },
    )
    for status in ["READY", "DEPLOYED", "COMPLETED"]:
        post(
            f"/api/releases/{lookup['REL-001']['id']}/transition",
            {
                "status": status,
                "comment": "Fictional baseline release, verified against local simulator evidence.",
            },
        )
    for document_type in [
        "Business Requirements Document",
        "Integration Specification",
        "Project Status Report",
    ]:
        post("/api/reports", {"project_id": lookup[PROJECT_KEY]["id"], "document_type": document_type})
    post("/api/auth/logout")


def main():
    with SessionLocal() as db:
        ensure_organization(db)
        db.commit()
        if settings().admin_email and settings().admin_password:
            if len(settings().admin_password) < 12:
                raise RuntimeError("Administrator password must contain at least 12 characters")
            if not db.scalar(select(m.User).where(m.User.email == settings().admin_email.lower())):
                db.add(
                    m.User(
                        email=settings().admin_email.lower(),
                        name="Administrator",
                        role="admin",
                        password_hash=password_hash.hash(settings().admin_password),
                    )
                )
                db.commit()
        if not settings().demo_mode:
            print("Administrator initialized. Demo seeding disabled.")
            return
        created = seed(db)
    if created:
        from fastapi.testclient import TestClient

        from backend.main import app

        with TestClient(app) as client:
            populate_evidence(client)
        print("Northstar demo seeded; 24 real local protocol executions captured, baseline release verified.")
    else:
        print("Northstar demo already exists; no records changed.")


if __name__ == "__main__":
    main()
