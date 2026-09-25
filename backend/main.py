import logging
import secrets
from collections import Counter, defaultdict, deque
from contextlib import asynccontextmanager
from time import monotonic

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from backend import models as m
from backend.auth import current_session, issue_session, password_hash, require_role, writer
from backend.config import settings
from backend.db import get_db
from backend.evidence import router as evidence_router
from backend.graph import (
    Graph,
    brief,
    execution_status,
    latest_executions,
    release_readiness,
    serialize,
    test_fingerprint,
    traceability,
    uat_state,
)
from backend.reports import generate_markdown
from backend.schemas import (
    SCHEMAS,
    ApprovalInput,
    DemoInput,
    ExecutionInput,
    LinkInput,
    LoginInput,
    MappingInput,
    ReportInput,
    ResetInput,
    ResultInput,
    TransitionInput,
)
from backend.services import (
    DEFAULT_TRANSITIONS,
    INITIAL,
    TRANSITIONS,
    audit,
    get_artifact,
    impact_snapshot,
    transition,
    validate_link,
    validate_references,
)
from backend.simulator import execute_local
from backend.simulator import router as simulator_router

logger = logging.getLogger("eicc")


@asynccontextmanager
async def lifespan(app):
    if not settings().demo_mode and not settings().secure_cookies:
        raise RuntimeError("Non-demo deployment requires EICC_SECURE_COOKIES=true and HTTPS")
    yield


app = FastAPI(
    title="EICC — Enterprise Integration Control Center",
    version="1.0.0",
    description="Fictional portfolio demonstration. Local simulators only. No government affiliation.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token", "If-Match"],
)
app.include_router(simulator_router)
app.include_router(evidence_router)
login_attempts = defaultdict(deque)


@app.middleware("http")
async def protections(request, call_next):
    if request.method in {"POST", "PATCH", "PUT"}:
        size = 0
        chunks = []
        async for chunk in request.stream():
            size += len(chunk)
            limit = 3 * 1024 * 1024 if request.url.path.endswith("/attachments") else 262144
            if size > limit:
                return JSONResponse({"detail": "Request body exceeds the allowed size"}, status_code=413)
            chunks.append(chunk)
        request._body = b"".join(chunks)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings().secure_cookies:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(
        {"detail": "This conflicts with an existing key or referenced record"}, status_code=409
    )


@app.exception_handler(StaleDataError)
async def stale_error(request, exc):
    return JSONResponse({"detail": "This record changed. Refresh and retry."}, status_code=409)


@app.exception_handler(Exception)
async def safe_error(request, exc):
    logger.error("Unhandled application error: %s", type(exc).__name__)
    return JSONResponse({"detail": "An internal error occurred; consult server logs"}, status_code=500)


@app.get("/api/health", tags=["Operations"])
def health(db: Session = Depends(get_db)):
    db.scalar(select(func.count()).select_from(m.Organization))
    return {"status": "ok", "version": "1.0.0", "demo_mode": settings().demo_mode}


def rate_limit(request):
    key = request.client.host if request.client else "local"
    queue = login_attempts[key]
    current = monotonic()
    while queue and current - queue[0] > 60:
        queue.popleft()
    if len(queue) >= 60:
        raise HTTPException(429, "Too many sign-in attempts; retry in one minute")
    queue.append(current)


@app.post("/api/auth/demo", tags=["Authentication"])
def demo_login(data: DemoInput, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request)
    if not settings().demo_mode:
        raise HTTPException(404, "Demo sign-in is disabled")
    return issue_session(db, response, f"Demo {data.role.title()}", data.role)


