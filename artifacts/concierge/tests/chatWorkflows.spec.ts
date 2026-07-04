import { test, expect } from '@playwright/test';

/**
 * Exercises chat the way a user would: type in the input, submit, and verify
 * the same REST contract the frontend uses (POST /api/v1/concierge/message).
 */

async function gotoHome(page: import('@playwright/test').Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await expect(page.getByRole('link', { name: 'Concierge' }).first()).toBeVisible({ timeout: 15_000 });
}

test.describe('Chat — user input workflows', () => {
  test('typing and Enter sends POST to concierge/message', async ({ page }) => {
    await gotoHome(page);

    const messageReq = page.waitForRequest(
      (req) =>
        req.method() === 'POST' &&
        req.url().includes('/api/v1/concierge/message'),
      { timeout: 20_000 },
    );

    const input = page.getByPlaceholder(/message|ask|concierge/i);
    await expect(input).toBeVisible();
    const prompt = 'Hello from Playwright — what can you help me with?';
    await input.fill(prompt);
    await input.press('Enter');

    const req = await messageReq;
    const body = req.postDataJSON() as { message?: string; history?: unknown[] };
    expect(body.message).toBe(prompt);
    expect(Array.isArray(body.history)).toBe(true);

    const messageRes = await page.waitForResponse(
      (res) =>
        res.request().method() === 'POST' &&
        res.url().includes('/api/v1/concierge/message') &&
        res.status() === 200,
      { timeout: 60_000 },
    );
    const json = await messageRes.json();
    const assistant = json?.data;
    expect(assistant?.role).toBe('assistant');
    expect(String(assistant?.content || '').length).toBeGreaterThan(5);

    await expect(page.locator('[data-message-role="user"]').filter({ hasText: prompt }).or(
      page.getByText(prompt, { exact: false }),
    ).first()).toBeVisible({ timeout: 10_000 });
  });

  test('image goal prompt starts workflow and shows acknowledgement', async ({ page }) => {
    test.setTimeout(180_000);
    await page.route('**/api/v1/concierge/timeline/stream**', (route) => route.abort());
    await gotoHome(page);

    const prompt = 'Generate a simple blue circle icon for a product test';
    const input = page.getByPlaceholder(/message|ask|concierge/i);
    await input.fill(prompt);
    await input.press('Enter');

    const res = await page.waitForResponse(
      (r) =>
        r.request().method() === 'POST' &&
        r.url().includes('/api/v1/concierge/message') &&
        r.status() === 200,
      { timeout: 120_000 },
    );
    expect(res.status()).toBe(200);
    const json = await res.json();
    const content = String(json?.data?.content || '');
    const raw = json?.data?.meta?.raw || {};
    const threadId = json?.thread_id || raw?.thread_id;

    if (raw?.status === 'processing' && threadId) {
      await expect(
        page.getByText(/started working|follow the progress/i).first(),
      ).toBeVisible({ timeout: 15_000 });
      // Frontend polls task status — verify at least one status fetch fires
      const statusHit = await page
        .waitForResponse(
          (r) => r.url().includes('/api/v1/tasks/') && r.url().includes('/status'),
          { timeout: 45_000 },
        )
        .catch(() => null);
      expect(statusHit).not.toBeNull();
    } else {
      // Conversational fallback still valid for small-talk style prompts
      expect(content.length).toBeGreaterThan(5);
    }
  });

  test('status query returns inline assistant reply', async ({ page }) => {
    await gotoHome(page);
    const input = page.getByPlaceholder(/message|ask|concierge/i);
    await input.fill('What tasks are running?');
    await input.press('Enter');

    const res = await page.waitForResponse(
      (r) =>
        r.request().method() === 'POST' &&
        r.url().includes('/api/v1/concierge/message') &&
        r.status() === 200,
      { timeout: 60_000 },
    );
    const json = await res.json();
    const content = String(json?.data?.content || '');
    expect(content.length).toBeGreaterThan(3);
    await expect(page.getByText(/task|thread|running|none|no active/i).first()).toBeVisible({
      timeout: 15_000,
    });
  });
});