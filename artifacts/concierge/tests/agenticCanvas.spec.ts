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

async function mockTaskApis(page: Page) {
  await page.route('**/api/v1/tasks/test-thread-123/status', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(TASK_TREE_RESPONSE),
    }),
  );
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
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Tasks', exact: true }).click();
  await page.waitForURL('**/tasks');

  // Visualizer controls only appear when a thread or tasks exist; seed one for canvas tests.
  await page.evaluate(() => {
    (window as any).getAppStore().setTaskThreadId('test-thread-123');
  });
  await page.waitForTimeout(400);

  const visualizerBtn = page.getByRole('button', { name: 'Visualizer' });
  await expect(visualizerBtn).toBeVisible({ timeout: 10_000 });
  await visualizerBtn.click();
}

async function injectMockThread(page: Page) {
  await page.evaluate(() => {
    (window as any).getAppStore().setTaskThreadId('test-thread-123');
  });
  // Allow time for the component to fetch the task tree and render nodes
  await page.waitForTimeout(700);
}

async function hoverAndSelectFirstNode(page: Page) {
  const canvasShell = page.locator('.agentic-thread-canvas-shell');
  await expect(canvasShell).toBeVisible({ timeout: 8_000 });

  // Node is laid out at canvas coords (200, 120) by the layout algorithm
  // In the initial view (x=0, y=0, scale=1) screen position equals canvas position
  await canvasShell.hover({ position: { x: 200, y: 120 } });
  // Allow the RAF-throttled hover handler to fire
  await page.waitForTimeout(300);

  const chip = page.locator('.agentic-thread-node-chip').first();
  await expect(chip).toBeVisible({ timeout: 5_000 });
  await chip.click();
  await page.waitForTimeout(200);
}

test.describe('AgenticThreadCanvas', () => {
  test('canvas renders without JS errors after switching to Visualizer', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', (err) => jsErrors.push(err.message));

    await navigateToVisualizer(page);

    const canvas = page.locator('canvas[aria-label="Concierge thread graph"]');
    await expect(canvas).toBeVisible({ timeout: 10_000 });

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

  test('fit view button triggers a measurable view-state change', async ({ page }) => {
    await mockTaskApis(page);
    await navigateToVisualizer(page);
    await injectMockThread(page);

    // Select the node so its overlay chip stays visible through button clicks
    await hoverAndSelectFirstNode(page);

    const chip = page.locator('.agentic-thread-node-chip').first();

    // Reset view → viewState = { x:0, y:0, scale:1 }
    // At scale=1 the chip at node.x=200 renders at style.left="200px"
    await page.getByRole('button', { name: 'Reset view' }).click();
    await page.waitForTimeout(300);
    const leftAfterReset = await chip.evaluate((el) => (el as HTMLElement).style.left);

    // Fit view computes a new x/y/scale from the bounding box of all nodes
    // → the chip's screen position changes
    await page.getByRole('button', { name: 'Fit view' }).click();
    await page.waitForTimeout(300);
    const leftAfterFit = await chip.evaluate((el) => (el as HTMLElement).style.left);

    expect(leftAfterFit).not.toBe(leftAfterReset);

    await expect(page.locator('canvas[aria-label="Concierge thread graph"]')).toBeVisible();
  });

  test('clicking a node chip opens its details in the side panel', async ({ page }) => {
    await mockTaskApis(page);
    await navigateToVisualizer(page);

    const panelEmpty = page.locator('.agentic-thread-panel-empty');
    await expect(panelEmpty).toBeVisible({ timeout: 8_000 });

    await injectMockThread(page);
    await hoverAndSelectFirstNode(page);

    await expect(page.locator('.agentic-thread-sidepanel__content')).toBeVisible({ timeout: 5_000 });
    await expect(panelEmpty).not.toBeVisible();
  });

  test('mobile fallback list renders instead of canvas on narrow viewports', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', (err) => jsErrors.push(err.message));

    await navigateToVisualizer(page, { width: 400, height: 800 });

    const mobileSummary = page.locator('.agentic-thread-mobile-summary');
    await expect(mobileSummary).toBeVisible({ timeout: 8_000 });

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
    await mockTaskApis(page);
    await navigateToVisualizer(page, { width: 400, height: 800 });
    await injectMockThread(page);

    const mobileList = page.locator('.agentic-thread-mobile-summary__list');
    await expect(mobileList).toBeVisible({ timeout: 8_000 });

    // Mock tree has root + 1 child = 2 nodes
    const nodeButtons = mobileList.locator('button');
    await expect(nodeButtons).toHaveCount(2, { timeout: 5_000 });

    const firstButton = nodeButtons.first();
    await expect(firstButton).not.toHaveClass(/agentic-thread-mobile-item--active/);

    await firstButton.click();
    await page.waitForTimeout(200);

    await expect(firstButton).toHaveClass(/agentic-thread-mobile-item--active/);
  });
});
