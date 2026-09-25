"""Joined-table artifacts keep graph identity normalized and subtype fields strongly typed."""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


def now():
    return datetime.now(UTC)


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")


class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    key: Mapped[str] = mapped_column(String(50), unique=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    project_id: Mapped[int | None] = mapped_column(ForeignKey("artifacts.id"), index=True)
    owner: Mapped[str] = mapped_column(String(150), default="Unassigned")
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"polymorphic_on": kind, "polymorphic_identity": "artifact", "version_id_col": revision}


class Project(Artifact):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    start_date: Mapped[datetime | None] = mapped_column(Date)
    target_date: Mapped[datetime | None] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String(20), default="HIGH")
    __mapper_args__ = {"polymorphic_identity": "projects"}


class Stakeholder(Artifact):
    __tablename__ = "stakeholders"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(100), default="Business owner")
    department: Mapped[str] = mapped_column(String(100), default="Operations")
    contact: Mapped[str] = mapped_column(String(200), default="")
    __mapper_args__ = {"polymorphic_identity": "stakeholders"}


class BusinessProcess(Artifact):
    __tablename__ = "processes"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    current_state: Mapped[str] = mapped_column(Text, default="")
    future_state: Mapped[str] = mapped_column(Text, default="")
    steps: Mapped[list] = mapped_column(JSON, default=list)
    __mapper_args__ = {"polymorphic_identity": "processes"}


class Requirement(Artifact):
    __tablename__ = "requirements"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    type: Mapped[str] = mapped_column(String(30), default="BUSINESS")
    priority: Mapped[str] = mapped_column(String(20), default="HIGH")
    source: Mapped[str] = mapped_column(Text, default="Stakeholder workshop")
    acceptance_criteria: Mapped[str] = mapped_column(Text)
    __mapper_args__ = {"polymorphic_identity": "requirements"}


class System(Artifact):
    __tablename__ = "systems"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    system_type: Mapped[str] = mapped_column(String(60), default="Internal application")
    environment: Mapped[str] = mapped_column(String(30), default="TEST")
    criticality: Mapped[str] = mapped_column(String(20), default="HIGH")
    technology: Mapped[str] = mapped_column(String(150), default="")
    __mapper_args__ = {"polymorphic_identity": "systems"}


class Integration(Artifact):
    __tablename__ = "integrations"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    source_system_id: Mapped[int] = mapped_column(ForeignKey("systems.id"))
    target_system_id: Mapped[int] = mapped_column(ForeignKey("systems.id"))
    protocol: Mapped[str] = mapped_column(String(10), default="REST")
    direction: Mapped[str] = mapped_column(String(20), default="OUTBOUND")
    mode: Mapped[str] = mapped_column(String(20), default="SYNCHRONOUS")
    endpoint: Mapped[str] = mapped_column(String(200), default="/simulator/notifications")
    method: Mapped[str] = mapped_column(String(30), default="POST")
    authentication_type: Mapped[str] = mapped_column(String(60), default="OAuth2 (simulated)")
    data_format: Mapped[str] = mapped_column(String(10), default="JSON")
    request_format: Mapped[str] = mapped_column(Text, default="")
    response_format: Mapped[str] = mapped_column(Text, default="")
    __mapper_args__ = {"polymorphic_identity": "integrations"}


class FieldMapping(Base):
    __tablename__ = "field_mappings"
    id: Mapped[int] = mapped_column(primary_key=True)
    integration_id: Mapped[int] = mapped_column(ForeignKey("integrations.id", ondelete="CASCADE"), index=True)
    source_field: Mapped[str] = mapped_column(String(80))
    target_field: Mapped[str] = mapped_column(String(80))
    datatype: Mapped[str] = mapped_column(String(20), default="string")
    transformation: Mapped[str] = mapped_column(String(20), default="identity")
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    validation_rule: Mapped[str] = mapped_column(String(150), default="non_empty")
    __table_args__ = (UniqueConstraint("integration_id", "target_field"),)


