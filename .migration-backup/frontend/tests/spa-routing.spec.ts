import { test, expect } from '@playwright/test';

test.describe('SPA Routing Fallback Verification', () => {
  /**
   * Test that a client-side route serves the index.html and the app loads.
   * This verifies that the server correctly falls back to the SPA entrypoint
   * for paths that look like application pages.
   */
  test('should serve index.html for a deep client-side route', async ({ page }) => {
    // Navigate to a path that doesn't correspond to a static file on the server.
    await page.goto('/capabilities');

    // Check that the React app has loaded by looking for a known element on that page.
    const heading = page.locator('h1', { hasText: 'Capabilities' });
    await expect(heading).toBeVisible({ timeout: 10000 });

    // Also verify the title, which is set in index.html or by the React app.
    await expect(page).toHaveTitle(/Concierge/);
  });

  /**
   * Test that a request for a non-existent static asset returns a 404.
   * This is critical to ensure the browser doesn't receive HTML when it
   * expects CSS or JavaScript, which would break the page.
   */
  test('should return 404 for a non-existent static asset', async ({ page }) => {
    const assetUrl = '/assets/this-file-does-not-exist.js';

    // Listen for the response and assert its status code.
    const [response] = await Promise.all([
      page.waitForResponse(resp => resp.url().includes(assetUrl)),
      page.evaluate(url => fetch(url), assetUrl), // Trigger the fetch from the browser context
    ]);

    expect(response.status()).toBe(404);
  });

  /**
   * Test that a request for a non-existent API endpoint returns a 404.
   * This confirms that the SPA fallback logic correctly ignores paths
   * that are intended for the API.
   */
  test('should return 404 for a non-existent API route', async ({ page }) => {
    const apiUrl = '/api/v1/this/route/does/not/exist';

    const [response] = await Promise.all([
      page.waitForResponse(resp => resp.url().includes(apiUrl)),
      page.evaluate(url => fetch(url), apiUrl),
    ]);

    // The API should return a 404, not the SPA fallback.
    const responseBody = await response.json();
    expect(response.status()).toBe(404);
    expect(responseBody.detail).toBe('Not Found');
  });
});