import { defineConfig } from "@playwright/test";

// Recording always uses a disposable database, never EICC_BASE_URL or live data.
export default defineConfig({
  testDir: "./demo",
  workers: 1,
  retries: 0,
  timeout: 600000,
  expect: { timeout: 15000 },
  outputDir: "../.local/demo-results",
  reporter: [["list"], ["json", { outputFile: "../.local/demo-results.json" }]],
  use: {
    baseURL: "http://127.0.0.1:4173",
    viewport: { width: 1600, height: 900 },
    locale: "en-US",
    timezoneId: "America/New_York",
    colorScheme: "light",
    reducedMotion: "reduce",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
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
