import { test, expect } from '@playwright/test';

// Simple end-to-end smoke test for the Concierge UI
// Assumes the frontend dev server is available at http://localhost:5173

const BASE = process.env.BASE_URL || 'http://localhost:5173';

test.describe('Concierge UI', () => {
  test('loads homepage and posts a message', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });

    // Check the landing text
    await expect(page.locator('text=Welcome to Concierge')).toBeVisible();

    // stub the API so that when the UI sends a message we immediately return
    // a minimal success payload; verify the conversation updates accordingly.
    await page.route('**/api/v1/concierge/message', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          data: { content: 'ok' },
        }),
      })
    );

    // type and send through the UI
    await page.fill('textarea', 'hello');
    await page.keyboard.press('Enter');

    // the stubbed response 'ok' should appear in the chat
    await expect(page.locator('text=ok')).toBeVisible();
  });

  test('shows error banner when API fails', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    // first simulate a 400 response (e.g. missing message field)
    await page.route('**/api/v1/concierge/message', (route) =>
      route.fulfill({ status: 400, body: 'message required' })
    );
    await page.fill('textarea', 'will be blocked');
    await page.keyboard.press('Enter');
    let banner = page.locator('role=alert');
    await expect(banner).toContainText('400');

    // now simulate a generic server error
    await page.route('**/api/v1/concierge/message', (route) =>
      route.fulfill({ status: 500, body: 'server error' })
    );
    await page.fill('textarea', 'trigger error');
    await page.keyboard.press('Enter');
    banner = page.locator('role=alert');
    await expect(banner).toContainText('500');
  });

  test('backend returns greeting for hi', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await page.fill('textarea', 'hi');
    await page.keyboard.press('Enter');
    const bubble = page.locator('[aria-label^="message-"]:visible').last();
    await expect(bubble).toContainText('Hello');
  });

  test('backend handles small talk', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await page.fill('textarea', 'how are you?');
    await page.keyboard.press('Enter');
    const bubble = page.locator('[aria-label^="message-"]:visible').last();
    await expect(bubble).not.toHaveText('');
  });

  test('navigation includes how-to and page renders', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    // confirm link is present in header
    const link = page.locator('nav >> text=How‑To');
    await expect(link).toBeVisible();
    await link.click();
    // new page should have the heading we added
    await expect(page.locator('h1')).toHaveText('How to use Concierge');
  });

  test('real backend chat returns a response', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    // send a message without stubbing to ensure backend interaction
    const message = 'integration test';

    // intercept the response so we can check it even if the UI lags
    const responsePromise = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/concierge/message') && resp.request().method() === 'POST',
      { timeout: 90000 }
    );

    await page.fill('textarea', message);
    await page.keyboard.press('Enter');

    const resp = await responsePromise;
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status).toBe('success');
    // make sure the backend actually returned something useful
    expect(body.data).toBeDefined();
  });
});
