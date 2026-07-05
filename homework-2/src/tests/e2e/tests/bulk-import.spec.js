import path from "node:path";
import { fileURLToPath } from "node:url";
import { test, expect } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SAMPLE_CSV = path.resolve(__dirname, "../../fixtures/sample_tickets.csv");

test("bulk import from CSV with auto-classification verification", async ({ page }) => {
  await page.goto("/import");

  await page.setInputFiles('input[type="file"]', SAMPLE_CSV);
  await page.getByLabel("Auto-classify every imported ticket").check();
  await page.getByRole("button", { name: "Import Tickets" }).click();

  await expect(page.getByRole("heading", { name: "Import Summary" })).toBeVisible();
  await expect(page.getByText(/Total: 50.*Successful: 50.*Failed: 0/)).toBeVisible();

  // sample_tickets.csv is deterministically generated (seeded), so cust-0002's
  // "Credit card billing issue" content reliably classifies as billing_question.
  await page.goto("/");
  await page.getByLabel("Customer ID").fill("cust-0002");

  await page.getByRole("link", { name: /Credit card billing issue/ }).click();
  await expect(page.getByText("Billing Question", { exact: true }).first()).toBeVisible();
  const confidenceRow = page
    .locator("dt", { hasText: "Classification Confidence" })
    .locator("xpath=following-sibling::dd[1]");
  await expect(confidenceRow).not.toHaveText("—");
});
