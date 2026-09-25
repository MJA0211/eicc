# Recorded walkthrough

A captioned recording of real browser interactions with the redesigned EICC application. The video is silent; the captions explain each chapter. All organizations and approvals are fictional. The release transitions record a local demonstration and do not deploy external software.

[Play or download the MP4](eicc-walkthrough.mp4) · [Chapter player](index.html) · [Screenshot gallery](../screenshots/README.md)

The opening tour uses seeded Northstar data. The qualification then uses a separate project whose test, defect, UAT, change, and release outcomes are created during the recording. Its definitions and reviewed requirements are prepared through the validated API before filming.

## Chapters

### 00:00 — Welcome to EICC

A recorded walkthrough of the redesigned app. All organizations, records, and approvals are fictional.

### 00:05 — Project overview

Coverage, test results, and release readiness are calculated from persisted Northstar records.

### 00:17 — Dark theme

The same workspace, with a dark slate palette and accessible semantic status colors.

### 00:22 — Requirements and traceability

Business needs connect to functional and technical requirements, integrations, tests, and release scope.

### 00:35 — Integration catalog

Inspect system boundaries, REST and SOAP contracts, mappings, and connected delivery evidence.

### 00:40 — Explainable release gates

The Northstar pilot remains blocked. Every failed gate identifies the evidence or work still required.

### 00:48 — Run a real SOAP test

In a separate qualification project, submit integer case ID 42 to a contract that requires an XML string.

### 00:53 — Inspect the failure

The captured request sends xsd:int. The local SOAP service rejects it because case_id must be xsd:string.

### 01:00 — Investigate a linked defect

Create the defect from the failed execution, then record the root cause and the intended correction.

### 01:11 — Correct the source mapping

Change the case_id transformation from identity to to_string. The test payload remains the integer 42.

### 01:24 — Retest and retain the evidence

The corrected mapping sends xsd:string and returns HTTP 200. The earlier failure remains in execution history.

### 01:38 — Close the evidence loop

Resolution requires investigation details and a later passing retest against the current contract.

### 01:42 — Complete the linked requirements

Complete the reviewed business, functional, and technical requirements after the contract has passed qualification.

### 01:53 — Record acceptance evidence

The case operator verifies the current SOAP result and attaches the retained request and response.

### 02:07 — Record stakeholder sign-off

Approval identifies both the represented fictional stakeholder and the authenticated demo actor.

### 02:15 — Assess and approve the change

Record impact from stored relationships before approval; validation checks the current passing test evidence.

### 02:42 — Verify every release gate

Requirements, current tests, acceptance, defects, change validation, deployment notes, and rollback all satisfy the gates.

### 02:51 — Complete the fictional release

Authorized transitions record Planned, Ready, Deployed, and Completed. This does not deploy external software.

### 03:08 — Generate the delivery document

Release notes are a versioned snapshot generated from the project's stored scope, deployment plan, and readiness.

### 03:16 — A connected delivery record

The business-to-technical chain now has passing tests, accepted UAT, a closed defect, and a completed release.
