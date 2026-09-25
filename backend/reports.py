from collections import Counter

from sqlalchemy import select

from backend import models as m
from backend.graph import release_readiness, traceability


def generate_markdown(db, project, document_type):
    artifacts = list(
        db.scalars(select(m.Artifact).where(m.Artifact.project_id == project.id).order_by(m.Artifact.key))
    )
    lines = [
        f"# {document_type}",
        "",
        f"Project: {project.key} — {project.title}",
        "",
        "Fictional Northstar Enterprise Services portfolio demonstration. No government or vendor affiliation.",
        "",
        f"Generated from stored records at {m.now().isoformat()}. This document is a versioned snapshot.",
        "",
    ]
    kinds = {
        "Business Requirements Document": {"requirements", "stakeholders", "processes"},
        "Functional Requirements Document": {"requirements", "systems"},
        "Integration Specification": {"integrations", "dependencies", "risks"},
        "Test Plan": {"test-plans", "test-cases"},
        "UAT Plan": {"uat", "uat-scenarios", "stakeholders"},
        "Release Notes": {"releases", "changes", "incidents"},
        "Training Guide": {"training", "processes"},
        "Project Status Report": {"projects", "risks", "dependencies", "releases"},
    }[document_type]
    if document_type == "Project Status Report":
        matrix = traceability(db, project.id)
        lines += [
            "## Current metrics",
            "",
            *[f"- {k.replace('_', ' ').title()}: {v}" for k, v in matrix["metrics"].items()],
            "",
            f"Artifact counts: {dict(Counter(a.kind for a in artifacts))}",
            "",
        ]
    for a in artifacts:
        if a.kind not in kinds:
            continue
        if a.kind == "requirements":
            if document_type == "Business Requirements Document" and a.type != "BUSINESS":
                continue
            if document_type == "Functional Requirements Document" and a.type not in {
                "FUNCTIONAL",
                "TECHNICAL",
                "NON_FUNCTIONAL",
                "INTEGRATION",
            }:
                continue
        lines += [
            f"## {a.key}: {a.title}",
            "",
            f"Status: {a.status} · Owner: {a.owner}",
            "",
            a.description,
            "",
        ]
        for field in [
            "acceptance_criteria",
            "source",
            "scope",
            "objectives",
            "entry_criteria",
            "exit_criteria",
            "steps",
            "expected_result",
            "content",
            "mitigation",
            "impact",
            "root_cause",
            "resolution",
            "deployment_notes",
            "rollback_plan",
            "current_state",
            "future_state",
        ]:
            value = getattr(a, field, None)
            if value:
                lines += [f"### {field.replace('_', ' ').title()}", "", str(value), ""]
        if a.kind == "integrations":
            source, target = db.get(m.System, a.source_system_id), db.get(m.System, a.target_system_id)
            lines += [
                f"{source.title} → {target.title}",
                "",
                f"Protocol: {a.protocol} / {a.data_format}; {a.method} {a.endpoint}",
                "",
                f"Authentication design: {a.authentication_type}; execution is local simulation.",
                "",
                "| Source | Target | Type | Transformation | Required | Validation |",
                "|---|---|---|---|---|---|",
            ]
            for mapping in db.scalars(select(m.FieldMapping).where(m.FieldMapping.integration_id == a.id)):
                lines.append(
                    f"| {mapping.source_field} | {mapping.target_field} | {mapping.datatype} | {mapping.transformation} | {mapping.required} | {mapping.validation_rule} |"
                )
            lines += [
                "",
                "### Request contract",
                "",
                "```",
                a.request_format,
                "```",
                "",
                "### Response contract",
                "",
                "```",
                a.response_format,
                "```",
                "",
            ]
        if a.kind == "releases":
            readiness = release_readiness(db, a)
            lines += [
                f"Readiness: **{readiness['status']}**",
                "",
                *[f"- {g['name']}: {g['status']} — {g['detail']}" for g in readiness["gates"]],
                "",
            ]
    return "\n".join(lines)
