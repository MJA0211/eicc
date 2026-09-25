import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function login(page: Page, role = "admin") {
  await page.goto("/");
  await page.getByLabel("Explore as").selectOption(role);
  await page.getByRole("button", { name: "Enter demo workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Project overview" }),
  ).toBeVisible();
}

test("dashboard uses live metrics, changes views and exports a stored report", async ({
  page,
}) => {
  await login(page);
  await expect(page.getByText("Requirements coverage")).toBeVisible();
  await expect(
    page.getByText("Not Ready", { exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Analyst view" }).click();
  await expect(
    page.getByRole("heading", { name: "Analyst quality metrics" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Executive view" }).click();
  await page.screenshot({
    path: test.info().outputPath("dashboard.png"),
    fullPage: true,
  });
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export report" }).click();
  expect((await downloaded).suggestedFilename()).toMatch(/^DOC-.*\.md$/);
});

for (const [path, heading] of [
  ["projects", "Projects"],
  ["requirements", "Requirements"],
  ["traceability", "Traceability matrix"],
  ["systems", "Systems"],
  ["integrations", "Integration catalog"],
  ["test-cases", "Test management"],
  ["test-plans", "Test plans"],
  ["uat", "User acceptance testing"],
  ["uat-scenarios", "UAT scenarios"],
  ["incidents", "Incidents & defects"],
  ["changes", "Change requests"],
  ["risks", "Risk register"],
  ["dependencies", "Dependencies"],
  ["releases", "Releases"],
  ["reports", "Project reports"],
  ["training", "Training library"],
  ["processes", "Process design"],
  ["administration", "Administration"],
]) {
  test(`renders ${path} from the real API`, async ({ page }) => {
    await login(page);
    await page.goto(`/${path}`);
    await expect(
      page.getByRole("heading", { name: heading, exact: true }).first(),
    ).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
  });
}

test("requirement authoring, filtering, persisted editing and global search", async ({
  page,
}) => {
  await login(page);
  await page.goto("/requirements");
  await page
    .getByRole("button", { name: "New requirement", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Key", { exact: false }).fill("BROWSER-REQ");
  await dialog
    .getByLabel("Title", { exact: false })
    .fill("Browser-created notification requirement");
  await dialog
    .getByLabel("Acceptance Criteria")
    .fill("A case notification preserves the original case identifier.");
  await dialog.getByRole("button", { name: "Create record" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Browser-created notification requirement",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit record", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByLabel("Title", { exact: false })
    .fill("Browser-verified notification requirement");
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "Browser-verified notification requirement",
      exact: true,
    }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", {
      name: "Browser-verified notification requirement",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByLabel("Search workspace").fill("BROWSER-REQ");
  await expect(
    page
      .getByRole("region", { name: "Search results" })
      .getByText("Browser-verified notification requirement"),
  ).toBeVisible();
});

test("SOAP failure, defect, mapping correction and passing retest are visible", async ({
  page,
}) => {
  await login(page);
  const workspace = await (await page.request.get("/api/workspace")).json();
  const find = (key: string) => workspace.items.find((a: any) => a.key === key);
  const testCase = find("INT-002"),
    integration = find("CASE-API-001");
  await page.goto(`/test-cases/${testCase.id}`);
  await page.getByRole("button", { name: "Run test", exact: true }).click();
  await expect(
    page.getByText("Test executed. Request and response evidence saved."),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Execution evidence" }).click();
  await expect(
    page.getByText("Captured response", { exact: false }).first(),
  ).toBeVisible();
  await expect(
    page.locator("pre").filter({ hasText: "case_id must be xsd:string" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Create defect", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: /Failed: Legacy integer identifier/ }),
  ).toBeVisible();
  const defectUrl = page.url();
  async function move(status: string) {
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
  await move("ASSIGNED");
  await move("IN_PROGRESS");
  await page.getByRole("button", { name: "Edit record" }).click();
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
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.goto(`/integrations/${integration.id}`);
  await page.getByRole("tab", { name: "Field mappings" }).click();
  await page
    .getByRole("row")
    .filter({ hasText: "case_id" })
    .getByRole("button", { name: "Edit mapping" })
    .click();
  await page
    .getByRole("dialog")
    .getByLabel("Transformation")
    .selectOption("to_string");
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.goto(`/test-cases/${testCase.id}`);
  await page.getByRole("button", { name: "Run test", exact: true }).click();
  await expect(
    page.getByText(
      "Expected HTTP 200; received HTTP 200. Response schema valid.",
      { exact: true },
    ),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Execution evidence" }).click();
  await expect(
    page.locator("pre").filter({ hasText: "CreateCaseResponse" }),
  ).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath("execution-evidence.png"),
    fullPage: true,
  });
  await page.goto(defectUrl);
  await move("RESOLVED");
  await page.getByRole("tab", { name: "Timeline" }).click();
  await expect(
    page.getByRole("heading", { name: "Incident timeline" }),
  ).toBeVisible();
  await expect(
    page.getByRole("tabpanel").getByText("Resolved", { exact: true }),
  ).toBeVisible();
});

test("traceability filters and release gates are explainable", async ({
  page,
}) => {
  await login(page);
  await page.goto("/traceability");
  await page.getByLabel("Filter requirement").fill("BR-001");
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(2);
  await expect(
    page.getByRole("table").getByText("BR-001", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath("traceability.png"),
    fullPage: true,
  });
  await page.goto("/releases");
  await page.getByRole("link").filter({ hasText: "REL-002" }).first().click();
  await expect(
    page.getByRole("heading", { name: "Release readiness gate" }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "This release cannot proceed until every mandatory criterion passes.",
    ),
  ).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath("release-readiness.png"),
    fullPage: true,
  });
});

test("keyboard access, dark mode and dashboard accessibility", async ({
  page,
}) => {
  await login(page);
  await page.keyboard.press("Control+k");
  await expect(page.getByLabel("Search workspace")).toBeFocused();
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("link", { name: "Skip to content" }).focus();
  const darkResults = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(darkResults.violations).toEqual([]);
  await page.getByRole("button", { name: "Switch to light mode" }).focus();
  await page.screenshot({
    path: test.info().outputPath("dashboard-dark.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Switch to light mode" }).click();
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(results.violations).toEqual([]);
});

test("mobile navigation stays within the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(
    page.getByRole("button", { name: "Open navigation" }),
  ).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Open navigation" }),
  ).toHaveAttribute("aria-expanded", "false");
  await expect(page.locator("#workspace-navigation")).toHaveAttribute(
    "inert",
    "",
  );
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page
    .getByRole("link", { name: "Requirements", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Requirements", exact: true }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
  await page.screenshot({
    path: test.info().outputPath("mobile.png"),
    fullPage: false,
    animations: "disabled",
  });
});
