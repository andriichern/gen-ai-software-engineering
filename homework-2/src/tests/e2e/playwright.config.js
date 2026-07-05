import { defineConfig } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const srcDir = path.resolve(__dirname, "../../"); // parent of api/, required cwd for `api.main:app` to resolve
const apiDir = path.resolve(__dirname, "../../api");
const appDir = path.resolve(__dirname, "../../app");

export default defineConfig({
  testDir: "./tests",
  // The backend is one shared, persistent process across the whole run (no
  // reset-between-tests endpoint), so keep execution serial to avoid
  // cross-test interference in that shared in-memory store.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `${path.join(apiDir, ".venv", "bin", "python")} -m uvicorn api.main:app --port 8000`,
      cwd: srcDir,
      url: "http://localhost:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: "npm run dev",
      cwd: appDir,
      url: "http://localhost:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
  projects: [
    {
      name: "desktop",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 800 },
      },
    },
    {
      name: "mobile",
      use: {
        browserName: "chromium",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
      // Functional specs are viewport-agnostic and only need to run once (desktop);
      // only the responsive-layout spec needs the mobile viewport too.
      testMatch: /responsive-layout\.spec\.js/,
    },
  ],
});
