import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

test("stakeholder evidence, attachments, change approval and release readiness through the browser", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Explore as").selectOption("admin");
  await page.getByRole("button", { name: "Enter demo workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Project overview" }),
  ).toBeVisible();
  const session = await (await page.request.get("/api/auth/me")).json();
  const headers = { "X-CSRF-Token": session.csrf_token };
  const prefix = `GOV-${Date.now()}`;
  async function post(path: string, data: any = {}) {
    const response = await page.request.post(`/api/${path}`, { data, headers });
    expect(response.ok(), await response.text()).toBeTruthy();
    return response.json();
  }
  const project = await post("projects", {
    key: prefix,
    title: "Browser governance demonstration",
  });
  const p = { project_id: project.id };
  const requirement = await post("requirements", {
    ...p,
    key: `${prefix}-REQ`,
    title: "Notify the case owner with the original identifier",
    type: "TECHNICAL",
    acceptance_criteria:
      "A local notification returns the original string case identifier.",
  });
  const source = await post("systems", {
    ...p,
    key: `${prefix}-SRC`,
    title: "Demonstration intake",
  });
  const target = await post("systems", {
    ...p,
    key: `${prefix}-TGT`,
    title: "Demonstration notifications",
  });
  const integration = await post("integrations", {
    ...p,
    key: `${prefix}-API`,
    title: "Demonstration notification contract",
    source_system_id: source.id,
    target_system_id: target.id,
  });
  await post("links", {
    source_id: requirement.id,
    target_id: integration.id,
    relation: "AFFECTS",
  });
  const plan = await post("test-plans", {
    ...p,
    key: `${prefix}-PLAN`,
    title: "Browser qualification plan",
    scope: "Validate notification response schema",
  });
  const testCase = await post("test-cases", {
    ...p,
    key: `${prefix}-TEST`,
    title: "Verify string case identifier",
    test_plan_id: plan.id,
    requirement_id: requirement.id,
    integration_id: integration.id,
  });
  const execution = await post(`test-cases/${testCase.id}/execute`);
  expect(execution.status).toBe("PASS");
  for (const status of ["IN_REVIEW", "APPROVED", "IMPLEMENTING", "COMPLETE"])
    await post(`requirements/${requirement.id}/transition`, { status });
  const stakeholder = await post("stakeholders", {
    ...p,
    key: `${prefix}-OWNER`,
    title: "Fictional business owner",
  });
  const uat = await post("uat", {
    ...p,
    key: `${prefix}-UAT`,
    title: "Notification acceptance session",
  });
  await post("uat-scenarios", {
    ...p,
    key: `${prefix}-SCENARIO`,
    title: "Case operator verifies the notification",
    session_id: uat.id,
    requirement_id: requirement.id,
    steps: "Submit a case and inspect the local notification response.",
    expected_result: "The response contains the original string identifier.",
  });
  const change = await post("changes", {
    ...p,
    key: `${prefix}-CHANGE`,
    title: "Approve notification delivery",
    reason: "Deliver the verified notification contract",
  });
  await post("links", {
    source_id: change.id,
    target_id: requirement.id,
    relation: "AFFECTS",
  });
  const release = await post("releases", {
    ...p,
    key: `${prefix}-RELEASE`,
    title: "Browser verified release",
    version: "1.0.0",
    deployment_notes:
      "Apply the approved mapping version and run the saved qualification payload.",
    rollback_plan:
      "Restore the previous approved mapping revision and reconcile pending notifications.",
  });
  await post("links", {
    source_id: release.id,
    target_id: requirement.id,
    relation: "CONTAINS",
  });
  await post("links", {
    source_id: release.id,
    target_id: change.id,
    relation: "CONTAINS",
  });
  await page.reload();
  await page.getByLabel("Active project").selectOption(String(project.id));

  async function move(page: Page, status: string) {
    await page
      .getByRole("button", { name: "Update status", exact: true })
      .click();
    await page
      .getByRole("dialog")
      .getByLabel("Status", { exact: false })
      .selectOption(status);
    await page.getByRole("button", { name: "Apply transition" }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
  }
  await page.goto(`/uat/${uat.id}`);
  await move(page, "READY");
  await move(page, "IN_PROGRESS");
  await page
    .getByRole("button", { name: "Record result", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByLabel("Status", { exact: false })
    .selectOption("PASS");
  await page
    .getByRole("dialog")
    .getByLabel("Evidence", { exact: false })
    .fill(
      `Fictional browser demonstration: local execution ${execution.id} preserved the case identifier.`,
    );
  await page.getByRole("button", { name: "Save evidence" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByLabel("Attach evidence file").setInputFiles({
    name: "acceptance.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(
      "Fictional browser acceptance evidence: original case identifier verified.",
    ),
  });
  await expect(
    page.getByRole("link").filter({ hasText: "acceptance.txt" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Record decision", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByLabel("Represented stakeholder")
    .selectOption(String(stakeholder.id));
  await page
    .getByRole("dialog")
    .getByLabel("Comments")
    .fill(
      "Fictional stakeholder approves the demonstrated local acceptance criteria.",
    );
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Record decision", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator(".approval-record")).toContainText("Approved");
  await page.screenshot({
    path: test.info().outputPath("uat-approval.png"),
    fullPage: true,
  });

  await page.goto(`/changes/${change.id}`);
  await move(page, "SUBMITTED");
  await move(page, "ANALYSIS");
  await page.getByRole("button", { name: "Record impact analysis" }).click();
  await expect(
    page.getByText(
      "The recorded analysis matches the current affected artifacts.",
    ),
  ).toBeVisible();
  for (const status of [
    "PENDING_APPROVAL",
    "APPROVED",
    "IMPLEMENTING",
    "VALIDATION",
    "COMPLETED",
  ])
    await move(page, status);
  await page.goto(`/releases/${release.id}`);
  await expect(
    page.getByText(
      "All mandatory criteria pass. The release is eligible for an authorized transition.",
    ),
  ).toBeVisible();
  for (const status of ["PLANNED", "READY", "DEPLOYED", "COMPLETED"])
    await move(page, status);
  await expect(page.locator(".page-heading")).toContainText("Completed");
  await page.screenshot({
    path: test.info().outputPath("completed-release.png"),
    fullPage: true,
  });
  const readiness = await (
    await page.request.get(`/api/releases/${release.id}/readiness`)
  ).json();
  expect(readiness.status).toBe("READY");
});
