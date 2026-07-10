import { test, expect } from "@playwright/test";

const API_URL = "http://localhost:8000";
const CONCURRENT_REQUESTS = 20;

test("handles 20+ simultaneous ticket creation requests", async ({ request }) => {
  const runId = Date.now();

  const requests = Array.from({ length: CONCURRENT_REQUESTS }, (_, i) =>
    request.post(`${API_URL}/tickets`, {
      data: {
        customer_id: `concurrent-${runId}-${i}`,
        customer_email: `concurrent-${runId}-${i}@example.com`,
        customer_name: `Concurrent Tester ${i}`,
        subject: `Concurrent request test ${i}`,
        description: "Created as part of a concurrency end-to-end test scenario.",
      },
    })
  );

  const responses = await Promise.all(requests);

  for (const response of responses) {
    expect(response.status()).toBe(201);
  }

  const bodies = await Promise.all(responses.map((r) => r.json()));
  const uniqueIds = new Set(bodies.map((b) => b.id));
  expect(uniqueIds.size).toBe(CONCURRENT_REQUESTS);
});
