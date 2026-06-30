import { test, expect } from '@playwright/test';

test('media page loads gallery from API', async ({ page }) => {
  const apiPromise = page.waitForResponse(
    (res) => res.url().includes('/api/v1/concierge/media') && res.status() === 200,
    { timeout: 15000 },
  );

  await page.goto('/media');
  const apiRes = await apiPromise;
  const json = await apiRes.json();
  const items = Array.isArray(json?.data) ? json.data : [];
  expect(items.length).toBeGreaterThan(0);

  await expect(page.getByText(/Generated images and media saved by Concierge/i)).toBeVisible({ timeout: 10000 });
  await expect(page.getByText(/No media is currently available/i)).not.toBeVisible();
  await expect(page.getByText(/item/i)).toBeVisible();
});