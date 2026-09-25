import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const docs = path.resolve("../docs");
const shots = path.join(docs, "screenshots");
const media = path.join(docs, "demo");
const raw = path.resolve("../.local/demo-raw");

test("capture the redesigned workspace and a verified business-to-release demonstration", async ({
  browser,
  page: setup,
}) => {
  await Promise.all([
    mkdir(shots, { recursive: true }),
    mkdir(media, { recursive: true }),
    mkdir(raw, { recursive: true }),
  ]);
  const screenshots: {
    file: string;
    title: string;
    width: number;
    height: number;
    fullPage: boolean;
  }[] = [];
  const errors: string[] = [];
  const checks: string[] = [];
  async function settle(page: Page) {
    await page.evaluate(() => document.fonts.ready);
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await page.waitForTimeout(300);
    const dismiss = page.getByRole("button", { name: "Dismiss notification" });
    if (await dismiss.isVisible()) await dismiss.click();
  }
  async function screenshot(
    page: Page,
    file: string,
    title: string,
    fullPage = false,
  ) {
    await settle(page);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    await page.mouse.move(1590, 8);
    await page.screenshot({
      path: path.join(shots, `${file}.png`),
      fullPage,
      animations: "disabled",
    });
    const size = await page.evaluate(
      (full) => ({
        width: innerWidth,
        height: full
          ? Math.max(innerHeight, document.documentElement.scrollHeight)
          : innerHeight,
      }),
      fullPage,
    );
    screenshots.push({ file: `${file}.png`, title, ...size, fullPage });
  }
  async function login(page: Page) {
    await page.goto("/");
    await page.getByLabel("Explore as").selectOption("admin");
    await page.getByRole("button", { name: "Enter demo workspace" }).click();
    await expect(
      page.getByRole("heading", { name: "Project overview", exact: true }),
    ).toBeVisible();
  }
  await login(setup);
  const session = await (await setup.request.get("/api/auth/me")).json();
  const headers = { "X-CSRF-Token": session.csrf_token };
  async function post(route: string, data: Record<string, unknown> = {}) {
    const response = await setup.request.post(`/api/${route}`, {
      data,
      headers,
    });
    expect(response.ok(), await response.text()).toBeTruthy();
    return response.json();
  }
  const workspace = await (await setup.request.get("/api/workspace")).json();
  const pilot = workspace.items.find(
    (item: { key: string }) => item.key === "REL-002",
  );

  // Definitions are authored through the same validated API as the app. No outcomes
  // are seeded for this project: every test and decision below is recorded on camera.
  const project = await post("projects", {
    key: "DEMO-CASE",
    title: "Legacy case identifier correction",
    description:
      "Fictional recorded qualification of the local legacy case contract.",
    start_date: "2026-09-01",
    target_date: "2026-09-30",
  });
  const p = { project_id: project.id };
  const requirements = [];
  for (const [key, type, title] of [
    ["DEMO-BR", "BUSINESS", "Keep case identity consistent across systems"],
    ["DEMO-FR", "FUNCTIONAL", "Create a legacy case from an intake submission"],
    [
      "DEMO-TR",
      "TECHNICAL",
      "Serialize the legacy case identifier as a string",
    ],
  ]) {
    const requirement = await post("requirements", {
      ...p,
      key,
      type,
      title,
      acceptance_criteria:
        "The local CreateCase SOAP response returns the original identifier 42 as an XML string, with HTTP 200 and no validation fault.",
    });
    if (requirements.length)
      await post("links", {
        source_id: requirements.at(-1).id,
        target_id: requirement.id,
        relation: "DECOMPOSES",
      });
    requirements.push(requirement);
    for (const status of ["IN_REVIEW", "APPROVED", "IMPLEMENTING"])
      await post(`requirements/${requirement.id}/transition`, { status });
  }
  const source = await post("systems", {
    ...p,
    key: "DEMO-INTAKE",
    title: "Case Intake",
    technology: "REST / JSON",
  });
  const target = await post("systems", {
    ...p,
    key: "DEMO-LEGACY",
    title: "Legacy Records",
    technology: "SOAP / XML",
  });
  const integration = await post("integrations", {
    ...p,
    key: "DEMO-CASE-API",
    title: "Create a legacy case",
    source_system_id: source.id,
    target_system_id: target.id,
    protocol: "SOAP",
    endpoint: "/simulator/soap",
    method: "CreateCase",
    data_format: "XML",
    authentication_type: "Local demo session",
    request_format:
      "SOAP 1.1 CreateCase: case_id must have xsi:type=xsd:string.",
    response_format:
      "HTTP 200, CreateCaseResponse with the original string case_id.",
  });
  await post("links", {
    source_id: requirements[2].id,
    target_id: integration.id,
    relation: "AFFECTS",
  });
  for (const field of ["case_id", "status", "recipient"])
    await post(`integrations/${integration.id}/mappings`, {
      source_field: field,
      target_field: field,
      transformation: "identity",
    });
  const plan = await post("test-plans", {
    ...p,
    key: "DEMO-PLAN",
    title: "Legacy contract qualification",
    scope:
      "Verify identifier serialization and retain the SOAP request and response.",
  });
  const testCase = await post("test-cases", {
    ...p,
    key: "DEMO-TEST",
    title: "Preserve the legacy case identifier",
    test_plan_id: plan.id,
    requirement_id: requirements[2].id,
    integration_id: integration.id,
    payload: {
      case_id: 42,
      status: "ACCEPTED",
      recipient: "case.owner@example.test",
    },
    expected_status: 200,
    priority: "CRITICAL",
    expected_result: "HTTP 200 with case_id 42 serialized as xsd:string.",
  });
  const stakeholder = await post("stakeholders", {
    ...p,
    key: "DEMO-OWNER",
    title: "Fictional case operations owner",
    role: "Business acceptance owner",
  });
  const uat = await post("uat", {
    ...p,
    key: "DEMO-UAT",
    title: "Case identity acceptance",
  });
  await post("uat-scenarios", {
    ...p,
    key: "DEMO-SCENARIO",
    title: "Case operator verifies the legacy identifier",
    session_id: uat.id,
    requirement_id: requirements[2].id,
    steps: "Submit case 42 and inspect the retained local SOAP response.",
    expected_result:
      "The response preserves identifier 42 as an XML string without a validation fault.",
  });
  const change = await post("changes", {
    ...p,
    key: "DEMO-CHANGE",
    title: "Approve the identifier mapping correction",
    reason:
      "Correct integer-to-string serialization at the integration boundary.",
  });
  await post("links", {
    source_id: change.id,
    target_id: requirements[2].id,
    relation: "AFFECTS",
  });
  const release = await post("releases", {
    ...p,
    key: "DEMO-REL",
    title: "Legacy case mapping release",
    version: "1.0.0",
    deployment_notes:
      "Apply the approved to_string mapping and run the saved case 42 qualification payload. Retain current UAT approval.",
    rollback_plan:
      "Restore the previous mapping revision, suspend case submission, and reconcile pending case identifiers before resuming.",
  });
  for (const artifact of [requirements[0], change])
    await post("links", {
      source_id: release.id,
      target_id: artifact.id,
      relation: "CONTAINS",
    });

  const context = await browser.newContext({
    baseURL: "http://127.0.0.1:4173",
    viewport: { width: 1600, height: 900 },
    recordVideo: { dir: raw, size: { width: 1600, height: 900 } },
    locale: "en-US",
    timezoneId: "America/New_York",
    reducedMotion: "reduce",
    colorScheme: "light",
  });
  const started = Date.now();
  const page = await context.newPage();
  page.on("pageerror", (error) => errors.push(error.message));
  const chapters: { start: number; title: string; caption: string }[] = [];
  function chapter(title: string, caption: string) {
    chapters.push({ start: (Date.now() - started) / 1000, title, caption });
    console.log(`DEMO ${title}`);
  }
  const pause = (milliseconds = 3500) => page.waitForTimeout(milliseconds);
  async function click(locator: Locator) {
    await locator.scrollIntoViewIfNeeded();
    const box = await locator.boundingBox();
    if (box)
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, {
        steps: 12,
      });
    await page.waitForTimeout(350);
    await locator.click();
  }
  async function visit(route: string, title?: string) {
    await page.goto(route);
    if (title)
      await expect(
        page.getByRole("heading", { name: title, exact: true }).first(),
      ).toBeVisible();
    await settle(page);
  }
  async function move(status: string) {
    await click(
      page.getByRole("button", { name: "Update status", exact: true }),
    );
    await page
      .getByRole("dialog")
      .getByLabel("Status", { exact: false })
      .selectOption(status);
    await pause(650);
    await click(page.getByRole("button", { name: "Apply transition" }));
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await pause(700);
  }
  try {
    await page.goto("/");
    await expect(page.getByLabel("Explore as")).toBeVisible();
    await page.getByLabel("Explore as").selectOption("admin");
    chapter(
      "Welcome to EICC",
      "A recorded walkthrough of the redesigned app. All organizations, records, and approvals are fictional.",
    );
    await screenshot(page, "login", "Demo sign-in");
    await pause();
    await click(page.getByRole("button", { name: "Enter demo workspace" }));
    await expect(
      page.getByRole("heading", { name: "Project overview", exact: true }),
    ).toBeVisible();
    chapter(
      "Project overview",
      "Coverage, test results, and release readiness are calculated from persisted Northstar records.",
    );
    await screenshot(page, "dashboard", "Project overview");
    await screenshot(page, "dashboard-full", "Complete project overview", true);
    await pause(4500);
    await page.mouse.wheel(0, 590);
    await pause(4500);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
    await pause(700);
    await click(page.getByRole("button", { name: "Switch to dark mode" }));
    chapter(
      "Dark theme",
      "The same workspace, with a dark slate palette and accessible semantic status colors.",
    );
    await screenshot(page, "dashboard-dark", "Project overview in dark mode");
    await pause();
    await click(page.getByRole("button", { name: "Switch to light mode" }));
    await visit("/requirements", "Requirements");
    chapter(
      "Requirements and traceability",
      "Business needs connect to functional and technical requirements, integrations, tests, and release scope.",
    );
    await screenshot(page, "requirements", "Requirements register");
    await pause();
    await visit("/traceability", "Traceability matrix");
    await page.getByLabel("Filter requirement").fill("BR-001");
    await pause(1500);
    await screenshot(page, "traceability", "Filtered traceability matrix");
    await pause(4500);
    await visit("/integrations", "Integration catalog");
    chapter(
      "Integration catalog",
      "Inspect system boundaries, REST and SOAP contracts, mappings, and connected delivery evidence.",
    );
    await screenshot(page, "integrations", "Integration catalog");
    await pause();
    await visit(`/releases/${pilot.id}`);
    await expect(
      page.getByText(
        "This release cannot proceed until every mandatory criterion passes.",
      ),
    ).toBeVisible();
    chapter(
      "Explainable release gates",
      "The Northstar pilot remains blocked. Every failed gate identifies the evidence or work still required.",
    );
    await screenshot(
      page,
      "release-readiness",
      "Blocked pilot release gates",
      true,
    );
    await pause();
    await page.mouse.wheel(0, 440);
    await pause();

    await page.getByLabel("Active project").selectOption(String(project.id));
    await visit(`/test-cases/${testCase.id}`);
    chapter(
      "Run a real SOAP test",
      "In a separate qualification project, submit integer case ID 42 to a contract that requires an XML string.",
    );
    await pause();
    await click(page.getByRole("button", { name: "Run test", exact: true }));
    await expect(
      page.getByText("Test executed. Request and response evidence saved."),
    ).toBeVisible();
    await click(page.getByRole("tab", { name: "Execution evidence" }));
    await expect(
      page.locator("pre").filter({ hasText: "case_id must be xsd:string" }),
    ).toBeVisible();
    checks.push(
      "SOAP request failed with a captured string-type validation fault.",
    );
    chapter(
      "Inspect the failure",
      "The captured request sends xsd:int. The local SOAP service rejects it because case_id must be xsd:string.",
    );
    await screenshot(
      page,
      "execution-failure",
      "Captured SOAP validation fault",
      true,
    );
    await pause(5500);
    await click(
      page.getByRole("button", { name: "Create defect", exact: true }),
    );
    await expect(
      page.getByRole("heading", {
        name: /Failed: Preserve the legacy case identifier/,
      }),
    ).toBeVisible();
    const defectUrl = page.url();
    chapter(
      "Investigate a linked defect",
      "Create the defect from the failed execution, then record the root cause and the intended correction.",
    );
    await move("ASSIGNED");
    await move("IN_PROGRESS");
    await click(page.getByRole("button", { name: "Edit record", exact: true }));
    await page
      .getByRole("dialog")
      .getByLabel("Root Cause")
      .fill(
        "Integer identifier was forwarded without the required string conversion.",
      );
    await page
      .getByRole("dialog")
      .getByLabel("Resolution", { exact: true })
      .fill(
        "Apply to_string to case_id and confirm a passing local SOAP retest.",
      );
    await pause(2200);
    await click(
      page.getByRole("button", { name: "Save changes", exact: true }),
    );
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await visit(`/integrations/${integration.id}`);
    await click(page.getByRole("tab", { name: "Field mappings" }));
    chapter(
      "Correct the source mapping",
      "Change the case_id transformation from identity to to_string. The test payload remains the integer 42.",
    );
    await pause(2500);
    await click(
      page
        .getByRole("row")
        .filter({ hasText: "case_id" })
        .getByRole("button", { name: "Edit mapping" }),
    );
    await page
      .getByRole("dialog")
      .getByLabel("Transformation")
      .selectOption("to_string");
    await pause(2500);
    await click(
      page.getByRole("button", { name: "Save changes", exact: true }),
    );
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await screenshot(
      page,
      "field-mappings",
      "Corrected source-to-target mapping",
    );
    await pause();
    await visit(`/test-cases/${testCase.id}`);
    await click(page.getByRole("button", { name: "Run test", exact: true }));
    await expect(
      page.getByText(
        "Expected HTTP 200; received HTTP 200. Response schema valid.",
        { exact: true },
      ),
    ).toBeVisible();
    await click(page.getByRole("tab", { name: "Execution evidence" }));
    await expect(
      page.locator("pre").filter({ hasText: "CreateCaseResponse" }),
    ).toBeVisible();
    const record = await (
      await page.request.get(`/api/test-cases/${testCase.id}`)
    ).json();
    const execution = record.executions[0];
    expect(record.payload.case_id).toBe(42);
    expect(
      record.executions.map((item: { status: string }) => item.status),
    ).toEqual(["PASS", "FAIL"]);
    expect(execution.request_body).toContain('xsi:type="xsd:string"');
    checks.push(
      "The unchanged integer payload passed after mapping correction; both executions remain in history.",
    );
    chapter(
      "Retest and retain the evidence",
      "The corrected mapping sends xsd:string and returns HTTP 200. The earlier failure remains in execution history.",
    );
    await screenshot(
      page,
      "execution-evidence",
      "Passing SOAP request and response",
      true,
    );
    await page.mouse.wheel(0, 260);
    await pause(6500);
    await visit(defectUrl);
    await move("RESOLVED");
    await move("CLOSED");
    await click(page.getByRole("tab", { name: "Timeline" }));
    await expect(
      page.getByRole("heading", { name: "Incident timeline" }),
    ).toBeVisible();
    chapter(
      "Close the evidence loop",
      "Resolution requires investigation details and a later passing retest against the current contract.",
    );
    await screenshot(
      page,
      "incident-timeline",
      "Resolved defect and investigation timeline",
      true,
    );
    await pause();

    chapter(
      "Complete the linked requirements",
      "Complete the reviewed business, functional, and technical requirements after the contract has passed qualification.",
    );
    for (const requirement of requirements) {
      await visit(`/requirements/${requirement.id}`);
      await move("COMPLETE");
    }
    await visit(`/uat/${uat.id}`);
    chapter(
      "Record acceptance evidence",
      "The case operator verifies the current SOAP result and attaches the retained request and response.",
    );
    await move("READY");
    await move("IN_PROGRESS");
    await click(
      page.getByRole("button", { name: "Record result", exact: true }),
    );
    await page
      .getByRole("dialog")
      .getByLabel("Status", { exact: false })
      .selectOption("PASS");
    await page
      .getByRole("dialog")
      .getByLabel("Evidence", { exact: false })
      .fill(
        `Fictional demonstration: local execution ${execution.id} returned HTTP 200 and preserved case identifier 42 as xsd:string.`,
      );
    await pause(2000);
    await click(
      page.getByRole("button", { name: "Save evidence", exact: true }),
    );
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await page.getByLabel("Attach evidence file").setInputFiles({
      name: "case-42-acceptance.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(
        `Fictional local demonstration\nExecution ${execution.id}\nHTTP ${execution.response_status}\n\nRequest\n${execution.request_body}\n\nResponse\n${execution.response_body}\n`,
      ),
    });
    await expect(
      page.getByRole("link").filter({ hasText: "case-42-acceptance.txt" }),
    ).toBeVisible();
    await move("PASSED");
    await click(
      page.getByRole("button", { name: "Record decision", exact: true }),
    );
    await page
      .getByRole("dialog")
      .getByLabel("Represented stakeholder")
      .selectOption(String(stakeholder.id));
    await page
      .getByRole("dialog")
      .getByLabel("Comments")
      .fill(
        "Fictional business owner accepts the current case identity criteria, supported by the retained SOAP execution and attachment.",
      );
    chapter(
      "Record stakeholder sign-off",
      "Approval identifies both the represented fictional stakeholder and the authenticated demo actor.",
    );
    await pause(3000);
    await click(
      page
        .getByRole("dialog")
        .getByRole("button", { name: "Record decision", exact: true }),
    );
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.locator(".approval-record")).toContainText("Approved");
    await screenshot(
      page,
      "uat-approval",
      "Stakeholder acceptance and attached evidence",
      true,
    );
    checks.push(
      "UAT passed, an actual execution attachment was uploaded, and stakeholder approval was recorded.",
    );
    await pause();

    await visit(`/changes/${change.id}`);
    chapter(
      "Assess and approve the change",
      "Record impact from stored relationships before approval; validation checks the current passing test evidence.",
    );
    await move("SUBMITTED");
    await move("ANALYSIS");
    await click(
      page.getByRole("button", { name: "Record impact analysis", exact: true }),
    );
    await expect(
      page.getByText(
        "The recorded analysis matches the current affected artifacts.",
      ),
    ).toBeVisible();
    await screenshot(page, "change-impact", "Current change impact assessment");
    await pause();
    for (const status of [
      "PENDING_APPROVAL",
      "APPROVED",
      "IMPLEMENTING",
      "VALIDATION",
      "COMPLETED",
    ])
      await move(status);
    await visit(`/releases/${release.id}`);
    await expect(
      page.getByText(
        "All mandatory criteria pass. The release is eligible for an authorized transition.",
      ),
    ).toBeVisible();
    chapter(
      "Verify every release gate",
      "Requirements, current tests, acceptance, defects, change validation, deployment notes, and rollback all satisfy the gates.",
    );
    await screenshot(
      page,
      "release-ready",
      "All mandatory release gates passing",
      true,
    );
    await pause(4000);
    await page.mouse.wheel(0, 550);
    await pause(4500);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
    await pause(500);
    chapter(
      "Complete the fictional release",
      "Authorized transitions record Planned, Ready, Deployed, and Completed. This does not deploy external software.",
    );
    for (const status of ["PLANNED", "READY", "DEPLOYED", "COMPLETED"])
      await move(status);
    await expect(page.locator(".page-heading")).toContainText("Completed");
    await screenshot(
      page,
      "completed-release",
      "Completed release with verified gates",
      true,
    );
    const readiness = await (
      await page.request.get(`/api/releases/${release.id}/readiness`)
    ).json();
    expect(readiness.status).toBe("READY");
    expect(
      readiness.gates
        .filter(
          (gate: { mandatory: boolean; status: string }) => gate.mandatory,
        )
        .every((gate: { status: string }) => gate.status === "PASS"),
    ).toBeTruthy();
    checks.push(
      "The change and release completed through authorized UI transitions; every mandatory release gate passed.",
    );
    await pause();
    await visit("/reports", "Project reports");
    chapter(
      "Generate the delivery document",
      "Release notes are a versioned snapshot generated from the project's stored scope, deployment plan, and readiness.",
    );
    await screenshot(page, "reports", "Project report generator");
    await click(
      page
        .locator(".report-card")
        .filter({
          has: page.getByRole("heading", {
            name: "Release Notes",
            exact: true,
          }),
        })
        .getByRole("button", { name: "Generate document" }),
    );
    await expect(
      page.getByText("Versioned document generated from project data"),
    ).toBeVisible();
    await screenshot(page, "release-notes", "Generated release notes");
    checks.push("Release notes were generated from persisted project data.");
    await pause(5000);
    await visit("/traceability", "Traceability matrix");
    chapter(
      "A connected delivery record",
      "The business-to-technical chain now has passing tests, accepted UAT, a closed defect, and a completed release.",
    );
    await screenshot(
      page,
      "traceability-complete",
      "Completed delivery traceability",
    );
    await pause(6500);
    expect(errors).toEqual([]);
  } finally {
    await context.close();
  }
  await page.video()!.saveAs(path.join(raw, "walkthrough.webm"));

  // Mobile stills use a separate context so the desktop recording stays consistent.
  const mobile = await browser.newContext({
    baseURL: "http://127.0.0.1:4173",
    viewport: { width: 390, height: 844 },
    isMobile: true,
    deviceScaleFactor: 1,
    hasTouch: true,
    locale: "en-US",
    reducedMotion: "reduce",
  });
  const phone = await mobile.newPage();
  await login(phone);
  await screenshot(phone, "dashboard-mobile", "Mobile project overview");
  await phone.getByRole("button", { name: "Open navigation" }).click();
  await screenshot(phone, "mobile-navigation", "Mobile navigation drawer");
  await phone.getByRole("link", { name: "Requirements", exact: true }).click();
  await expect(
    phone.getByRole("heading", { name: "Requirements", exact: true }),
  ).toBeVisible();
  await screenshot(phone, "mobile", "Mobile requirements register");
  expect(await phone.evaluate(() => document.documentElement.scrollWidth)).toBe(
    390,
  );
  checks.push(
    "Mobile requirements fit the 390px viewport without document overflow.",
  );
  await mobile.close();
  await writeFile(
    path.join(media, "capture.json"),
    JSON.stringify(
      {
        capturedAt: new Date().toISOString(),
        source:
          "Disposable seeded SQLite database; real FastAPI HTTP simulator and browser interactions; no API mocking.",
        viewport: { width: 1600, height: 900 },
        trimStart: chapters[0].start,
        chapters,
        screenshots,
        checks,
        browserErrors: errors,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(
    `Saved ${screenshots.length} screenshots and ${chapters.length} video chapters.`,
  );
});
