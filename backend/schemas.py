from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Priority = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
Scenario = Literal[
    "success", "bad_request", "unauthorized", "not_found", "conflict", "server_error", "timeout"
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ArtifactInput(Strict):
    key: str = Field(pattern=r"^[A-Z][A-Z0-9-]{2,49}$")
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(default="", max_length=20000)
    project_id: int | None = None
    owner: str = Field(default="Jordan Lee", min_length=1, max_length=150)


class ProjectInput(ArtifactInput):
    organization_id: int = 1
    start_date: date | None = None
    target_date: date | None = None
    priority: Priority = "HIGH"

    @model_validator(mode="after")
    def dates(self):
        if self.start_date and self.target_date and self.target_date < self.start_date:
            raise ValueError("Target date must follow start date")
        return self


class StakeholderInput(ArtifactInput):
    role: str = Field(default="Business owner", max_length=100)
    department: str = Field(default="Operations", max_length=100)
    contact: str = Field(default="", max_length=200)


class ProcessInput(ArtifactInput):
    current_state: str = Field(default="", max_length=20000)
    future_state: str = Field(default="", max_length=20000)
    steps: list[str] = Field(default_factory=list, max_length=30)


class RequirementInput(ArtifactInput):
    type: Literal["BUSINESS", "FUNCTIONAL", "TECHNICAL", "NON_FUNCTIONAL", "INTEGRATION"] = "BUSINESS"
    priority: Priority = "HIGH"
    source: str = Field(default="Stakeholder workshop", max_length=3000)
    acceptance_criteria: str = Field(min_length=5, max_length=20000)


class SystemInput(ArtifactInput):
    system_type: str = Field(default="Internal application", max_length=60)
    environment: Literal["DEV", "TEST", "UAT", "PRODUCTION"] = "TEST"
    criticality: Priority = "HIGH"
    technology: str = Field(default="", max_length=150)


class IntegrationInput(ArtifactInput):
    source_system_id: int
    target_system_id: int
    protocol: Literal["REST", "SOAP"] = "REST"
    direction: Literal["INBOUND", "OUTBOUND", "BIDIRECTIONAL"] = "OUTBOUND"
    mode: Literal["SYNCHRONOUS", "ASYNCHRONOUS"] = "SYNCHRONOUS"
    endpoint: Literal[
        "/simulator/cases", "/simulator/notifications", "/simulator/soap", "/simulator/cases/{id}"
    ] = "/simulator/notifications"
    method: Literal["POST", "GET", "CreateCase"] = "POST"
    authentication_type: str = Field(default="OAuth2 (simulated)", max_length=60)
    data_format: Literal["JSON", "XML"] = "JSON"
    request_format: str = Field(default="", max_length=10000)
    response_format: str = Field(default="", max_length=10000)

    @model_validator(mode="after")
    def coherent_protocol(self):
        if self.source_system_id == self.target_system_id:
            raise ValueError("Source and target systems must differ")
        if self.protocol == "SOAP":
            if self.endpoint != "/simulator/soap" or self.data_format != "XML" or self.method != "CreateCase":
                raise ValueError("SOAP requires /simulator/soap, XML and CreateCase")
        elif self.endpoint == "/simulator/soap" or self.data_format != "JSON":
            raise ValueError("REST requires a JSON simulator endpoint")
        elif (self.endpoint == "/simulator/cases/{id}") != (self.method == "GET"):
            raise ValueError("GET is reserved for /simulator/cases/{id}")
        elif self.method == "CreateCase":
            raise ValueError("REST method must be GET or POST")
        return self


class MappingInput(Strict):
    source_field: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,79}$")
    target_field: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,79}$")
    datatype: Literal["string", "integer", "boolean"] = "string"
    transformation: Literal["identity", "to_string", "to_integer", "uppercase", "lowercase"] = "identity"
    required: bool = True
    validation_rule: Literal["none", "non_empty", "positive", "email"] = "non_empty"


class DependencyInput(ArtifactInput):
    source_id: int
    target_id: int
    impact: str = Field(min_length=3, max_length=10000)


class RiskInput(ArtifactInput):
    probability: int = Field(default=3, ge=1, le=5)
    impact: int = Field(default=3, ge=1, le=5)
    mitigation: str = Field(min_length=5, max_length=10000)


class TestPlanInput(ArtifactInput):
    scope: str = Field(min_length=3, max_length=10000)
    objectives: str = Field(default="Validate acceptance criteria", max_length=10000)
    environment: Literal["DEV", "TEST", "UAT"] = "TEST"
    entry_criteria: str = Field(default="Requirements approved; simulator available", max_length=10000)
    exit_criteria: str = Field(default="Mandatory tests pass; no critical defects", max_length=10000)


