# Portfolio case study: Northstar integration modernization

## Context and disclosure

Northstar Enterprise Services, its staff, its case workflow, and its release decisions are fictional. This is
an independently built portfolio demonstration. It is not affiliated with the Maryland Judiciary, another
government organization, or an enterprise customer. The results below describe implemented and tested software,
not employment experience, stakeholder research conducted with real users, or measured organizational savings.

## Business problem

The scenario starts with manual case intake, repeated data entry into a legacy records system, manual document
association, and inconsistent status notifications. A change to the case identifier can affect the legacy
interface, downstream messages, reporting, test evidence, and a release decision. Separate spreadsheets make
those relationships difficult to inspect.

The analyst objective is to retain the business reason for a change while making its technical consequences
reviewable. EICC connects that reason to requirements, contracts, test results, defects, acceptance evidence,
and delivery controls in one persisted workspace.

## Stakeholders and elicitation artifacts

The fictional stakeholder register represents the business sponsor, case operations, integration engineering,
quality assurance, and release governance. Each stakeholder has a role, department, contact placeholder, and
project association. Requirement sources and acceptance criteria record the assumed workshop outcomes; they
are illustrative inputs, not transcripts of interviews that actually occurred.

Current-state and future-state process descriptions explain where re-entry occurs and how validated intake,
legacy record creation, document association, notifications, and reporting should proceed. The process view
provides the business context alongside the technical catalog.

## Requirements analysis

The Northstar baseline includes 8 business, 12 functional, 8 technical, and 4 non-functional requirements.
Business intent decomposes into functional behavior and testable technical obligations through explicit
relationships. Requirements retain source, priority, owner, acceptance criteria, status, and revision history.

For example, timely status notification becomes a functional requirement to dispatch after a status change,
then a technical requirement to map a string case identifier and recipient into the notification contract.
Requirements move through review, approval, implementation, and completion. A manager must authorize approval.
The API rejects missing acceptance criteria, cyclic decomposition, cross-project references, stale edits,
and attempts to assign workflow status through ordinary editing.

## Interface analysis and mapping

Seven systems and seven integrations document the application landscape. The catalog distinguishes REST/JSON
from SOAP/XML, synchronous from asynchronous interactions, and design authentication metadata from local
simulator authorization. Each contract includes source and target systems, method or action, payload shape,
field mappings, validation, and related requirements.

The legacy SOAP example deliberately sends an integer identifier where the service requires `xsd:string`.
The analyst can inspect the actual XML fault, identify the mapping defect, apply a string conversion, and
retain the corrected request and successful retest. A separate partner example maps `status` to an incorrect
field, demonstrating that transport success and payload correctness are different questions.

The simulators execute locally. An asynchronous response means the simulator accepted a message; it does not
prove delivery through an external queue or mail provider.

## Test management and defect investigation

Test plans group executable cases. Each case records its requirement, integration, steps, payload, expected
result, severity, mandatory flag, and scenario. Executions retain request, response, status, actual result,
duration, actor, timestamp, and a fingerprint of the tested contract. Manual cases require written evidence.
Optional files provide supporting screenshots or documents with an integrity digest.

The seeded 24 protocol cases produce actual local responses, including controlled authentication, timeout,
schema, mapping, and downstream-service failures. A failed execution can create a linked defect. Assignment,
investigation, root cause, resolution, retest, closure, and reopening are represented in the incident workflow.
The server prevents resolution without a subsequent passing result for the current contract.

This preserves the failed evidence after a fix. Changing the mapping cannot rewrite the original request or
silently turn an earlier failure into a pass.

## UAT coordination

Acceptance sessions contain scenarios linked to requirements, expected outcomes, actual results, comments,
and supporting evidence. A decision identifies both the represented stakeholder and authenticated actor.
Ordinary approval requires all mandatory scenarios to pass. Incomplete acceptance can only be approved with
an explicit, substantive override reason, which remains visible in the decision history.

Approval is tied to an acceptance fingerprint. Changed criteria, relevant contracts, or test evidence make an
earlier decision stale. The release gate therefore checks acceptance of the current scope, rather than merely
the presence of an old approval record.

## Risk, dependency, and change control

Risks retain probability, impact, calculated score, mitigation, ownership, and status. Dependencies identify
their source and target artifacts and whether the dependency is open, blocked, or satisfied. Those relationships
feed impact analysis and readiness.

A change request records its reason, expected benefit, implementation and rollback plans, and affected scope.
Impact analysis follows stored graph edges and typed foreign keys into requirements, interfaces, tests, UAT,
risks, dependencies, documents, and releases. Shared systems and release containers stop further expansion to
avoid treating every connected artifact as affected by every change.

Approval requires a recorded assessment that still matches the current scope. A manager approves the change;
completion requires validation evidence for its affected tests.

## Release governance and documentation

A release contains explicit requirements and changes. Live gates check completed scope, leaf-level test and
UAT coverage, current passing executions, current stakeholder approval, critical defects, blocked dependencies,
completed changes, and substantive deployment and rollback instructions. High-scoring open risks produce an
advisory. The server rechecks gates at Ready, Deployed, and Completed transitions.

The fictional historical release has a narrow verified scope. The pilot remains blocked by its unresolved
conditions. A separate automated workflow constructs a fresh scope and proves the entire path through failure,
correction, UAT, change approval, and completed release.

Eight generated document types turn current records into versioned Markdown snapshots: BRD, FRD, integration
specification, test plan, UAT plan, release notes, training guide, and status report. Review status and version
history remain distinct from the underlying source records.

## Implementation results

The deliverable is a running React/FastAPI application with SQLAlchemy, Alembic, PostgreSQL deployment, a SQLite
development mode, Docker Compose, CI configuration, and automated verification. Exact execution counts, build
results, screenshots, and environment details appear in [the verification report](verification.md).

The demonstrated result is that the analyst can follow and validate the full lifecycle using actual persisted
application data. No monetary savings, reduced processing time, production adoption, or real enterprise
acceptance is asserted.

## Lessons and practical limits

Evidence must be bound to the contract it tested. Otherwise an edited mapping can leave a misleading green
release gate. Acceptance needs similar invalidation when criteria or evidence change. Coverage must be checked
at requirement leaves; one passing test on a broad parent is insufficient. Impact traversal needs boundaries
around shared systems to avoid overwhelming the analyst with unrelated scope.

The application demonstrates business analysis and integration governance, not production multitenancy,
high availability, SSO, regulatory certification, external messaging, or deployment automation. Its bounded
local simulations make the failure and recovery paths reproducible and inspectable.
