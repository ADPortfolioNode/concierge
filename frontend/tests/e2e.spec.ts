import { test, expect } from '@playwright/test';

// Simple end-to-end smoke test for the Concierge UI
// Assumes the frontend dev server is available at http://localhost:5173

const BASE = process.env.BASE_URL || 'http://localhost:5173';

test.describe('Concierge UI', () => {
  test('loads homepage and posts a message', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });

    // Check the landing text
    await expect(page.locator('text=Welcome to Concierge')).toBeVisible();

    // POST to the API and return raw response details so Playwright can surface
    // status codes, headers and body without assuming JSON.
    const result = await page.evaluate(async () => {
      const res = await fetch('/api/v1/concierge/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'playwright-test' }),
      });
      return {
        status: res.status,
        headers: Object.fromEntries(res.headers.entries()),
        text: await res.text(),
      };
    });

    // dump what we got to help debug failures
    console.log('E2E raw response:', result);

    expect(result.status).toBeGreaterThanOrEqual(200);
    expect(result.status).toBeLessThan(600);

    // if we received a text body try parsing it, but fail if it isn't valid JSON
    let parsed: any;
    try {
      parsed = result.text ? JSON.parse(result.text) : null;
    } catch (err) {
      throw new Error(`Failed to parse response text as JSON: ${err} -- body='${result.text}'`);
    }

    if (parsed && typeof parsed === 'object') {
      expect(parsed).toHaveProperty('status');
      expect(parsed).toHaveProperty('data');
      const payload = parsed.data;
      if (payload && typeof payload === 'object') {
        const content = payload.content || payload.text || null;
        expect(content).not.toBeNull();
      }
    } else {
      throw new Error('API returned empty or non-JSON response');
    }
  });
});
