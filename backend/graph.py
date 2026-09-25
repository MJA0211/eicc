"""Trace only real edges; release containers never expand unrelated release scope."""

import hashlib
import json
from collections import Counter

from fastapi.encoders import jsonable_encoder
from sqlalchemy import inspect, select

from backend import models as m


def serialize(obj):
    return jsonable_encoder({a.key: getattr(obj, a.key) for a in inspect(obj).mapper.column_attrs})


def brief(obj):
    return {"id": obj.id, "key": obj.key, "kind": obj.kind, "title": obj.title, "status": obj.status}


class Graph:
    def __init__(self, db, project_id=None):
        query = select(m.Artifact)
        if project_id:
            query = query.where(m.Artifact.project_id == project_id)
        self.nodes = {a.id: a for a in db.scalars(query)}
        self.edges = [
            (e.source_id, e.target_id, e.relation)
            for e in db.scalars(select(m.ArtifactLink))
            if e.source_id in self.nodes and e.target_id in self.nodes
        ]
        for a in self.nodes.values():
            fields = {
                "source_system_id": "SOURCE",
                "target_system_id": "TARGET",
                "requirement_id": "VERIFIES",
                "integration_id": "EXERCISES",
                "test_plan_id": "PLANNED_IN",
                "session_id": "SESSION",
                "source_id": "DEPENDS",
                "target_id": "DEPENDS",
            }
            for field, relation in fields.items():
                target = getattr(a, field, None)
                if target in self.nodes:
                    self.edges.append((a.id, target, relation))
        self.edges = list(dict.fromkeys(self.edges))

    def descendants(self, ids):
        reached = set(ids)
        while True:
            added = {t for s, t, r in self.edges if s in reached and r == "DECOMPOSES"} - reached
            if not added:
                return reached
            reached |= added

    def scope(self, requirement_id):
        reqs = self.descendants({requirement_id})
        found = set(reqs)
        for s, t, r in self.edges:
            if s in reqs and r != "DECOMPOSES":
                found.add(t)
            if t in reqs and r != "DECOMPOSES":
                found.add(s)
        # Add systems of directly affected integrations, and artifacts attached to those integrations.
        integrations = {i for i in found if self.nodes[i].kind == "integrations"}
        for s, t, _ in self.edges:
            if s in integrations:
                found.add(t)
            if t in integrations and self.nodes[s].kind in {"incidents", "risks", "dependencies", "changes"}:
                found.add(s)
        for s, t, r in self.edges:
            if s in found and self.nodes[s].kind == "uat-scenarios" and r == "SESSION":
                found.add(t)
        return found

    def impact(self, root):
        if self.nodes[root].kind == "requirements":
            ids = self.scope(root)
        else:
            ids = {root}
            # Impact follows consumers and dependencies, but stops at containers and shared systems.
            frontier = {root}
            for _ in range(8):
                additions = set()
                for s, t, r in self.edges:
                    if s in frontier:
                        additions.add(t)
                    if t in frontier and r not in {"PLANNED_IN", "SESSION"}:
                        additions.add(s)
                additions -= ids
                ids |= additions
                frontier = {
                    i
                    for i in additions
                    if self.nodes[i].kind in {"requirements", "integrations", "test-cases", "uat-scenarios"}
                }
                if not frontier:
                    break
        items = sorted((brief(self.nodes[i]) for i in ids if i != root), key=lambda a: (a["kind"], a["key"]))
        edges = [
            {"source_id": s, "target_id": t, "relation": r} for s, t, r in self.edges if s in ids and t in ids
        ]
        return {
            "root": brief(self.nodes[root]),
            "items": items,
            "counts": dict(Counter(a["kind"] for a in items)),
            "edges": edges,
        }


def fingerprint(value):
    return hashlib.sha256(json.dumps(jsonable_encoder(value), sort_keys=True).encode()).hexdigest()


def latest_executions(db):
    result = {}
    for execution in db.scalars(select(m.TestExecution).order_by(m.TestExecution.id)):
        result[execution.test_case_id] = execution
    return result


def test_fingerprint(db, test):
    contract = {
        k: getattr(test, k)
        for k in [
            "payload",
            "scenario",
            "expected_status",
            "expected_result",
            "steps",
            "preconditions",
            "mandatory",
            "integration_id",
            "requirement_id",
        ]
    }
    requirement = db.get(m.Requirement, test.requirement_id)
    contract["acceptance_criteria"] = requirement.acceptance_criteria
    if test.integration_id:
        integration = db.get(m.Integration, test.integration_id)
        contract["integration"] = {
            k: getattr(integration, k)
            for k in [
                "endpoint",
                "method",
                "protocol",
                "mode",
                "data_format",
                "request_format",
                "response_format",
            ]
        }
        contract["mappings"] = [
            serialize(v)
            for v in db.scalars(
                select(m.FieldMapping)
                .where(m.FieldMapping.integration_id == test.integration_id)
                .order_by(m.FieldMapping.id)
            )
        ]
    return fingerprint(contract)


