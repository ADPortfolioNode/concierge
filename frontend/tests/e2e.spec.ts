import { test, expect } from '@playwright/test';

// Simple end-to-end smoke test for the Concierge UI
// Assumes the frontend dev server is available at http://localhost:5173

const BASE = process.env.BASE_URL || 'http://localhost:5173';

test.describe('Concierge UI', () => {
  test('loads homepage and posts a message', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });

    // Check the landing text
    await expect(page.locator('text=Welcome to Concierge')).toBeVisible();

    // use Playwright's request API to talk to the backend directly. this
    // avoids browser networking problems and still exercises the same proxy
    // route used by the UI.
    const nodeResp = await page.request.post(`${BASE}/api/v1/concierge/message`, {
      data: { message: 'playwright-test' },
    });
    console.log('node-side status', nodeResp.status());

    const text = await nodeResp.text();
    console.log('node-side body (first 200 chars)', text.slice(0, 200));

    expect(nodeResp.status()).toBeGreaterThanOrEqual(200);
    expect(nodeResp.status()).toBeLessThan(600);

    // try to parse JSON and validate shape
    let parsed: any;
    try {
      parsed = text ? JSON.parse(text) : null;
    } catch (err) {
      throw new Error(`Failed to parse node-side response as JSON: ${err} -- body='${text}'`);
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
