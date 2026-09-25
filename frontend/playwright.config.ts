import { defineConfig, devices } from "@playwright/test";

const external = process.env.EICC_BASE_URL;
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 90000,
  expect: { timeout: 15000 },
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ["list"],
    ["html", { open: "never" }],
    ["json", { outputFile: "test-results/results.json" }],
  ],
  use: {
    baseURL: external || "http://127.0.0.1:4173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 1100 },
      },
    },
  ],
  webServer: external
    ? undefined
    : [
        {
          command: "uv run python -m scripts.e2e_server",
          cwd: "..",
          url: "http://127.0.0.1:8001/api/health",
          timeout: 120000,
          reuseExistingServer: false,
        },
        {
          command: "npm run dev -- --port 4173",
          url: "http://127.0.0.1:4173",
          env: { EICC_API_URL: "http://127.0.0.1:8001" },
          timeout: 60000,
          reuseExistingServer: false,
        },
      ],
});
