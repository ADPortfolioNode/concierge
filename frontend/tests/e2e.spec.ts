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
    // intercept the concierge API and force a 500 error
    await page.route('**/api/v1/concierge/message', (route) =>
      route.fulfill({ status: 500, body: 'server error' })
    );
    // type a message and send
    await page.fill('textarea', 'trigger error');
    await page.keyboard.press('Enter');
    // expect error banner to appear
    const banner = page.locator('role=alert');
    // banner should contain the HTTP status code or a generic error message
    await expect(banner).toContainText('500');
  });
});
