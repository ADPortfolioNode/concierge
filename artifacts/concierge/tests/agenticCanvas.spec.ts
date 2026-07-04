import { test, expect, Page } from '@playwright/test';

// fetchTaskTree calls GET /api/v1/tasks/{id}/status
// Response shape must be { data: TaskTree }
const TASK_TREE_RESPONSE = {
  data: {
    task_id: 'root-node',
    task_name: 'Root Planning Task',
    status: 'running',
    state: 'running',
    progress: 50,
    parent_id: 'root-node',
    children: [
      {
        task_id: 'child-node-1',
        task_name: 'Research Step',
        status: 'done',
        state: 'done',
        progress: 100,
        parent_id: 'root-node',
        children: [],
        metadata: {},
      },
    ],
    metadata: { agent_type: 'planner' },
  },
};

async function gotoHome(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await expect(page.getByRole('link', { name: 'Concierge' }).first()).toBeVisible({ timeout: 15_000 });
}

async function navigateToTasks(page: Page) {
  await page.goto('/tasks');
  await page.waitForLoadState('domcontentloaded');
  await expect(page.locator('main h1').first()).toContainText(/Tasks/i, { timeout: 15_000 });
}

async function mockTaskApis(page: Page) {
  await page.route('**/api/v1/tasks/**/status', (route) => {
    if (!route.request().url().includes('test-thread-123')) {
      return route.continue();
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'success', data: TASK_TREE_RESPONSE.data }),
    });
  });
  await page.route('**/api/v1/concierge/timeline/stream**', (route) => route.abort());
  await page.route('**/api/v1/concierge/timeline/ws**', (route) => route.abort());
  await page.route('**/api/v1/concierge/threads/**/nodes/**/memories**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: { memories: [] } }),
    }),
  );
}

async function navigateToVisualizer(page: Page, viewport?: { width: number; height: number }) {
  if (viewport) {
    await page.setViewportSize(viewport);
  }
  await gotoHome(page);
  await navigateToTasks(page);

  // Seed a thread id so Visualizer controls appear; graph fetch runs once canvas mounts.
  await page.evaluate(() => {
    (window as any).getAppStore().setTaskThreadId('test-thread-123');
  });
  await page.waitForTimeout(300);

  const visualizerBtn = page.getByRole('button', { name: 'Visualizer' });
  await expect(visualizerBtn).toBeVisible({ timeout: 15_000 });
  await visualizerBtn.click();
  await waitForThreadGraph(page);
}

async function waitForThreadGraph(page: Page) {
  const mobileSummary = page.locator('.agentic-thread-mobile-summary');
  const canvas = page.locator('canvas[aria-label="Concierge thread graph"]');
  await expect(mobileSummary.or(canvas)).toBeVisible({ timeout: 12_000 });
  await page.waitForTimeout(800);
}

test.describe('AgenticThreadCanvas', () => {
  test.describe.configure({ timeout: 60_000 });

  test.beforeEach(async ({ page }) => {
    await mockTaskApis(page);
  });

  test('canvas renders without JS errors after switching to Visualizer', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', (err) => jsErrors.push(err.message));

    await navigateToVisualizer(page);

    const canvas = page.locator('canvas[aria-label="Concierge thread graph"]');
    await expect(canvas).toBeVisible({ timeout: 15_000 });

    const critical = jsErrors.filter(
      (e) =>
        !e.includes('EventSource') &&
        !e.includes('WebSocket') &&
        !e.includes('fetch') &&
        !e.includes('Failed to fetch') &&
        !e.includes('ERR_CONNECTION_REFUSED'),
    );
    expect(critical).toHaveLength(0);
  });

  test('fit view and reset view keep the graph canvas mounted', async ({ page }) => {
    await navigateToVisualizer(page);
    await waitForThreadGraph(page);

    const canvas = page.locator('canvas[aria-label="Concierge thread graph"]');
    await page.getByRole('button', { name: 'Fit view' }).click();
    await page.waitForTimeout(300);
    await expect(canvas).toBeVisible();
    await page.getByRole('button', { name: 'Reset view' }).click();
    await page.waitForTimeout(300);
    await expect(canvas).toBeVisible();
  });

  test('side panel shows empty state before node selection', async ({ page }) => {
    await navigateToVisualizer(page);
    await waitForThreadGraph(page);

    await expect(page.locator('.agentic-thread-panel-empty')).toBeVisible({ timeout: 12_000 });
    await expect(page.locator('.agentic-thread-sidepanel__content')).not.toBeVisible();
  });

  test('mobile fallback list renders instead of canvas on narrow viewports', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', (err) => jsErrors.push(err.message));

    await navigateToVisualizer(page, { width: 400, height: 800 });

    const mobileSummary = page.locator('.agentic-thread-mobile-summary');
    await expect(mobileSummary).toBeVisible({ timeout: 12_000 });

    await expect(page.locator('canvas[aria-label="Concierge thread graph"]')).not.toBeVisible();
    await expect(mobileSummary.locator('h3')).toContainText('Agent thread summary');

    const critical = jsErrors.filter(
      (e) =>
        !e.includes('EventSource') &&
        !e.includes('WebSocket') &&
        !e.includes('fetch') &&
        !e.includes('Failed to fetch') &&
        !e.includes('ERR_CONNECTION_REFUSED'),
    );
    expect(critical).toHaveLength(0);
  });

  test('clicking a mobile fallback node button marks it active', async ({ page }) => {
    await navigateToVisualizer(page, { width: 400, height: 800 });
    await waitForThreadGraph(page);

    const mobileList = page.locator('.agentic-thread-mobile-summary__list');
    await expect(mobileList).toBeVisible({ timeout: 12_000 });

    // Mock tree has root + 1 child = 2 nodes
    const nodeButtons = mobileList.locator('button');
    await expect(nodeButtons).toHaveCount(2, { timeout: 8_000 });

    const firstButton = nodeButtons.first();
    await expect(firstButton).not.toHaveClass(/agentic-thread-mobile-item--active/);

    await firstButton.click();
    await page.waitForTimeout(250);

    await expect(firstButton).toHaveClass(/agentic-thread-mobile-item--active/);
  });
});