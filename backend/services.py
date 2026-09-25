from fastapi import HTTPException
from sqlalchemy import select

from backend import models as m
from backend.graph import (
    Graph,
    execution_status,
    fingerprint,
    latest_executions,
    release_readiness,
    serialize,
    uat_state,
)

TRANSITIONS = {
    "projects": {"DRAFT": ["ACTIVE"], "ACTIVE": ["ON_HOLD", "COMPLETED"], "ON_HOLD": ["ACTIVE"]},
    "requirements": {
        "DRAFT": ["IN_REVIEW"],
        "IN_REVIEW": ["APPROVED", "DRAFT"],
        "APPROVED": ["IMPLEMENTING"],
        "IMPLEMENTING": ["COMPLETE"],
        "COMPLETE": ["IMPLEMENTING"],
    },
    "incidents": {
        "NEW": ["ASSIGNED"],
        "ASSIGNED": ["IN_PROGRESS", "PENDING"],
        "IN_PROGRESS": ["PENDING", "RESOLVED"],
        "PENDING": ["IN_PROGRESS"],
        "RESOLVED": ["CLOSED", "IN_PROGRESS"],
        "CLOSED": ["IN_PROGRESS"],
    },
    "changes": {
        "DRAFT": ["SUBMITTED"],
        "SUBMITTED": ["ANALYSIS", "REJECTED"],
        "ANALYSIS": ["PENDING_APPROVAL"],
        "PENDING_APPROVAL": ["APPROVED", "REJECTED"],
        "APPROVED": ["IMPLEMENTING"],
        "REJECTED": ["DRAFT"],
        "IMPLEMENTING": ["VALIDATION"],
        "VALIDATION": ["COMPLETED", "IMPLEMENTING"],
    },
    "releases": {
        "DRAFT": ["PLANNED"],
        "PLANNED": ["READY"],
        "READY": ["DEPLOYED", "PLANNED"],
        "DEPLOYED": ["COMPLETED", "ROLLED_BACK"],
    },
    "uat": {
        "NOT_READY": ["READY"],
        "READY": ["IN_PROGRESS"],
        "IN_PROGRESS": ["PASSED", "FAILED"],
        "FAILED": ["IN_PROGRESS"],
        "PASSED": ["IN_PROGRESS"],
        "APPROVED": ["IN_PROGRESS"],
        "REJECTED": ["IN_PROGRESS"],
    },
    "uat-scenarios": {"DRAFT": ["READY"], "READY": ["DRAFT"]},
    "risks": {
        "OPEN": ["MITIGATED", "ACCEPTED"],
        "MITIGATED": ["CLOSED", "OPEN"],
        "ACCEPTED": ["CLOSED", "OPEN"],
    },
    "dependencies": {
        "OPEN": ["BLOCKED", "SATISFIED"],
        "BLOCKED": ["SATISFIED", "OPEN"],
        "SATISFIED": ["BLOCKED"],
    },
    "integrations": {
        "DRAFT": ["ACTIVE"],
        "ACTIVE": ["DEGRADED", "RETIRED"],
        "DEGRADED": ["ACTIVE", "RETIRED"],
    },
    "systems": {"DRAFT": ["ACTIVE"], "ACTIVE": ["MAINTENANCE", "RETIRED"], "MAINTENANCE": ["ACTIVE"]},
}
DEFAULT_TRANSITIONS = {"DRAFT": ["IN_REVIEW"], "IN_REVIEW": ["APPROVED", "DRAFT"], "APPROVED": ["ARCHIVED"]}
INITIAL = {"incidents": "NEW", "uat": "NOT_READY", "risks": "OPEN", "dependencies": "OPEN"}


def audit(db, actor, action, obj, before=None, after=None):
    db.add(
        m.AuditLog(
            actor=actor,
            action=action,
            entity=getattr(obj, "kind", obj.__tablename__),
            entity_id=obj.id,
            previous_value=before,
            new_value=after if after is not None else serialize(obj),
        )
    )


def get_artifact(db, entity_id, kind=None):
    obj = db.get(m.Artifact, entity_id)
    if not obj or (kind and obj.kind != kind):
        raise HTTPException(404, "Record not found")
    return obj


def validate_references(db, kind, data):
    project_id = data.get("project_id")
    if kind == "projects":
        if project_id:
            raise HTTPException(422, "A project cannot be nested in another project")
        if not db.get(m.Organization, data["organization_id"]):
            raise HTTPException(422, "Organization does not exist")
    else:
        if not project_id:
            raise HTTPException(422, "Project is required")
        get_artifact(db, project_id, "projects")
    fields = {
        "source_system_id": "systems",
        "target_system_id": "systems",
        "requirement_id": "requirements",
        "integration_id": "integrations",
        "test_plan_id": "test-plans",
        "session_id": "uat",
        "source_id": None,
        "target_id": None,
    }
    for field, target_kind in fields.items():
        if data.get(field) is not None:
            target = get_artifact(db, data[field], target_kind)
            if target.project_id != project_id:
                raise HTTPException(422, f"{field} must belong to the same project")
    if kind == "dependencies" and data["source_id"] == data["target_id"]:
        raise HTTPException(422, "A dependency cannot reference itself")


