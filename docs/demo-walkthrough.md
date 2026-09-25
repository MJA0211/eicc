# Demonstration guide

[Watch the captioned recording](demo/eicc-walkthrough.mp4) · [Recorded chapters and transcript](demo/transcript.md) · [New layout screenshots](screenshots/README.md)

All records and stakeholder decisions in this guide are fictional. Use a demo administrator to walk through
all role-gated actions, or switch between Analyst, Stakeholder, and Manager in Administration to demonstrate
the authorization boundaries.

## Five-minute orientation

1. Open the Dashboard. Note that coverage, pass rate, critical defects, and readiness are calculated from stored data.
2. Open Requirements → **BR-001**. Its acceptance criteria express the need to notify users after a case status change.
3. Open Traceability. Filter `BR-001` and inspect the functional/technical descendants, notification interface, tests,
   acceptance session, defects, changes, and planned release.
4. Open Integrations → **NOTIFY-API-002**. Inspect source/target systems, JSON contracts, and field mappings.
5. Open Releases → **REL-002**. Read each failed gate. Open **REL-001** to compare the completed fictional baseline.

## Investigate and permanently correct the SOAP mismatch

1. Open Testing → **INT-002**. Run the test and open **Execution evidence**.
2. Inspect the XML request: the integer case ID is sent with `xsi:type="xsd:int"`. The local legacy service returns
   a SOAP validation fault because it requires `xsd:string`.
3. Select **Create defect**. The defect retains the failed execution and links to the requirement, test, and integration.
4. Move the defect to Assigned, then In Progress. Edit its root cause and resolution:
   - Root cause: the source identifier was forwarded without the required string conversion.
   - Resolution: convert `case_id` to a string in the mapping and verify the corrected contract.
5. Open **CASE-API-001 → Field mappings**. Edit the `case_id` row and select `to_string`.
6. Return to **INT-002** and run it again. Inspect the new XML request and successful response. The failed execution
   remains in history. Optionally attach a text, PDF, or image evidence file.
7. Return to the defect. Resolve and close it. The server checks for both investigation details and a later passing
   execution against the current contract. The timeline records the retest and resolution.

The mapping is corrected at its source. Editing the defect text alone cannot make the test pass. Other failing
tests and defects remain visible until individually addressed; resolving this one issue cannot make the pilot ready.

## REST notification scenario

**INT-001** intentionally requests the controlled `unauthorized` fixture and expects a successful notification.
Its failure is real within the simulator. Create a defect and inspect the 401 response. After documenting the
fictional authentication correction, edit the test scenario to `success`, run again, inspect the JSON response,
and resolve the defect after its passing retest. This demonstrates analysis of an authentication failure, not a
claim to have implemented or contacted a real OAuth provider.

**PARTNER-API-006** contains an incorrect `status → case_status` mapping. Correct the target field to `status`
and rerun the affected tests. Input quality and contract mapping are separately visible in the captured payload.

## Acceptance and delivery

1. Create a focused project or use the existing scope. Create a business requirement, functional child, and technical
   child. Use **Add relationship → Decomposes** from each parent.
2. Create source and target systems and a local integration. Link the technical requirement to the integration with
   Affects. Create mappings, a test plan, and an integration test case referencing the technical requirement.
3. Run the test; investigate failures and obtain a current pass. Complete the requirement hierarchy through the allowed
   review, approval, implementation, and completion transitions. Manager authority is required for approval.
4. Create a UAT session and a scenario linked to each leaf requirement. Move the session to Ready, then In Progress.
   Read the acceptance criteria, record results and evidence, and attach supporting files.
5. As a Stakeholder or Manager, select **Record decision**, choose the represented stakeholder, and approve or reject.
   Incomplete mandatory evidence blocks ordinary approval. A recorded override is visible as an explicit decision.
6. Create a change and link affected requirements/integrations. Submit it, move to Analysis, and select **Record impact
   analysis**. Review affected tests, UAT, risks, dependencies, documents, and releases. Request and obtain approval.
7. Implement, validate, and complete the change. The server checks affected tests before completion.
8. Create a release, add the business requirement and change with **Contains**, and write deployment and rollback
   instructions. Resolve critical defects and blocked dependencies in scope.
9. Open **Readiness**. Every mandatory gate must pass. As a Manager, transition Planned → Ready → Deployed → Completed.
10. Generate Release Notes and a Project Status Report under Reports. Export the stored Markdown snapshots.

`tests/test_workflow.py` automates the complete chain, including the initial failure and permanent correction.
`frontend/e2e/governance.spec.ts` executes acceptance, file evidence, impact analysis, approval, and release
transitions through the browser against the real backend.

## Reset

Administration → Reset Demo Data requires the Admin role and the exact confirmation `RESET NORTHSTAR DEMO`.
Only the Northstar project is replaced. Other projects and the audit log are retained. Reset reruns the 24 actual
local tests, so the starting dashboard again shows the intentional failures and completed baseline.