def execution_status(db, test, execution):
    if not execution or execution.contract_fingerprint != test_fingerprint(db, test):
        return "NOT_RUN"
    return execution.status


def uat_state(db, session_id):
    scenarios = list(db.scalars(select(m.UATScenario).where(m.UATScenario.session_id == session_id)))
    latest = {}
    for result in db.scalars(select(m.UATResult).order_by(m.UATResult.id)):
        latest[result.scenario_id] = result
    rows = [
        {
            **brief(s),
            "mandatory": s.mandatory,
            "requirement_id": s.requirement_id,
            "steps": s.steps,
            "expected_result": s.expected_result,
            "result": serialize(latest[s.id]) if s.id in latest else None,
        }
        for s in scenarios
    ]
    mandatory = [s for s in scenarios if s.mandatory]
    incomplete = [
        s.key
        for s in mandatory
        if s.id not in latest or latest[s.id].status != "PASS" or not latest[s.id].evidence.strip()
    ]
    criteria = [
        {
            "id": s.id,
            "revision": s.revision,
            "requirement": serialize(db.get(m.Requirement, s.requirement_id)),
            "result": serialize(latest[s.id]) if s.id in latest else None,
        }
        for s in scenarios
    ]
    tested_requirements = {s.requirement_id for s in scenarios}
    latest_tests = latest_executions(db)
    test_evidence = [
        {
            "id": t.id,
            "contract": test_fingerprint(db, t),
            "execution": latest_tests[t.id].id if t.id in latest_tests else None,
        }
        for t in db.scalars(select(m.TestCase).where(m.TestCase.requirement_id.in_(tested_requirements)))
    ]
    fp = fingerprint({"criteria": criteria, "test_evidence": test_evidence})
    approval = db.scalar(
        select(m.UATApproval).where(m.UATApproval.session_id == session_id).order_by(m.UATApproval.id.desc())
    )
    approved = bool(approval and approval.decision == "APPROVED" and approval.fingerprint == fp)
    return {
        "scenarios": rows,
        "incomplete": incomplete,
        "ready": bool(mandatory) and not incomplete,
        "approved": approved,
        "fingerprint": fp,
        "approval": serialize(approval) if approval else None,
        "stale_approval": bool(approval and approval.fingerprint != fp),
    }


def traceability(db, project_id):
    graph = Graph(db, project_id)
    latest = latest_executions(db)
    rows = []
    for req in sorted((a for a in graph.nodes.values() if a.kind == "requirements"), key=lambda a: a.key):
        ids = graph.scope(req.id)
        related = [graph.nodes[i] for i in ids if i != req.id]
        tests = [
            t for t in related if t.kind == "test-cases" and t.requirement_id in graph.descendants({req.id})
        ]
        states = [execution_status(db, t, latest.get(t.id)) for t in tests]
        status = next(
            (s for s in ["FAIL", "BLOCKED", "NOT_RUN"] if s in states), "PASS" if states else "NOT_RUN"
        )
        sessions = [a for a in related if a.kind == "uat"]
        approved = bool(sessions) and all(uat_state(db, s.id)["approved"] for s in sessions)
        rows.append(
            {
                **serialize(req),
                "test_status": status,
                "test_count": len(tests),
                "uat_status": "APPROVED" if approved else "PENDING",
                "parents": [
                    brief(graph.nodes[s]) for s, t, r in graph.edges if t == req.id and r == "DECOMPOSES"
                ],
                "related": [brief(a) for a in sorted(related, key=lambda a: (a.kind, a.key))],
                "tests": [
                    {**brief(t), "latest_execution": serialize(latest[t.id]) if t.id in latest else None}
                    for t in tests
                ],
            }
        )
    total = len(rows)
    with_tests = sum(r["test_count"] > 0 for r in rows)
    return {
        "rows": rows,
        "metrics": {
            "total": total,
            "with_tests": with_tests,
            "without_tests": total - with_tests,
            "passing": sum(r["test_status"] == "PASS" for r in rows),
            "failing": sum(r["test_status"] == "FAIL" for r in rows),
            "blocked": sum(r["test_status"] == "BLOCKED" for r in rows),
            "without_uat": sum(r["uat_status"] != "APPROVED" for r in rows),
            "coverage": round(100 * with_tests / total) if total else 0,
        },
    }


