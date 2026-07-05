import { test, expect } from "@playwright/test";

const API_URL = "http://localhost:8000";

test("ticket list adapts its layout to the viewport", async ({ page, request }) => {
  const runId = Date.now();
  await request.post(`${API_URL}/tickets`, {
    data: {
      customer_id: `responsive-${runId}`,
      customer_email: `responsive-${runId}@example.com`,
      customer_name: "Responsive Tester",
      subject: `Responsive layout check ${runId}`,
      description: "Ticket seeded purely to guarantee a row exists for this layout test.",
    },
  });

  await page.goto("/");
  const firstRow = page.locator(".ticket-row").first();
  await expect(firstRow).toBeVisible();

  const viewport = page.viewportSize();
  const isNarrow = viewport.width <= 720;

  const gridColumns = await firstRow.evaluate((el) => getComputedStyle(el).gridTemplateColumns);
  const columnCount = gridColumns.trim().split(/\s+/).length;

  if (isNarrow) {
    expect(columnCount).toBe(1);
  } else {
    expect(columnCount).toBeGreaterThan(1);
  }

  // No horizontal overflow at either breakpoint.
  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  );
  expect(hasHorizontalOverflow).toBe(false);

  // Nav stays usable (wraps rather than overflowing) at every width.
  await expect(page.getByRole("link", { name: "Tickets" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Categories" })).toBeVisible();
});