def validate_link(db, data):
    source = get_artifact(db, data.source_id)
    target = get_artifact(db, data.target_id)
    if source.id == target.id or source.project_id != target.project_id:
        raise HTTPException(422, "Links require different records in the same project")
    if data.relation == "DECOMPOSES":
        if source.kind != "requirements" or target.kind != "requirements":
            raise HTTPException(422, "Decomposition connects two requirements")
        graph = Graph(db, source.project_id)
        if source.id in graph.descendants({target.id}):
            raise HTTPException(409, "Requirement decomposition cannot contain a cycle")
        if any(t == target.id and r == "DECOMPOSES" for _, t, r in graph.edges):
            raise HTTPException(409, "A requirement already has a parent")
    elif data.relation == "CONTAINS":
        if source.kind != "releases" or target.kind not in {"requirements", "changes"}:
            raise HTTPException(422, "Release scope contains requirements and changes")
    elif data.relation == "VERIFIES" and (
        source.kind not in {"test-cases", "uat-scenarios"} or target.kind != "requirements"
    ):
        raise HTTPException(422, "Verification connects a test or UAT scenario to a requirement")
    return source, target


def impact_snapshot(db, change):
    graph = Graph(db, change.project_id)
    result = graph.impact(change.id)
    # Approval fields and change status do not stale their own impact analysis.
    data = {"items": [serialize(graph.nodes[i["id"]]) for i in result["items"]], "edges": result["edges"]}
    return result, fingerprint(data)


def transition(db, obj, status, actor, role, comment=""):
    allowed = TRANSITIONS.get(obj.kind, DEFAULT_TRANSITIONS).get(obj.status, [])
    if status not in allowed:
        raise HTTPException(
            409, f"Cannot transition {obj.status} to {status}; allowed: {', '.join(allowed) or 'none'}"
        )
    if (obj.kind in {"changes", "releases"} and status in {"APPROVED", "READY", "DEPLOYED", "COMPLETED"}) or (
        obj.kind == "requirements" and status == "APPROVED"
    ):
        if role not in {"manager", "admin"}:
            raise HTTPException(403, "A manager must authorize this transition")
    if obj.kind == "changes":
        if status in {"PENDING_APPROVAL", "APPROVED"}:
            impact, fp = impact_snapshot(db, obj)
            if not impact["items"] or not obj.analysis_fingerprint or obj.analysis_fingerprint != fp:
                raise HTTPException(409, "Record a current impact analysis before approval")
        if status == "APPROVED":
            obj.approved_by = actor
        if status == "COMPLETED":
            graph = Graph(db, obj.project_id)
            impacted = graph.impact(obj.id)["items"]
            tests = [i for i in impacted if i["kind"] == "test-cases"]
            latest = latest_executions(db)
            if not tests or any(
                execution_status(db, db.get(m.TestCase, t["id"]), latest.get(t["id"])) != "PASS"
                for t in tests
            ):
                raise HTTPException(409, "All impacted tests must have a passing latest execution")
    if obj.kind == "releases" and status in {"READY", "DEPLOYED", "COMPLETED"}:
        gates = release_readiness(db, obj)
        if gates["status"] != "READY":
            raise HTTPException(409, {"message": "Mandatory release criteria failed", "readiness": gates})
    if obj.kind == "incidents" and status == "RESOLVED":
        if not obj.root_cause.strip() or not obj.resolution.strip():
            raise HTTPException(409, "Root cause and resolution are required")
        executions = list(db.scalars(select(m.TestExecution).where(m.TestExecution.defect_id == obj.id)))
        latest = latest_executions(db)
        if any(
            e.test_case_id not in latest
            or latest[e.test_case_id].id <= e.id
            or execution_status(db, db.get(m.TestCase, e.test_case_id), latest.get(e.test_case_id)) != "PASS"
            for e in executions
            if e.status == "FAIL"
        ):
            raise HTTPException(409, "A passing retest after the linked failure is required")
        obj.resolved_at = m.now()
    if obj.kind == "uat":
        state = uat_state(db, obj.id)
        if status == "READY" and not state["scenarios"]:
            raise HTTPException(409, "Define UAT scenarios first")
        if status == "PASSED" and not state["ready"]:
            raise HTTPException(409, "Mandatory UAT scenarios need passing evidence")
    before = serialize(obj)
    obj.status = status
    db.flush()
    audit(db, actor, "status_changed", obj, before, {**serialize(obj), "comment": comment})
    return obj
