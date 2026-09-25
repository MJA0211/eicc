# Verification report

Verified on September 13, 2026, America/New_York (September 14 UTC). These are observed execution results,
not estimates. The repository was initially empty; no existing application behavior was assumed.

The subsequent UI redesign and its current browser checks are documented in [UI design](ui-design.md).
The following records preserve the original implementation verification.

## Automated results

| Check                                                           | Observed result                                                                                                                          |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Python regression suite, SQLite / Windows Python 3.11.5         | **64 passed**, 0 failed, 0 skipped, 59.67 seconds                                                                                        |
| Same Python suite, PostgreSQL 17 / Linux container              | **64 passed**, 0 failed, 0 skipped, 56.18 seconds                                                                                        |
| Chromium browser suite, isolated migrated/seeded local app      | **25 passed**, 0 failed, 100.47 seconds                                                                                                  |
| Same Chromium suite, built Nginx/FastAPI/PostgreSQL Compose app | **25 passed**, 0 failed, 110.11 seconds                                                                                                  |
| Backend statement coverage, SQLite pytest run                   | **91%** (1,549 of 1,697 statements); graph, auth, models, and reports modules 100%                                                       |
| Ruff lint and format check                                      | Passed; 28 Python files formatted                                                                                                        |
| TypeScript and Vite production build                            | Passed; 1,594 modules transformed                                                                                                        |
| Python dependency audit                                         | No known vulnerabilities reported                                                                                                        |
| Frontend and repository npm audits                              | 0 vulnerabilities reported                                                                                                               |
| Actionlint 1.7.12                                               | GitHub Actions workflow passed validation                                                                                                |
| Compose configuration                                           | Passed `docker compose config --quiet`                                                                                                   |
| Compose build/start/health                                      | Frontend, backend, and PostgreSQL healthy                                                                                                |
| Database migration                                              | Upgrade → full downgrade → re-upgrade test passed; deployed database at `51d69315b352`                                                   |
| Clean authenticated setup smoke                                 | Migration, organization/admin bootstrap, disabled demo endpoint, HTTPS test-client login, empty workspace, first project creation passed |

There are **89 distinct automated tests**, run across two database/deployment configurations for **178 passing
test executions** in the final verification set. Parametrized cases are counted separately. Targeted checks and
earlier development reruns are not added to that total. The 24 seeded protocol executions are application demo
records, not additional pytest or Playwright test cases.

After the final integration-metric currency correction, both complete backend suites passed again and a
focused dashboard/view/export browser check passed against the rebuilt Compose application (1 test, 4.4 seconds).
That extra check is not added to the 178-execution total. Final health requests returned HTTP 200 for Docker,
the local API, and the local frontend. Northstar was restored to its intended starting scenario; the separate
browser-created governance project remains available in the Docker workspace.

The final browser result summaries and SQLite case-level results are retained in
[`verification-results.json`](verification-results.json). Local raw JUnit and coverage output are in ignored
`.local/`; Playwright retains its report and JSON in ignored frontend test-output directories.

## Primary workflow proved

The full API workflow creates its own persisted scope:

1. Create project, business requirement, functional child, technical child, and decomposition links.
2. Create source/target systems, a SOAP integration, an intentionally incorrect mapping, test plan, and test.
3. Execute the actual local protocol request and retain the failure and linked defect.
4. Assign and investigate the defect, correct the mapping, execute a passing retest, resolve and close the defect.
5. Complete the requirements through authorized states and record UAT scenario evidence and stakeholder approval.
6. Record change scope and impact, obtain approval, validate, and complete the change.
7. Create release scope and plans, satisfy every mandatory gate, and progress through completed release.
8. Inspect traceability and generated reports; alter acceptance criteria and verify approval becomes stale.

Browser tests separately prove authoring and persisted editing, SOAP failure/investigation/mapping correction/
retest, file upload, UAT decision, impact recording, change approval, release gates and transitions, search,
filtering, document export, all navigation pages, keyboard access, dashboard axe checks, and mobile containment.
No browser route mocks are used.

## Deployment verification

Docker Engine 29.1.3 and Compose 2.40.3 run in Ubuntu 24.04 under WSL. The application was built from the delivered
Dockerfiles and served through the Nginx production frontend at `http://127.0.0.1:8080`. The browser suite used
that URL and the persistent PostgreSQL database. The Python suite used isolated PostgreSQL schemas that were
removed after each test, preserving demonstration data.

Local Windows startup also passed using the provided helper, with frontend `http://127.0.0.1:5173` and API
`http://127.0.0.1:8000`. The reset regression verified that Northstar is reconstructed with actual execution
evidence while a separately created project and audit history survive.

CI contains backend, browser, and deployment jobs with mandatory failure propagation. Actionlint validates
the workflow. These jobs' substantive commands were exercised locally; **GitHub-hosted CI has not run**, because
the repository has not been pushed.

## Visual evidence

The screenshots are captured from the running application. Desktop overview, evidence, traceability, release
gates, and mobile navigation were inspected during verification.

| View                                   | Screenshot                                             |
| -------------------------------------- | ------------------------------------------------------ |
| Live dashboard                         | [Dashboard](screenshots/dashboard.png)                 |
| Request, response, and retest evidence | [Execution](screenshots/execution-evidence.png)        |
| Requirement coverage and links         | [Traceability](screenshots/traceability.png)           |
| Intentionally blocked pilot            | [Release readiness](screenshots/release-readiness.png) |
| Stakeholder acceptance                 | [UAT approval](screenshots/uat-approval.png)           |
| Browser-created completed release      | [Completed release](screenshots/completed-release.png) |
| 390-pixel responsive layout            | [Mobile](screenshots/mobile.png)                       |

## Verification limits and tool warnings

Pytest reports two dependency deprecation warnings concerning Starlette's HTTPX test-client integration and
an AnyIO alias. Playwright reports an environment color-setting warning. The WSL Compose install warns that
Buildx is absent and completes builds using its available Docker builder. These warnings did not cause skipped
checks or ignored failures.

The axe check covers the dashboard, not a full accessibility certification. Browser automation uses Chromium,
not every browser engine. Coverage is statement coverage from pytest; browser-driven backend coverage and
container startup are not included in the percentage. No external penetration test, load test, production
failover, malware scan, or disaster-recovery certification was performed. Dependency audit results describe
the advisories known at verification time.

## Git and delivery state

```text
Branch: main
Commit: none created
Working tree: new implementation files, uncommitted
Tests: 64 backend + 25 browser; passing in both verified configurations
Build: TypeScript/Vite and Docker images passed
Docker: healthy frontend, backend, PostgreSQL; loopback port 8080
Known limitations: fictional portfolio; bounded local simulations; no external enterprise deployment or hosted CI run
```

No remote push, release, package publication, history rewrite, or credential commit was performed.
