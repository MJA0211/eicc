# EICC engineering delivery report

## Delivered architecture

A React 19 / TypeScript analyst workspace connects to a FastAPI/Pydantic backend, SQLAlchemy joined-table
domain model, and explicit Alembic migrations. PostgreSQL 17 runs in Docker Compose; SQLite supports local
development and isolated tests. The interface includes responsive navigation, project selection, search,
filters, dark mode, schema-driven authoring dialogs, detail views, evidence panels, and calculated dashboards.

## Business analysis and traceability

The fictional Northstar project includes stakeholder and process analysis, business/functional/technical/
non-functional requirements, review and approval, acceptance criteria, and typed artifact relationships.
Coverage rolls up decomposed requirements. Traceability and impact views query persisted relationships and
foreign keys, connecting intent to interfaces, tests, acceptance, defects, changes, documents, and releases.

## Integrations and testing

Seven integrations document REST/JSON and SOAP/XML contracts. Local HTTP simulators provide persisted case
creation/retrieval, idempotency, notification acceptance, XML validation, controlled errors, and timeout.
Mappings use bounded transformations. Executions retain actual request/response evidence and a contract
fingerprint, so changing a contract requires a fresh test. Evidence supports authenticated file attachments.

The automated suite contains **64 backend tests and 25 Chromium browser tests**. The backend suite passes on
both SQLite and PostgreSQL. Browser verification covers an isolated local server and the built Compose app.
Exact run results, coverage, commands, screenshots, and test boundaries are in [verification](verification.md).

## UAT and incident management

UAT sessions contain requirement-linked scenarios, actual results, evidence, stakeholder decisions, comments,
and explicit override reasons. Approval currency is checked against the current acceptance definition and
test evidence. Defects originate from failed executions and retain assignment, investigation, root cause,
resolution, retest, closure, and audit history. Linked failures require a current passing retest before resolution.

## Change and release management

Changes require a current recorded impact assessment and management approval. Impact traverses stored scope
with boundaries around shared systems and delivery containers. Completing a change requires current passing
validation for affected tests.

Release readiness evaluates **11 mandatory checks and one risk advisory**: completed requirements, leaf test
coverage, current execution, passing mandatory tests, leaf UAT coverage, current approval, critical defects,
dependencies, completed changes, rollback instructions, deployment instructions, and high-scoring open risks.
Mandatory failures block Ready, Deployed, and Completed transitions. These transitions record fictional
delivery decisions; they do not deploy software to an external environment.

## Security and deployment

Implemented controls include Argon2 passwords, opaque expiring/revocable sessions, CSRF and origin checks,
server-side roles, optimistic revision checks, strict input validation, database constraints, safe XML,
bounded attachment validation, fixed local simulator routes, audit events, and security headers. Non-demo
startup requires secure cookies; private administrator bootstrap and additional account provisioning are
documented and verified. Demo role selection is explicitly an exploration feature.

The production frontend build passes. Compose builds and starts healthy frontend, backend, and PostgreSQL
containers, with the application reachable at `http://127.0.0.1:8080`. Local helpers start the SQLite-backed
workspace at `http://127.0.0.1:5173`. Both use the delivered source. CI configuration passes Actionlint;
the corresponding build/test/deployment commands were executed locally. No remote CI run is claimed.

## Documentation and portfolio value

Delivered documentation includes setup, architecture, domain and process diagrams, the demonstration guide,
capability-to-test traceability, security and operations, contribution guidance, this engineering report,
the verification report, and a fictional portfolio case study. The app also generates eight versioned document
types from persisted records and exports their immutable Markdown content.

The project demonstrates requirements analysis, interface specification, mapping, protocol troubleshooting,
test management, evidence handling, UAT coordination, defect investigation, impact analysis, change approval,
release governance, technical writing, and reproducible software delivery.

## Limits and repository state

Northstar and stakeholder acceptance are fictional. No government affiliation, enterprise adoption, real
production integration, external notification delivery, or measured business savings is claimed. OAuth2/mTLS
are contract design metadata; the local simulator uses EICC sessions. Queue acceptance is simulated without
an external worker. This is not a certified, highly available, multitenant production platform.

Branch: `main`. Commit: none created. Working tree: new implementation files remain uncommitted. No push,
release, package publication, or remote configuration change was performed. Private configuration, databases,
logs, and dependency/build directories are excluded from Git. Known non-failing tool warnings and verification
scope are recorded in the verification report.