class TestCaseInput(ArtifactInput):
    test_plan_id: int
    requirement_id: int
    integration_id: int | None = None
    type: Literal["FUNCTIONAL", "INTEGRATION", "REGRESSION", "SECURITY"] = "INTEGRATION"
    priority: Priority = "HIGH"
    preconditions: str = Field(default="Simulator available", max_length=10000)
    steps: str = Field(
        default="Submit payload; compare response with expected result.", min_length=5, max_length=20000
    )
    expected_result: str = Field(default="Valid response with string case_id", min_length=5, max_length=10000)
    payload: dict = Field(
        default_factory=lambda: {
            "case_id": "NS-1001",
            "status": "ACCEPTED",
            "recipient": "case.owner@example.test",
        }
    )
    expected_status: Literal[200, 201, 202, 400, 401, 404, 409, 500, 504] = 201
    scenario: Scenario = "success"
    mandatory: bool = True


class UATInput(ArtifactInput):
    coordinator: str = Field(default="Jordan Lee", max_length=150)
    start_date: date | None = None
    end_date: date | None = None


class UATScenarioInput(ArtifactInput):
    session_id: int
    requirement_id: int
    steps: str = Field(min_length=5, max_length=20000)
    expected_result: str = Field(min_length=5, max_length=10000)
    mandatory: bool = True


class IncidentInput(ArtifactInput):
    type: Literal["INCIDENT", "DEFECT"] = "DEFECT"
    severity: Priority = "HIGH"
    priority: Priority = "HIGH"
    environment: Literal["DEV", "TEST", "UAT", "PRODUCTION"] = "TEST"
    assigned_to: str = Field(default="Unassigned", max_length=150)
    business_impact: str = Field(default="", max_length=10000)
    technical_impact: str = Field(default="", max_length=10000)
    root_cause: str = Field(default="", max_length=10000)
    workaround: str = Field(default="", max_length=10000)
    resolution: str = Field(default="", max_length=10000)


class ChangeInput(ArtifactInput):
    reason: str = Field(min_length=5, max_length=10000)
    impact: str = Field(default="", max_length=10000)
    risk: str = Field(default="", max_length=10000)
    requested_by: str = Field(default="Jordan Lee", max_length=150)


class ReleaseInput(ArtifactInput):
    version: str = Field(min_length=1, max_length=40)
    target_date: date | None = None
    deployment_notes: str = Field(default="", max_length=20000)
    rollback_plan: str = Field(default="", max_length=20000)


class TrainingInput(ArtifactInput):
    audience: str = Field(default="Case operations", max_length=150)
    content: str = Field(min_length=5, max_length=100000)


class DocumentInput(ArtifactInput):
    document_type: str = Field(min_length=3, max_length=80)
    content: str = Field(min_length=5, max_length=100000)


SCHEMAS = dict(
    zip(
        [
            "projects",
            "stakeholders",
            "processes",
            "requirements",
            "systems",
            "integrations",
            "dependencies",
            "risks",
            "test-plans",
            "test-cases",
            "uat",
            "uat-scenarios",
            "incidents",
            "changes",
            "releases",
            "training",
            "documents",
        ],
        [
            ProjectInput,
            StakeholderInput,
            ProcessInput,
            RequirementInput,
            SystemInput,
            IntegrationInput,
            DependencyInput,
            RiskInput,
            TestPlanInput,
            TestCaseInput,
            UATInput,
            UATScenarioInput,
            IncidentInput,
            ChangeInput,
            ReleaseInput,
            TrainingInput,
            DocumentInput,
        ],
        strict=True,
    )
)


class LinkInput(Strict):
    source_id: int
    target_id: int
    relation: Literal["DECOMPOSES", "AFFECTS", "VERIFIES", "CONTAINS", "DOCUMENTS", "MITIGATES", "RELATES"]


class TransitionInput(Strict):
    status: str = Field(max_length=40)
    comment: str = Field(default="", max_length=10000)


class ExecutionInput(Strict):
    mode: Literal["AUTOMATED", "MANUAL"] = "AUTOMATED"
    status: Literal["PASS", "FAIL", "BLOCKED", "NOT_RUN"] | None = None
    actual_result: str = Field(default="", max_length=10000)
    evidence: str = Field(default="", max_length=50000)


class ResultInput(Strict):
    status: Literal["PASS", "FAIL", "BLOCKED"]
    evidence: str = Field(min_length=10, max_length=50000)
    comments: str = Field(default="", max_length=10000)


class ApprovalInput(Strict):
    stakeholder_id: int
    decision: Literal["APPROVED", "REJECTED"]
    comments: str = Field(min_length=5, max_length=10000)
    override_reason: str = Field(default="", max_length=10000)


class LoginInput(Strict):
    email: str = Field(max_length=200)
    password: str = Field(min_length=1, max_length=200)


class DemoInput(Strict):
    role: Literal["analyst", "tester", "stakeholder", "manager", "viewer", "admin"] = "analyst"


class ResetInput(Strict):
    confirmation: Literal["RESET NORTHSTAR DEMO"]


class ReportInput(Strict):
    project_id: int
    document_type: Literal[
        "Business Requirements Document",
        "Functional Requirements Document",
        "Integration Specification",
        "Test Plan",
        "UAT Plan",
        "Release Notes",
        "Training Guide",
        "Project Status Report",
    ]