@app.post("/api/auth/login", tags=["Authentication"])
def login(data: LoginInput, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request)
    user = db.scalar(select(m.User).where(m.User.email == data.email.lower()))
    if not user or not password_hash.verify(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return issue_session(db, response, user.name, user.role)


@app.get("/api/auth/me", tags=["Authentication"])
def me(session=Depends(current_session)):
    return {
        "actor": session.actor,
        "role": session.role,
        "csrf_token": session.csrf_token,
        "demo_mode": settings().demo_mode,
    }


@app.post("/api/auth/logout", tags=["Authentication"])
def logout(response: Response, session=Depends(current_session), db: Session = Depends(get_db)):
    db.delete(session)
    db.commit()
    response.delete_cookie("eicc_session", path="/")
    return {"signed_out": True}


@app.get("/api/meta", tags=["Workspace"])
def metadata(session=Depends(current_session)):
    return {
        "schemas": {k: v.model_json_schema() for k, v in SCHEMAS.items()},
        "transitions": TRANSITIONS,
        "default_transitions": DEFAULT_TRANSITIONS,
        "fictional": True,
    }


@app.get("/api/workspace", tags=["Workspace"])
def workspace(project_id: int | None = None, session=Depends(current_session), db: Session = Depends(get_db)):
    query = select(m.Artifact).order_by(m.Artifact.key)
    if project_id:
        query = query.where((m.Artifact.project_id == project_id) | (m.Artifact.kind == "projects"))
    items = [serialize(a) for a in db.scalars(query)]
    latest = latest_executions(db)
    for item in items:
        if item["kind"] == "releases":
            item["readiness_status"] = release_readiness(db, db.get(m.Release, item["id"]))["status"]
        if item["kind"] == "test-cases":
            item["effective_test_status"] = execution_status(
                db, db.get(m.TestCase, item["id"]), latest.get(item["id"])
            )
    return {
        "items": items,
        "organizations": [serialize(a) for a in db.scalars(select(m.Organization))],
        "executions": [
            serialize(e)
            for e in latest_executions(db).values()
            if any(a["id"] == e.test_case_id for a in items)
        ],
    }


@app.get("/api/search", tags=["Workspace"])
def search(
    q: str = Query(min_length=1, max_length=200),
    project_id: int | None = None,
    session=Depends(current_session),
    db: Session = Depends(get_db),
):
    query = select(m.Artifact).where(
        m.Artifact.title.icontains(q, autoescape=True) | m.Artifact.key.icontains(q, autoescape=True)
    )
    if project_id:
        query = query.where((m.Artifact.project_id == project_id) | (m.Artifact.id == project_id))
    return [brief(a) for a in db.scalars(query.limit(40))]


@app.get("/api/traceability", tags=["Traceability"])
def matrix(
    project_id: int,
    requirement: str = "",
    system_id: int | None = None,
    integration_id: int | None = None,
    test_status: str = "",
    uat_status: str = "",
    release_id: int | None = None,
    session=Depends(current_session),
    db: Session = Depends(get_db),
):
    get_artifact(db, project_id, "projects")
    data = traceability(db, project_id)
    rows = data["rows"]
    if requirement:
        rows = [r for r in rows if requirement.lower() in (r["title"] + r["key"]).lower()]
    for related_id in [system_id, integration_id, release_id]:
        if related_id:
            rows = [r for r in rows if any(a["id"] == related_id for a in r["related"])]
    if test_status:
        rows = [r for r in rows if r["test_status"] == test_status]
    if uat_status:
        rows = [r for r in rows if r["uat_status"] == uat_status]
    return {**data, "rows": rows, "filtered_count": len(rows)}


@app.get("/api/impact/{entity_id}", tags=["Traceability"])
def impact(entity_id: int, session=Depends(current_session), db: Session = Depends(get_db)):
    obj = get_artifact(db, entity_id)
    return Graph(db, obj.project_id).impact(entity_id)


@app.get("/api/analytics", tags=["Reporting"])
def analytics(project_id: int, session=Depends(current_session), db: Session = Depends(get_db)):
    project = get_artifact(db, project_id, "projects")
    objects = list(db.scalars(select(m.Artifact).where(m.Artifact.project_id == project_id)))
    by_kind = {kind: [a for a in objects if a.kind == kind] for kind in m.MODELS}
    latest = latest_executions(db)
    current_results = {t.id: execution_status(db, t, latest.get(t.id)) for t in by_kind["test-cases"]}
    results = Counter(current_results.values())
    total = len(by_kind["test-cases"])
    executed = total - results["NOT_RUN"]
    uat = [uat_state(db, s.id) for s in by_kind["uat"]]
    defects = [d for d in by_kind["incidents"] if d.status not in {"RESOLVED", "CLOSED"}]
    risk = [
        r
        for r in by_kind["risks"]
        if r.probability * r.impact >= 15 and r.status not in {"MITIGATED", "CLOSED", "ACCEPTED"}
    ]
    tests = by_kind["test-cases"]
    failing = {t.integration_id for t in tests if t.integration_id and current_results[t.id] == "FAIL"}
    return {
        "project": serialize(project),
        "counts": {k: len(v) for k, v in by_kind.items()},
        "coverage": traceability(db, project_id)["metrics"],
        "test_results": {k: results[k] for k in ["PASS", "FAIL", "BLOCKED", "NOT_RUN"]},
        "completed_requirements": sum(r.status == "COMPLETE" for r in by_kind["requirements"]),
        "open_requirements": sum(r.status != "COMPLETE" for r in by_kind["requirements"]),
        "test_completion": round(100 * executed / total) if total else 0,
        "pass_rate": round(100 * results["PASS"] / executed) if executed else 0,
        "failure_rate": round(100 * results["FAIL"] / executed) if executed else 0,
        "blocked_rate": round(100 * results["BLOCKED"] / total) if total else 0,
        "defect_density": round(len(defects) / max(1, len(by_kind["requirements"])), 2),
        "uat_approval_rate": round(100 * sum(s["approved"] for s in uat) / len(uat)) if uat else 0,
        "protocols": dict(Counter(i.protocol for i in by_kind["integrations"])),
        "passing_integration_tests": sum(
            t.integration_id is not None and current_results[t.id] == "PASS" for t in tests
        ),
        "failing_integrations": len(failing),
        "open_defects": [brief(d) for d in defects],
        "critical_defects": [brief(d) for d in defects if d.severity == "CRITICAL"],
        "high_risks": [brief(r) for r in risk],
        "blocked_dependencies": [brief(d) for d in by_kind["dependencies"] if d.status == "BLOCKED"],
        "releases": [
            {**brief(r), "version": r.version, "readiness": release_readiness(db, r)}
            for r in by_kind["releases"]
        ],
    }


@app.post("/api/links", status_code=201, tags=["Traceability"])
def link(data: LinkInput, session=Depends(writer), db: Session = Depends(get_db)):
    require_role(session, "analyst", "manager")
    source, target = validate_link(db, data)
    record = m.ArtifactLink(**data.model_dump())
    db.add(record)
    db.flush()
    audit(
        db,
        session.actor,
        "relationship_created",
        source,
        after={**serialize(record), "target_key": target.key},
    )
    db.commit()
    return serialize(record)


@app.delete("/api/links/{link_id}", tags=["Traceability"])
def unlink(link_id: int, session=Depends(writer), db: Session = Depends(get_db)):
    require_role(session, "analyst", "manager")
    record = db.get(m.ArtifactLink, link_id)
    if not record:
        raise HTTPException(404, "Relationship not found")
    source = get_artifact(db, record.source_id)
    audit(db, session.actor, "relationship_removed", source, before=serialize(record), after={})
    db.delete(record)
    db.commit()
    return {"deleted": True}


@app.post("/api/integrations/{entity_id}/mappings", status_code=201, tags=["Integrations"])
def create_mapping(
    entity_id: int, data: MappingInput, session=Depends(writer), db: Session = Depends(get_db)
):
    require_role(session, "analyst", "manager")
    integration = get_artifact(db, entity_id, "integrations")
    mapping = m.FieldMapping(integration_id=entity_id, **data.model_dump())
    db.add(mapping)
    integration.updated_at = m.now()
    db.flush()
    audit(db, session.actor, "mapping_created", integration, after=serialize(mapping))
    db.commit()
    return serialize(mapping)


@app.patch("/api/mappings/{mapping_id}", tags=["Integrations"])
def update_mapping(
    mapping_id: int, data: MappingInput, session=Depends(writer), db: Session = Depends(get_db)
):
    require_role(session, "analyst", "manager")
    record = db.get(m.FieldMapping, mapping_id)
    if not record:
        raise HTTPException(404, "Mapping not found")
    before = serialize(record)
    for k, v in data.model_dump().items():
        setattr(record, k, v)
    integration = db.get(m.Integration, record.integration_id)
    integration.updated_at = m.now()
    audit(db, session.actor, "mapping_updated", integration, before, serialize(record))
    db.commit()
    return serialize(record)


@app.post("/api/test-cases/{entity_id}/execute", status_code=201, tags=["Testing"])
async def execute(
    entity_id: int,
    data: ExecutionInput,
    request: Request,
    session=Depends(writer),
    db: Session = Depends(get_db),
):
    require_role(session, "analyst", "tester", "manager")
    test = get_artifact(db, entity_id, "test-cases")
    if data.mode == "AUTOMATED":
        record = await execute_local(request, db, test, session.actor)
    else:
        if not data.status or len(data.evidence.strip()) < 10 or len(data.actual_result.strip()) < 5:
            raise HTTPException(
                422, "Manual execution requires a result, actual result and substantive evidence"
            )
        record = m.TestExecution(
            test_case_id=test.id,
            executed_by=session.actor,
            status=data.status,
            actual_result=data.actual_result,
            evidence=data.evidence,
        )
    record.contract_fingerprint = test_fingerprint(db, test)
    db.add(record)
    db.flush()
    audit(db, session.actor, "test_executed", test, after=serialize(record))
    if record.status == "PASS":
        defect_ids = set(
            db.scalars(
                select(m.TestExecution.defect_id).where(
                    m.TestExecution.test_case_id == test.id, m.TestExecution.defect_id.is_not(None)
                )
            )
        )
        for defect_id in defect_ids:
            audit(
                db,
                session.actor,
                "retest_passed",
                db.get(m.Incident, defect_id),
                after={"execution_id": record.id, "test_key": test.key, "status": "PASS"},
            )
    db.commit()
    return serialize(record)


@app.get("/api/test-executions", tags=["Testing"])
def executions(
    test_case_id: int | None = None, session=Depends(current_session), db: Session = Depends(get_db)
):
    query = select(m.TestExecution).order_by(m.TestExecution.id.desc())
    if test_case_id:
        query = query.where(m.TestExecution.test_case_id == test_case_id)
    return [serialize(e) for e in db.scalars(query.limit(500))]


@app.post("/api/test-executions/{execution_id}/defect", status_code=201, tags=["Incidents"])
def defect_from_execution(execution_id: int, session=Depends(writer), db: Session = Depends(get_db)):
    require_role(session, "analyst", "tester", "manager")
    execution = db.get(m.TestExecution, execution_id)
    if not execution:
        raise HTTPException(404, "Execution not found")
    if execution.status != "FAIL":
        raise HTTPException(409, "Only a failed execution can create a defect")
    if execution.defect_id:
        return serialize(db.get(m.Incident, execution.defect_id))
    test = db.get(m.TestCase, execution.test_case_id)
    defect = m.Incident(
        key=f"DEF-{secrets.token_hex(4).upper()}",
        title=f"Failed: {test.title}"[:240],
        description=execution.actual_result,
        project_id=test.project_id,
        status="NEW",
        severity="CRITICAL" if test.priority == "CRITICAL" else "HIGH",
        owner=session.actor,
        business_impact="Acceptance criteria are not satisfied; investigate before release.",
        technical_impact=execution.response_body[:10000],
    )
    db.add(defect)
    db.flush()
    execution.defect_id = defect.id
    for target in [test.id, test.requirement_id, test.integration_id]:
        if target:
            db.add(m.ArtifactLink(source_id=defect.id, target_id=target, relation="AFFECTS"))
    audit(
        db,
        session.actor,
        "defect_created_from_failure",
        defect,
        after={**serialize(defect), "execution_id": execution.id},
    )
    db.commit()
    return serialize(defect)


@app.post("/api/uat-scenarios/{entity_id}/results", status_code=201, tags=["UAT"])
def record_uat(entity_id: int, data: ResultInput, session=Depends(writer), db: Session = Depends(get_db)):
    require_role(session, "stakeholder", "tester", "analyst", "manager")
    scenario = get_artifact(db, entity_id, "uat-scenarios")
    uat = db.get(m.UATSession, scenario.session_id)
    if uat.status != "IN_PROGRESS":
        raise HTTPException(409, "Start or reopen the UAT session before recording results")
    record = m.UATResult(scenario_id=entity_id, actor=session.actor, **data.model_dump())
    db.add(record)
    db.flush()
    audit(db, session.actor, "uat_result_recorded", scenario, after=serialize(record))
    db.commit()
    return serialize(record)


@app.post("/api/uat/{entity_id}/approve", status_code=201, tags=["UAT"])
def approve_uat(entity_id: int, data: ApprovalInput, session=Depends(writer), db: Session = Depends(get_db)):
    require_role(session, "stakeholder", "manager")
    uat = get_artifact(db, entity_id, "uat")
    stakeholder = get_artifact(db, data.stakeholder_id, "stakeholders")
    if stakeholder.project_id != uat.project_id:
        raise HTTPException(422, "Stakeholder must belong to the UAT project")
    if uat.status not in {"IN_PROGRESS", "PASSED", "FAILED"}:
        raise HTTPException(409, "UAT must be in progress or evaluated before a decision")
    state = uat_state(db, entity_id)
    if data.decision == "APPROVED" and not state["ready"]:
        if len(data.override_reason.strip()) < 20:
            raise HTTPException(
                409,
                {
                    "message": "Mandatory acceptance evidence is incomplete; an explicit override of at least 20 characters is required",
                    "incomplete": state["incomplete"],
                },
            )
    record = m.UATApproval(
        session_id=entity_id, actor=session.actor, fingerprint=state["fingerprint"], **data.model_dump()
    )
    db.add(record)
    before = serialize(uat)
    uat.status = data.decision
    db.flush()
    audit(db, session.actor, "uat_decision", uat, before, serialize(record))
    db.commit()
    return serialize(record)


@app.post("/api/changes/{entity_id}/analyze", tags=["Changes"])
def analyze_change(entity_id: int, session=Depends(writer), db: Session = Depends(get_db)):
    require_role(session, "analyst", "manager")
    change = get_artifact(db, entity_id, "changes")
    if change.status not in {"ANALYSIS", "PENDING_APPROVAL"}:
        raise HTTPException(409, "Submit the change and move it to ANALYSIS first")
    result, fp = impact_snapshot(db, change)
    change.analysis_snapshot = result
    change.analysis_fingerprint = fp
    audit(db, session.actor, "impact_analysis_recorded", change, after=result)
    db.commit()
    return result


@app.get("/api/releases/{entity_id}/readiness", tags=["Releases"])
def readiness(entity_id: int, session=Depends(current_session), db: Session = Depends(get_db)):
    return release_readiness(db, get_artifact(db, entity_id, "releases"))


@app.get("/api/audit", tags=["Audit"])
def audit_records(
    entity_id: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    session=Depends(current_session),
    db: Session = Depends(get_db),
):
    query = select(m.AuditLog).order_by(m.AuditLog.id.desc())
    if entity_id:
        query = query.where(m.AuditLog.entity_id == entity_id)
    return [serialize(a) for a in db.scalars(query.limit(limit))]


@app.post("/api/reports", status_code=201, tags=["Reporting"])
def generate_report(data: ReportInput, session=Depends(writer), db: Session = Depends(get_db)):
    project = get_artifact(db, data.project_id, "projects")
    version = 1 + (
        db.scalar(
            select(func.max(m.Document.version)).where(
                m.Document.project_id == project.id, m.Document.document_type == data.document_type
            )
        )
        or 0
    )
    document = m.Document(
        key=f"DOC-{secrets.token_hex(4).upper()}",
        title=f"{data.document_type} · v{version}",
        project_id=project.id,
        owner=session.actor,
        status="DRAFT",
        version=version,
        document_type=data.document_type,
        content=generate_markdown(db, project, data.document_type),
    )
    db.add(document)
    db.flush()
    audit(db, session.actor, "document_generated", document)
    db.commit()
    return serialize(document)


@app.get("/api/documents/{entity_id}/export", tags=["Reporting"])
def export_document(entity_id: int, session=Depends(current_session), db: Session = Depends(get_db)):
    document = get_artifact(db, entity_id, "documents")
    return PlainTextResponse(
        document.content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{document.key}-v{document.version}.md"'},
    )


@app.post("/api/admin/reset-demo", tags=["Administration"])
def reset_demo(data: ResetInput, request: Request, session=Depends(writer), db: Session = Depends(get_db)):
    require_role(session, "admin")
    if not settings().demo_mode:
        raise HTTPException(403, "Demo reset is disabled")
    from fastapi.testclient import TestClient

    from backend.seed import populate_evidence, reset_northstar, seed

    reset_northstar(db)
    seed(db)
    db.add(
        m.AuditLog(
            actor=session.actor,
            action="demo_reset",
            entity="workspace",
            new_value={"confirmation": data.confirmation},
        )
    )
    db.commit()
    with TestClient(request.app) as demo_client:
        populate_evidence(demo_client)
    return {"reset": True}


def register_crud(kind, model, schema):
    def list_records(
        project_id: int | None = None,
        q: str = "",
        status: str = "",
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=200),
        session=Depends(current_session),
        db: Session = Depends(get_db),
    ):
        query = select(model)
        if project_id:
            query = query.where(model.project_id == project_id)
        if q:
            query = query.where(
                model.title.icontains(q, autoescape=True) | model.key.icontains(q, autoescape=True)
            )
        if status:
            query = query.where(model.status == status)
        total = db.scalar(select(func.count()).select_from(query.subquery()))
        return {
            "items": [
                serialize(a)
                for a in db.scalars(query.order_by(model.key).offset((page - 1) * page_size).limit(page_size))
            ],
            "total": total,
            "page": page,
        }

    def detail(entity_id: int, session=Depends(current_session), db: Session = Depends(get_db)):
        obj = get_artifact(db, entity_id, kind)
        result = serialize(obj)
        result["links"] = [
            serialize(e)
            for e in db.scalars(
                select(m.ArtifactLink).where(
                    (m.ArtifactLink.source_id == entity_id) | (m.ArtifactLink.target_id == entity_id)
                )
            )
        ]
        result["allowed_transitions"] = TRANSITIONS.get(kind, DEFAULT_TRANSITIONS).get(obj.status, [])
        if kind != "projects":
            result["impact_analysis"] = Graph(db, obj.project_id).impact(obj.id)
        if kind == "requirements":
            result["traceability"] = next(
                r for r in traceability(db, obj.project_id)["rows"] if r["id"] == obj.id
            )
        if kind == "integrations":
            result["mappings"] = [
                serialize(v)
                for v in db.scalars(select(m.FieldMapping).where(m.FieldMapping.integration_id == entity_id))
            ]
        if kind == "test-cases":
            result["executions"] = [
                {**serialize(e), "current_contract": e.contract_fingerprint == test_fingerprint(db, obj)}
                for e in db.scalars(
                    select(m.TestExecution)
                    .where(m.TestExecution.test_case_id == entity_id)
                    .order_by(m.TestExecution.id.desc())
                )
            ]
        if kind == "uat":
            result["acceptance"] = uat_state(db, entity_id)
        if kind == "releases":
            result["readiness"] = release_readiness(db, obj)
        if kind == "incidents":
            result["timeline"] = [
                serialize(a)
                for a in db.scalars(
                    select(m.AuditLog).where(m.AuditLog.entity_id == entity_id).order_by(m.AuditLog.id)
                )
            ]
        if kind == "changes":
            _, fp = impact_snapshot(db, obj)
            result["analysis_current"] = bool(obj.analysis_fingerprint and obj.analysis_fingerprint == fp)
        return result

    def create_record(data: schema, session=Depends(writer), db: Session = Depends(get_db)):
        require_role(
            session,
            "analyst",
            "manager",
            *(["tester"] if kind in {"test-plans", "test-cases", "incidents"} else []),
        )
        values = data.model_dump()
        validate_references(db, kind, values)
        obj = model(**values, status=INITIAL.get(kind, "DRAFT"))
        db.add(obj)
        db.flush()
        audit(db, session.actor, "created", obj)
        db.commit()
        return serialize(obj)

    def update_record(
        entity_id: int, data: dict, request: Request, session=Depends(writer), db: Session = Depends(get_db)
    ):
        require_role(
            session,
            "analyst",
            "manager",
            *(["tester"] if kind in {"test-plans", "test-cases", "incidents"} else []),
        )
        obj = get_artifact(db, entity_id, kind)
        if kind == "documents":
            raise HTTPException(409, "Generated document content is immutable; generate a new version")
        if "status" in data:
            raise HTTPException(422, "Use the transition endpoint to change status")
        match = request.headers.get("If-Match")
        if not match:
            raise HTTPException(428, "Supply If-Match with the current record revision")
        if match != str(obj.revision):
            raise HTTPException(409, "This record changed; refresh before editing")
        before = serialize(obj)
        values = {k: before[k] for k in schema.model_fields if k in before}
        try:
            validated = schema.model_validate({**values, **data}).model_dump()
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc
        if validated.get("project_id") != obj.project_id:
            raise HTTPException(422, "Records cannot be moved across projects")
        validate_references(db, kind, validated)
        for k, v in validated.items():
            setattr(obj, k, v)
        obj.updated_at = m.now()
        db.flush()
        audit(db, session.actor, "updated", obj, before)
        db.commit()
        return serialize(obj)

    def change_status(
        entity_id: int, data: TransitionInput, session=Depends(writer), db: Session = Depends(get_db)
    ):
        require_role(
            session,
            "analyst",
            "manager",
            *(["tester"] if kind in {"test-plans", "test-cases", "incidents", "uat"} else []),
            *(["stakeholder"] if kind == "uat" else []),
        )
        obj = transition(
            db, get_artifact(db, entity_id, kind), data.status, session.actor, session.role, data.comment
        )
        db.commit()
        return serialize(obj)

    def delete_record(entity_id: int, session=Depends(writer), db: Session = Depends(get_db)):
        require_role(session, "analyst", "manager")
        obj = get_artifact(db, entity_id, kind)
        if obj.status != "DRAFT":
            raise HTTPException(409, "Only unlinked draft records can be deleted; retain governed history")
        if db.scalar(
            select(m.ArtifactLink.id).where(
                (m.ArtifactLink.source_id == entity_id) | (m.ArtifactLink.target_id == entity_id)
            )
        ):
            raise HTTPException(409, "Remove relationships before deleting a draft")
        audit(db, session.actor, "deleted", obj, before=serialize(obj), after={})
        db.delete(obj)
        db.commit()
        return {"deleted": True}

    for path, endpoint, methods, code in [
        (f"/api/{kind}", list_records, ["GET"], 200),
        (f"/api/{kind}", create_record, ["POST"], 201),
        (f"/api/{kind}/{{entity_id}}", detail, ["GET"], 200),
        (f"/api/{kind}/{{entity_id}}", update_record, ["PATCH"], 200),
        (f"/api/{kind}/{{entity_id}}/transition", change_status, ["POST"], 200),
        (f"/api/{kind}/{{entity_id}}", delete_record, ["DELETE"], 200),
    ]:
        app.add_api_route(
            path,
            endpoint,
            methods=methods,
            status_code=code,
            tags=[kind.title()],
            name=f"{endpoint.__name__}_{kind}",
        )


for domain_kind, domain_model in m.MODELS.items():
    register_crud(domain_kind, domain_model, SCHEMAS[domain_kind])