class Dependency(Artifact):
    __tablename__ = "dependencies"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("artifacts.id"))
    target_id: Mapped[int] = mapped_column(ForeignKey("artifacts.id"))
    impact: Mapped[str] = mapped_column(Text, default="")
    __mapper_args__ = {"polymorphic_identity": "dependencies", "inherit_condition": id == Artifact.id}


class Risk(Artifact):
    __tablename__ = "risks"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    probability: Mapped[int] = mapped_column(Integer, default=3)
    impact: Mapped[int] = mapped_column(Integer, default=3)
    mitigation: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (
        CheckConstraint("probability BETWEEN 1 AND 5"),
        CheckConstraint("impact BETWEEN 1 AND 5"),
    )
    __mapper_args__ = {"polymorphic_identity": "risks"}


class TestPlan(Artifact):
    __tablename__ = "test_plans"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    scope: Mapped[str] = mapped_column(Text, default="")
    objectives: Mapped[str] = mapped_column(Text, default="")
    environment: Mapped[str] = mapped_column(String(30), default="TEST")
    entry_criteria: Mapped[str] = mapped_column(Text, default="Requirements approved; simulator available")
    exit_criteria: Mapped[str] = mapped_column(Text, default="Mandatory tests pass; no critical defects")
    __mapper_args__ = {"polymorphic_identity": "test-plans"}


class TestCase(Artifact):
    __tablename__ = "test_cases"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    test_plan_id: Mapped[int] = mapped_column(ForeignKey("test_plans.id"))
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id"))
    integration_id: Mapped[int | None] = mapped_column(ForeignKey("integrations.id"))
    type: Mapped[str] = mapped_column(String(30), default="INTEGRATION")
    priority: Mapped[str] = mapped_column(String(20), default="HIGH")
    preconditions: Mapped[str] = mapped_column(Text, default="Simulator available")
    steps: Mapped[str] = mapped_column(Text, default="Submit payload; compare response with expected result.")
    expected_result: Mapped[str] = mapped_column(Text, default="Valid response with string case_id")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    expected_status: Mapped[int] = mapped_column(Integer, default=201)
    scenario: Mapped[str] = mapped_column(String(30), default="success")
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    __mapper_args__ = {"polymorphic_identity": "test-cases"}


class TestExecution(Base):
    __tablename__ = "test_executions"
    id: Mapped[int] = mapped_column(primary_key=True)
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"), index=True)
    environment: Mapped[str] = mapped_column(String(30), default="TEST")
    executed_by: Mapped[str] = mapped_column(String(150))
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    status: Mapped[str] = mapped_column(String(20))
    actual_result: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    request_body: Mapped[str] = mapped_column(Text, default="")
    response_body: Mapped[str] = mapped_column(Text, default="")
    response_status: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    contract_fingerprint: Mapped[str] = mapped_column(String(64), default="", server_default="")
    defect_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id"))
    __table_args__ = (
        CheckConstraint("status IN ('PASS','FAIL','BLOCKED','NOT_RUN')", name="ck_test_execution_status"),
    )


class UATSession(Artifact):
    __tablename__ = "uat_sessions"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    coordinator: Mapped[str] = mapped_column(String(150), default="Jordan Lee")
    start_date: Mapped[datetime | None] = mapped_column(Date)
    end_date: Mapped[datetime | None] = mapped_column(Date)
    __mapper_args__ = {"polymorphic_identity": "uat"}


class UATScenario(Artifact):
    __tablename__ = "uat_scenarios"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("uat_sessions.id"))
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id"))
    steps: Mapped[str] = mapped_column(Text)
    expected_result: Mapped[str] = mapped_column(Text)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    __mapper_args__ = {"polymorphic_identity": "uat-scenarios"}


class UATResult(Base):
    __tablename__ = "uat_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("uat_scenarios.id"), index=True)
    actor: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(20))
    evidence: Mapped[str] = mapped_column(Text)
    comments: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (CheckConstraint("status IN ('PASS','FAIL','BLOCKED')"),)


