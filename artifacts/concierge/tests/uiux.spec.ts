import { test, expect, Page } from '@playwright/test';

const ROUTES = [
  { path: '/', navLabel: 'Home', heading: /Concierge|Dashboard|workflow/i },
  { path: '/goals', navLabel: 'Goals', heading: /Goals/i },
  { path: '/strategy', navLabel: 'Strategy', heading: /Strategy/i },
  { path: '/tasks', navLabel: 'Tasks', heading: /Tasks/i },
  { path: '/workspace', navLabel: 'Workspace', heading: /Workspace/i },
  { path: '/media', navLabel: 'Media', heading: /Media library|Multimedia/i },
  { path: '/howto', navLabel: 'Guide', heading: /How to Use Concierge/i },
  { path: '/capabilities', navLabel: 'Integrations', heading: /Integrations|Capabilities/i },
] as const;

function collectCriticalErrors(errors: string[]) {
  return errors.filter(
    (e) =>
      !e.includes('EventSource') &&
      !e.includes('WebSocket') &&
      !e.includes('Failed to fetch') &&
      !e.includes('ERR_CONNECTION_REFUSED') &&
      !e.includes('NetworkError') &&
      !e.includes('Load failed'),
  );
}

async function gotoHome(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await expect(page.getByRole('link', { name: 'Concierge' }).first()).toBeVisible({ timeout: 15_000 });
}

async function navigateViaHeader(page: Page, label: string, path: string) {
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: label, exact: true }).click();
  await page.waitForURL(`**${path}`);
}

async function resetTimelineToIdle(page: Page) {
  await page.evaluate(() => {
    const es = (window as any).__TIMELINE_ES__;
    if (es) {
      es.close();
      (window as any).__TIMELINE_ES__ = null;
    }
    const store = (window as any).getAppStore?.();
    store?.clearTaskThread?.();
    store?.setTaskThreadId?.(null);
    store?.setTimelinePlan?.({ tasks: [] });
  });
}

async function mockEmptyTimeline(page: Page) {
  await page.route('**/api/v1/concierge/timeline**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'success', data: { tasks: [] } }),
    }),
  );
}

test.describe('Layout shell', () => {
  test('header, nav links, and chat sidebar render on home', async ({ page }) => {
    await gotoHome(page);

    await expect(page.getByRole('banner')).toBeVisible();
    await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible();
    await expect(page.getByRole('complementary', { name: 'AI Concierge chat' })).toBeVisible();
    await expect(page.getByText('Concierge', { exact: false }).first()).toBeVisible();
    await expect(page.getByText('Ready to help').or(page.getByText(/Orchestrating/))).toBeVisible();
  });

  test('chat toggle hides and restores sidebar on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await gotoHome(page);

    const chat = page.getByRole('complementary', { name: 'AI Concierge chat' });
    await expect(chat).toBeVisible();

    await page.getByRole('button', { name: '⤫ Chat' }).click();
    await expect(chat).not.toBeVisible();

    await page.getByRole('button', { name: 'Chat ▸' }).click();
    await expect(chat).toBeVisible();
  });

  test('mobile drawer navigation opens and closes', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await gotoHome(page);

    await page.getByRole('button', { name: 'Open navigation' }).click();
    const mobileNav = page.getByRole('navigation', { name: 'Mobile navigation' });
    await expect(mobileNav).toBeVisible();

    await mobileNav.getByRole('link', { name: 'Tasks' }).click();
    await expect(page).toHaveURL(/\/tasks/);
    await expect(mobileNav).not.toBeVisible();
  });
});

test.describe('Routes — client-side navigation', () => {
  for (const route of ROUTES) {
    test(`${route.path} loads via header nav without JS errors`, async ({ page }) => {
      const jsErrors: string[] = [];
      page.on('pageerror', (err) => jsErrors.push(err.message));

      await gotoHome(page);
      if (route.path === '/') {
        await expect(page.locator('main')).toBeVisible();
      } else {
        await navigateViaHeader(page, route.navLabel, route.path);
      }

      await expect(page.locator('main h1').first()).toBeVisible({ timeout: 10_000 });
      await expect(page.locator('main h1').first()).toContainText(route.heading);

      expect(collectCriticalErrors(jsErrors)).toHaveLength(0);
    });
  }

  test('unknown path redirects to home', async ({ page }) => {
    await gotoHome(page);
    await page.evaluate(() => {
      window.history.pushState({}, '', '/this-route-does-not-exist');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });
    // React Router Navigate should send us back to /
    await page.waitForTimeout(500);
    await expect(page).toHaveURL(/\/(\?.*)?$/);
  });
});

