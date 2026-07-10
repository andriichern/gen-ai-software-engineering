import { test, expect } from "@playwright/test";

test("complete ticket lifecycle: create, auto-classify, resolve, delete", async ({ page }) => {
  const runId = Date.now();
  const subject = `Cannot access account ${runId}`;

  await page.goto("/tickets/new");
  await page.getByLabel("Customer ID").fill(`lifecycle-${runId}`);
  await page.getByLabel("Customer Email").fill(`lifecycle-${runId}@example.com`);
  await page.getByLabel("Customer Name").fill("Lifecycle Tester");
  await page.getByLabel("Subject").fill(subject);
  await page
    .getByLabel("Description")
    .fill("I forgot my password and cannot log in to my account at all.");
  await page.getByRole("button", { name: "Create Ticket" }).click();

  // Created tickets navigate to their detail page.
  await expect(page.getByRole("heading", { name: subject })).toBeVisible();

  // Trigger auto-classification and verify the result is displayed.
  await page.getByRole("button", { name: "Trigger Auto-Classify" }).click();
  await expect(page.getByText(/Confidence: \d+%/)).toBeVisible();
  await expect(page.getByText("Account Access", { exact: true }).first()).toBeVisible();

  // Edit: move the ticket to resolved and confirm resolved_at now populates.
  await page.getByRole("link", { name: "Edit" }).click();
  await page.getByLabel("Status").selectOption("resolved");
  await page.getByRole("button", { name: "Save Changes" }).click();

  await expect(page.getByRole("heading", { name: subject })).toBeVisible();
  const resolvedRow = page.locator("dt", { hasText: "Resolved" }).locator("xpath=following-sibling::dd[1]");
  await expect(resolvedRow).not.toHaveText("—");

  // Delete and confirm we land back on the list without the ticket.
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Delete" }).click();

  await expect(page).toHaveURL("/");
  await expect(page.getByText(subject)).toHaveCount(0);
});