class UATApproval(Base):
    __tablename__ = "uat_approvals"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("uat_sessions.id"), index=True)
    stakeholder_id: Mapped[int] = mapped_column(ForeignKey("stakeholders.id"))
    actor: Mapped[str] = mapped_column(String(150))
    decision: Mapped[str] = mapped_column(String(20))
    comments: Mapped[str] = mapped_column(Text)
    override_reason: Mapped[str] = mapped_column(Text, default="")
    fingerprint: Mapped[str] = mapped_column(String(64))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Incident(Artifact):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    type: Mapped[str] = mapped_column(String(20), default="DEFECT")
    severity: Mapped[str] = mapped_column(String(20), default="HIGH")
    priority: Mapped[str] = mapped_column(String(20), default="HIGH")
    environment: Mapped[str] = mapped_column(String(30), default="TEST")
    assigned_to: Mapped[str] = mapped_column(String(150), default="Unassigned")
    business_impact: Mapped[str] = mapped_column(Text, default="")
    technical_impact: Mapped[str] = mapped_column(Text, default="")
    root_cause: Mapped[str] = mapped_column(Text, default="")
    workaround: Mapped[str] = mapped_column(Text, default="")
    resolution: Mapped[str] = mapped_column(Text, default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __mapper_args__ = {"polymorphic_identity": "incidents"}


class ChangeRequest(Artifact):
    __tablename__ = "changes"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    impact: Mapped[str] = mapped_column(Text, default="")
    risk: Mapped[str] = mapped_column(Text, default="")
    requested_by: Mapped[str] = mapped_column(String(150), default="Jordan Lee")
    approved_by: Mapped[str] = mapped_column(String(150), default="")
    analysis_fingerprint: Mapped[str] = mapped_column(String(64), default="")
    analysis_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    __mapper_args__ = {"polymorphic_identity": "changes"}


class Release(Artifact):
    __tablename__ = "releases"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    version: Mapped[str] = mapped_column(String(40))
    target_date: Mapped[datetime | None] = mapped_column(Date)
    deployment_notes: Mapped[str] = mapped_column(Text, default="")
    rollback_plan: Mapped[str] = mapped_column(Text, default="")
    __mapper_args__ = {"polymorphic_identity": "releases"}


class TrainingMaterial(Artifact):
    __tablename__ = "training"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    audience: Mapped[str] = mapped_column(String(150), default="Case operations")
    content: Mapped[str] = mapped_column(Text)
    __mapper_args__ = {"polymorphic_identity": "training"}


class Document(Artifact):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    document_type: Mapped[str] = mapped_column(String(80))
    content: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"polymorphic_identity": "documents"}


class ArtifactLink(Base):
    __tablename__ = "artifact_links"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), index=True)
    relation: Mapped[str] = mapped_column(String(30))
    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "relation"),
        CheckConstraint("source_id <> target_id"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(150))
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    previous_value: Mapped[dict | None] = mapped_column(JSON)
    new_value: Mapped[dict | None] = mapped_column(JSON)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(30))


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_token: Mapped[str] = mapped_column(String(100))
    actor: Mapped[str] = mapped_column(String(150))
    role: Mapped[str] = mapped_column(String(30))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EvidenceAttachment(Base):
    __tablename__ = "evidence_attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int | None] = mapped_column(
        ForeignKey("test_executions.id", ondelete="CASCADE"), index=True
    )
    uat_result_id: Mapped[int | None] = mapped_column(
        ForeignKey("uat_results.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(150))
    media_type: Mapped[str] = mapped_column(String(80))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(150))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        CheckConstraint(
            "(execution_id IS NOT NULL AND uat_result_id IS NULL) OR (execution_id IS NULL AND uat_result_id IS NOT NULL)"
        ),
    )


class SimulatorCase(Base):
    __tablename__ = "simulator_cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(String(80), unique=True)
    status: Mapped[str] = mapped_column(String(30))
    payload: Mapped[dict] = mapped_column(JSON)


MODELS = {
    m.__mapper_args__["polymorphic_identity"]: m
    for m in (
        Project,
        Stakeholder,
        BusinessProcess,
        Requirement,
        System,
        Integration,
        Dependency,
        Risk,
        TestPlan,
        TestCase,
        UATSession,
        UATScenario,
        Incident,
        ChangeRequest,
        Release,
        TrainingMaterial,
        Document,
    )
}