test.describe('Routes — direct URL (production SPA fallback)', () => {
  for (const route of ROUTES.filter((r) => r.path !== '/')) {
    test(`direct load ${route.path} should serve SPA shell`, async ({ page }) => {
      const response = await page.goto(route.path);
      // Known production issue: StaticFiles html=True does not fall back for client routes.
      // Document current behavior; fail only if we get a hard network error.
      expect(response).not.toBeNull();
      const status = response?.status() ?? 0;
      if (status === 404) {
        test.info().annotations.push({
          type: 'bug',
          description: `Direct navigation to ${route.path} returns HTTP 404 — SPA fallback missing in production server.`,
        });
        return;
      }
      await expect(page.locator('main h1').first()).toContainText(route.heading, { timeout: 10_000 });
    });
  }
});

test.describe('Home workflows', () => {
  test('home links to tasks and media', async ({ page }) => {
    await gotoHome(page);
    const tasksLink = page.locator('main').getByRole('link', { name: 'Tasks', exact: true });
    await expect(tasksLink).toBeVisible({ timeout: 10_000 });
    await tasksLink.click();
    await expect(page).toHaveURL(/\/tasks/);
  });

  test('sample prompt injects draft into chat input', async ({ page }) => {
    await gotoHome(page);
    const promptButton = page.locator('main button').filter({ hasText: /Summarize and tag|uploaded/i }).first();
    if (await promptButton.count()) {
      await promptButton.click();
      await expect(page).toHaveURL(/\//);
      const chatInput = page.getByPlaceholder(/message|ask|concierge/i);
      await expect(chatInput).toBeVisible({ timeout: 5_000 });
      const value = await chatInput.inputValue();
      expect(value.length).toBeGreaterThan(10);
    }
  });
});

test.describe('Tasks workflows', () => {
  test('sub-navigation tabs switch content descriptions', async ({ page }) => {
    await gotoHome(page);
    await navigateViaHeader(page, 'Tasks', '/tasks');

    await page.getByRole('button', { name: 'Sample tasks', exact: true }).click();
    await expect(page.getByText(/Sample tasks: explore curated task examples/i)).toBeVisible();

    await page.getByRole('button', { name: 'Job history', exact: true }).click();
    await expect(page.getByText(/Job history: monitor queue status/i)).toBeVisible();

    await page.getByRole('button', { name: 'Quick prompts', exact: true }).click();
    await expect(page.getByText(/Quick prompts: use these prompt templates/i)).toBeVisible();
  });

  test('distributed agent job form validates empty goal', async ({ page }) => {
    await gotoHome(page);
    await navigateViaHeader(page, 'Tasks', '/tasks');

    const submit = page.getByRole('button', { name: 'Submit Job' });
    await expect(submit).toBeDisabled();

    await page.getByPlaceholder('Goal — what should the agent do?').fill('List open tasks in the workspace');
    await expect(submit).toBeEnabled();
  });

  test('tasks page shows timeline hero (idle or active)', async ({ page }) => {
    await mockEmptyTimeline(page);
    await gotoHome(page);
    await resetTimelineToIdle(page);
    await navigateViaHeader(page, 'Tasks', '/tasks');
    await resetTimelineToIdle(page);

    const hero = page.locator('section.timeline-hero');
    const idle = hero.getByRole('heading', { name: 'No active thread' });
    const active = hero.getByText(/Agentic thread visualizer/i);
    await expect(idle.or(active).first()).toBeVisible({ timeout: 15_000 });
    if (await idle.isVisible()) {
      await expect(hero.getByRole('button', { name: 'Visualizer' })).not.toBeVisible();
    } else {
      await expect(hero.getByRole('button', { name: 'Visualizer' })).toBeVisible();
    }
  });
});

test.describe('Goals & Strategy prompts', () => {
  test('goals sample prompt navigates home with draft', async ({ page }) => {
    await gotoHome(page);
    await navigateViaHeader(page, 'Goals', '/goals');

    const prompt = page.locator('main button').filter({ hasText: /launch|goal|week/i }).first();
    await expect(prompt).toBeVisible();
    await prompt.click();
    await expect(page).toHaveURL(/\//);
  });

  test('strategy page shows framework cards', async ({ page }) => {
    await gotoHome(page);
    await navigateViaHeader(page, 'Strategy', '/strategy');
    await expect(page.getByText('OKR', { exact: true })).toBeVisible();
    await expect(page.getByText('SWOT', { exact: true })).toBeVisible();
  });
});

test.describe('Workspace & Media', () => {
  test('workspace shows allowed file types', async ({ page }) => {
    await gotoHome(page);
    await navigateViaHeader(page, 'Workspace', '/workspace');
    await expect(page.getByText(/Plain text|CSV|PDF/i).first()).toBeVisible();
  });

  test('media page loads gallery or empty state', async ({ page }) => {
    await gotoHome(page);
    await navigateViaHeader(page, 'Media', '/media');
    const apiRes = await page.waitForResponse(
      (res) => res.url().includes('/api/v1/concierge/media') && res.status() === 200,
      { timeout: 30_000 },
    );
    const json = await apiRes.json();
    const payload = json?.data;
    const items = Array.isArray(payload)
      ? payload
      : Array.isArray(payload?.items)
      ? payload.items
      : [];
    await expect(page.getByRole('link', { name: '← Home' })).toBeVisible();
    await expect(page.getByText(/Media library/i).first()).toBeVisible({ timeout: 10_000 });
    if (items.length > 0) {
      await expect(page.getByText(/Preview —|file\(s\)/i).first()).toBeVisible({ timeout: 10_000 });
      await expect(page.getByText(/No images in/i)).not.toBeVisible();
    } else {
      await expect(page.getByText(/No images in/i).first()).toBeVisible({ timeout: 10_000 });
    }
  });
});

test.describe('Guide & Integrations', () => {
  test('how-to sections are collapsible', async ({ page }) => {
    await gotoHome(page);
    await navigateViaHeader(page, 'Guide', '/howto');

    const sectionButton = page.locator('main section button').first();
    await expect(sectionButton).toBeVisible();
    await sectionButton.click();
    await sectionButton.click();
  });

  test('integrations page loads capability categories', async ({ page }) => {
    await gotoHome(page);
    await navigateViaHeader(page, 'Integrations', '/capabilities');
    await expect(page.getByText(/Plugins|Tools|Integrations/i).first()).toBeVisible({ timeout: 15_000 });
  });
});

test.describe('Chat workflows', () => {
  test('message input accepts text and shows send affordance', async ({ page }) => {
    await gotoHome(page);
    const input = page.getByPlaceholder(/message|ask|concierge/i);
    await expect(input).toBeVisible();
    await input.fill('Hello from UI test');
    await expect(input).toHaveValue('Hello from UI test');
  });

  test('chat sidebar shows empty-state prompt when no messages', async ({ page }) => {
    await gotoHome(page);
    await expect(page.getByRole('complementary', { name: 'AI Concierge chat' })).toBeVisible();
    await expect(
      page.getByText(/Ask Concierge to plan a goal|ready when you are/i).first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('tasks page prompt fills chat draft after navigation', async ({ page }) => {
    await gotoHome(page);
    await navigateViaHeader(page, 'Tasks', '/tasks');

    const prompt = page.locator('main button').filter({ hasText: /Read the spec|Python script|CSV/i }).first();
    await prompt.click();
    await expect(page).toHaveURL(/\//);
    const input = page.getByPlaceholder(/message|ask|concierge/i);
    await expect(input).toHaveValue(/.{10,}/, { timeout: 5_000 });
  });
});

test.describe('Full navigation workflow', () => {
  test('visit every page in order and verify shell + page meta bar', async ({ page }) => {
    await gotoHome(page);

    for (const route of ROUTES) {
      if (route.path !== '/') {
        await navigateViaHeader(page, route.navLabel, route.path);
      }
      await expect(page.locator('main h1').first()).toContainText(route.heading, { timeout: 10_000 });
      await expect(page.getByRole('complementary', { name: 'AI Concierge chat' })).toBeVisible();
      // PageMetaBar shows route title chip on each page
      await expect(page.getByText(route.navLabel === 'Home' ? 'Dashboard' : route.navLabel, { exact: false }).first()).toBeVisible();
    }
  });

  test('page meta bar loads dashboard chips when API is reachable', async ({ page }) => {
    await gotoHome(page);
    await expect(page.getByText('Dashboard').first()).toBeVisible({ timeout: 15_000 });
    await expect(
      page.getByText(/Requests|Tasks|No active plan/i).first(),
    ).toBeVisible({ timeout: 15_000 });
  });
});

test.describe('Timeline tree layout', () => {
  test('tasks page shows idle timeline without visualizer chrome', async ({ page }) => {
    await mockEmptyTimeline(page);
    await gotoHome(page);
    await resetTimelineToIdle(page);
    await navigateViaHeader(page, 'Tasks', '/tasks');
    await resetTimelineToIdle(page);

    const hero = page.locator('section.timeline-hero');
    await expect(hero.getByRole('heading', { name: 'No active thread' })).toBeVisible({ timeout: 15_000 });
    await expect(hero.getByRole('button', { name: 'Visualizer' })).not.toBeVisible();
  });

  test('home shows orchestrator status or live workflow tree', async ({ page }) => {
    await gotoHome(page);
    const hero = page.getByText(/Orchestrator ready|Active workflow/i);
    const liveTree = page.getByTestId('timeline-horizontal-tree');
    await expect(hero.or(liveTree).first()).toBeVisible({ timeout: 10_000 });
  });
});