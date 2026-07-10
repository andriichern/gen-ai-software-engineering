import { test, expect } from "@playwright/test";

const API_URL = "http://localhost:8000";

test("combined filtering by category and priority", async ({ page, request }) => {
  const runId = Date.now();
  const target = {
    customer_id: `filter-target-${runId}`,
    customer_email: `filter-target-${runId}@example.com`,
    customer_name: "Filter Target",
    subject: `Billing question high priority ${runId}`,
    description: "Placeholder description text for the filtering scenario.",
    category: "billing_question",
    priority: "high",
  };
  const decoy = {
    ...target,
    customer_id: `filter-decoy-${runId}`,
    subject: `Billing question low priority ${runId}`,
    priority: "low",
  };

  for (const payload of [target, decoy]) {
    const response = await request.post(`${API_URL}/tickets`, { data: payload });
    expect(response.status()).toBe(201);
  }

  await page.goto("/");
  await page.getByLabel("Category").selectOption("billing_question");
  await page.getByLabel("Priority").selectOption("high");
  await page.getByLabel("Customer ID").fill(`filter-target-${runId}`);

  await expect(page.getByText(target.subject)).toBeVisible();
  await expect(page.getByText(decoy.subject)).toHaveCount(0);
});
