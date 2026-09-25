// Verify the shareable assets, including direct local playback of the chapter player.
const {
  chromium,
  expect,
} = require("../frontend/node_modules/@playwright/test");
const AxeBuilder =
  require("../frontend/node_modules/@axe-core/playwright").default;
const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { createHash } = require("node:crypto");

(async () => {
  const root = path.resolve(__dirname, "..");
  const media = path.join(root, "docs/demo");
  const manifest = JSON.parse(
    await fs.readFile(path.join(media, "manifest.json"), "utf8"),
  );
  for (const artifact of manifest.artifacts) {
    const data = await fs.readFile(path.join(root, artifact.file));
    expect(data.length).toBe(artifact.bytes);
    expect(createHash("sha256").update(data).digest("hex")).toBe(
      artifact.sha256,
    );
    if (artifact.file.endsWith(".png")) {
      expect(data.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a");
      expect(data.readUInt32BE(16)).toBeGreaterThan(0);
      expect(data.readUInt32BE(20)).toBeGreaterThan(0);
    }
  }
  const browser = await chromium.launch();
  const report = {
    checkedAt: new Date().toISOString(),
    artifactHashesChecked: manifest.artifacts.length,
    errors: [],
    checks: [],
  };
  try {
    const context = await browser.newContext({
      viewport: { width: 1600, height: 1200 },
    });
    const page = await context.newPage();
    page.on("pageerror", (error) => report.errors.push(error.message));
    await page.goto(pathToFileURL(path.join(media, "index.html")).href);
    await expect
      .poll(() => page.locator("video").evaluate((video) => video.readyState))
      .toBeGreaterThanOrEqual(2);
    const video = await page.locator("video").evaluate((video) => ({
      duration: video.duration,
      width: video.videoWidth,
      height: video.videoHeight,
      error: video.error?.message || null,
    }));
    expect(video.error).toBeNull();
    expect(video.width).toBe(1600);
    expect(video.height).toBe(1000);
    expect(Math.abs(video.duration - manifest.durationSeconds)).toBeLessThan(
      0.2,
    );
    const chapter = manifest.chapters.find(
      (chapter) => chapter.title === "Correct the source mapping",
    );
    await page
      .getByRole("button", { name: /Correct the source mapping/ })
      .click();
    await expect
      .poll(() => page.locator("video").evaluate((video) => video.currentTime))
      .toBeGreaterThan(chapter.start + 0.3);
    await expect(
      page.getByRole("button", { name: /Correct the source mapping/ }),
    ).toHaveAttribute("aria-current", "true");
    await page.locator("video").evaluate((video) => video.pause());
    report.checks.push(
      "Local HTML player loads the MP4, plays it, seeks to a chapter, and highlights the active chapter.",
    );
    await page.screenshot({
      path: path.join(root, ".local/demo-player.png"),
      fullPage: true,
    });
    const accessibility = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(accessibility.violations).toEqual([]);
    report.checks.push(
      "The desktop chapter player has no automated WCAG A/AA axe violations.",
    );
    for (const href of await page
      .locator("a[href]")
      .evaluateAll((links) => links.map((link) => link.getAttribute("href")))) {
      if (!href || /^https?:/.test(href)) continue;
      await fs.access(path.resolve(media, href));
    }
    report.checks.push(
      "Every local link in the player resolves to an existing repository file.",
    );
    await page.setViewportSize({ width: 390, height: 844 });
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBe(390);
    await expect(
      page.getByRole("button", { name: /Correct the source mapping/ }),
    ).toBeVisible();
    report.checks.push("The chapter player also fits a 390px mobile viewport.");
    expect(report.errors).toEqual([]);
    report.video = video;
    await fs.writeFile(
      path.join(media, "playback-verification.json"),
      JSON.stringify(report, null, 2) + "\n",
    );
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