def release_readiness(db, release):
    graph = Graph(db, release.project_id)
    direct = {t for s, t, r in graph.edges if s == release.id and r == "CONTAINS"}
    requirements = graph.descendants({i for i in direct if graph.nodes[i].kind == "requirements"})
    changes = [graph.nodes[i] for i in direct if graph.nodes[i].kind == "changes"]
    scoped = set(requirements) | direct
    for req in requirements:
        scoped |= graph.scope(req)
    nodes = [graph.nodes[i] for i in scoped]
    tests = [a for a in nodes if a.kind == "test-cases" and a.requirement_id in requirements and a.mandatory]
    latest = latest_executions(db)
    sessions = [a for a in nodes if a.kind == "uat"]
    scenarios = [a for a in nodes if a.kind == "uat-scenarios" and a.requirement_id in requirements]
    defects = [
        a
        for a in nodes
        if a.kind == "incidents" and a.severity == "CRITICAL" and a.status not in {"RESOLVED", "CLOSED"}
    ]
    risks = [
        a
        for a in nodes
        if a.kind == "risks"
        and a.probability * a.impact >= 15
        and a.status not in {"MITIGATED", "CLOSED", "ACCEPTED"}
    ]
    dependencies = [a for a in nodes if a.kind == "dependencies" and a.status == "BLOCKED"]
    gates = []

    def gate(name, passed, detail, mandatory=True):
        gates.append(
            {
                "name": name,
                "status": "PASS" if passed else ("FAIL" if mandatory else "WARNING"),
                "mandatory": mandatory,
                "detail": detail,
            }
        )

    gate(
        "Requirements complete",
        bool(requirements) and all(graph.nodes[i].status == "COMPLETE" for i in requirements),
        f"{sum(graph.nodes[i].status == 'COMPLETE' for i in requirements)}/{len(requirements)} scoped requirements complete",
    )
    leaf_requirements = {
        i for i in requirements if not any(s == i and r == "DECOMPOSES" for s, _, r in graph.edges)
    }
    covered = {t.requirement_id for t in tests}
    gate(
        "Requirement test coverage",
        bool(leaf_requirements) and leaf_requirements <= covered,
        f"{len(leaf_requirements & covered)}/{len(leaf_requirements)} leaf requirements have mandatory tests",
    )
    states = [execution_status(db, t, latest.get(t.id)) for t in tests]
    gate(
        "Required tests executed",
        bool(tests) and all(s != "NOT_RUN" for s in states),
        f"{sum(s != 'NOT_RUN' for s in states)}/{len(tests)} mandatory tests have current contract evidence",
    )
    gate(
        "Mandatory tests passing",
        bool(tests) and all(s == "PASS" for s in states),
        f"{sum(s == 'PASS' for s in states)}/{len(tests)} latest executions pass the current contract",
    )
    uat_covered = (
        set().union(*(graph.descendants({s.requirement_id}) for s in scenarios)) if scenarios else set()
    )
    gate(
        "UAT acceptance coverage",
        bool(leaf_requirements) and leaf_requirements <= uat_covered,
        f"{len(leaf_requirements & uat_covered)}/{len(leaf_requirements)} leaf requirements have acceptance scenarios",
    )
    gate(
        "UAT approval",
        bool(scenarios) and bool(sessions) and all(uat_state(db, s.id)["approved"] for s in sessions),
        f"{sum(uat_state(db, s.id)['approved'] for s in sessions)}/{len(sessions)} sessions have current stakeholder approval",
    )
    gate(
        "Critical defects",
        not defects,
        ", ".join(a.key for a in defects) or "No open critical defects in scope",
    )
    gate(
        "Dependencies",
        not dependencies,
        ", ".join(a.key for a in dependencies) or "No blocked dependencies in scope",
    )
    gate(
        "Change validation",
        all(c.status == "COMPLETED" for c in changes),
        f"{sum(c.status == 'COMPLETED' for c in changes)}/{len(changes)} changes completed",
    )
    gate("High-risk items", not risks, ", ".join(a.key for a in risks) or "No unmitigated high risks", False)
    gate(
        "Rollback plan",
        len(release.rollback_plan.strip()) >= 20,
        "Documented"
        if len(release.rollback_plan.strip()) >= 20
        else "A substantive rollback plan is required",
    )
    gate(
        "Deployment notes",
        len(release.deployment_notes.strip()) >= 20,
        "Documented"
        if len(release.deployment_notes.strip()) >= 20
        else "Deployment instructions are required",
    )
    return {
        "status": "READY" if all(g["status"] == "PASS" for g in gates if g["mandatory"]) else "NOT READY",
        "gates": gates,
        "scope": [brief(a) for a in nodes],
        "requirements": sorted(requirements),
    }
