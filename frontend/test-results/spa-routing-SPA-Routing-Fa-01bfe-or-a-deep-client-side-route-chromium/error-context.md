# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: spa-routing.spec.ts >> SPA Routing Fallback Verification >> should serve index.html for a deep client-side route
- Location: tests\spa-routing.spec.ts:9:7

# Error details

```
Error: page.goto: Protocol error (Page.navigate): Cannot navigate to invalid URL
Call log:
  - navigating to "/capabilities", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('SPA Routing Fallback Verification', () => {
  4  |   /**
  5  |    * Test that a client-side route serves the index.html and the app loads.
  6  |    * This verifies that the server correctly falls back to the SPA entrypoint
  7  |    * for paths that look like application pages.
  8  |    */
  9  |   test('should serve index.html for a deep client-side route', async ({ page }) => {
  10 |     // Navigate to a path that doesn't correspond to a static file on the server.
> 11 |     await page.goto('/capabilities');
     |                ^ Error: page.goto: Protocol error (Page.navigate): Cannot navigate to invalid URL
  12 | 
  13 |     // Check that the React app has loaded by looking for a known element on that page.
  14 |     const heading = page.locator('h1', { hasText: 'Capabilities' });
  15 |     await expect(heading).toBeVisible({ timeout: 10000 });
  16 | 
  17 |     // Also verify the title, which is set in index.html or by the React app.
  18 |     await expect(page).toHaveTitle(/Concierge/);
  19 |   });
  20 | 
  21 |   /**
  22 |    * Test that a request for a non-existent static asset returns a 404.
  23 |    * This is critical to ensure the browser doesn't receive HTML when it
  24 |    * expects CSS or JavaScript, which would break the page.
  25 |    */
  26 |   test('should return 404 for a non-existent static asset', async ({ page }) => {
  27 |     const assetUrl = '/assets/this-file-does-not-exist.js';
  28 | 
  29 |     // Listen for the response and assert its status code.
  30 |     const [response] = await Promise.all([
  31 |       page.waitForResponse(resp => resp.url().includes(assetUrl)),
  32 |       page.evaluate(url => fetch(url), assetUrl), // Trigger the fetch from the browser context
  33 |     ]);
  34 | 
  35 |     expect(response.status()).toBe(404);
  36 |   });
  37 | 
  38 |   /**
  39 |    * Test that a request for a non-existent API endpoint returns a 404.
  40 |    * This confirms that the SPA fallback logic correctly ignores paths
  41 |    * that are intended for the API.
  42 |    */
  43 |   test('should return 404 for a non-existent API route', async ({ page }) => {
  44 |     const apiUrl = '/api/v1/this/route/does/not/exist';
  45 | 
  46 |     const [response] = await Promise.all([
  47 |       page.waitForResponse(resp => resp.url().includes(apiUrl)),
  48 |       page.evaluate(url => fetch(url), apiUrl),
  49 |     ]);
  50 | 
  51 |     // The API should return a 404, not the SPA fallback.
  52 |     const responseBody = await response.json();
  53 |     expect(response.status()).toBe(404);
  54 |     expect(responseBody.detail).toBe('Not Found');
  55 |   });
  56 | });
```