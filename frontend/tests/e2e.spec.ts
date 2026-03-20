import { test, expect } from '@playwright/test';

// increase per-test timeout to accommodate slower backend/model startup
test.setTimeout(60000);

// Simple end-to-end smoke test for the Concierge UI
// Assumes the frontend dev server is available at http://localhost:5173

const BASE = process.env.BASE_URL || 'http://localhost:5173';

test.describe('Concierge UI', () => {
  test.beforeEach(async ({ page }) => {
    page.on('console', (msg) => console.log('BROWSER:', msg.text()));
  });
  test('loads homepage and posts a message', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    // tell the store to use POST instead of streaming
    await page.evaluate(() => (window as any).USE_POST = true);

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
    await page.evaluate(() => (window as any).USE_POST = true);
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

  test('backend returns greeting for hi with suggestions', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await page.fill('textarea', 'hi');
    await page.keyboard.press('Enter');
    const bubble = page.locator('[aria-label^="message-"]:visible').last();
    await expect(bubble).toContainText('Hello');
    // should also mention at least one capability hint
    await expect(bubble).toContainText(/image|goal|file/i);
  });
  
  test('capability question yields hint', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await page.fill('textarea', 'what can you do?');
    await page.keyboard.press('Enter');
    const bubble = page.locator('[aria-label^="message-"]:visible').last();
    await expect(bubble).toContainText(/image|audio|video|file/i);
  });

  test('mentioning a keyword adds a hint', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await page.fill('textarea', 'here is an audio file');
    await page.keyboard.press('Enter');
    const bubble = page.locator('[aria-label^="message-"]:visible').last();
    await expect(bubble).toContainText(/audio/i);
  });

  test('search trigger returns results using ResearchAgent', async ({ page }) => {
    await page.route('**/api/v1/concierge/stream', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: `data:{"type":"progress","text":"Searching the web for 'foo'…"}\n\n` +
              `data:{"type":"token","text":"RESULTS"}\n\n` +
              `data:{"type":"done","result":{"response":"RESULTS"}}\n\n`,
      }),
    );
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await page.fill('textarea', 'search for foo');
    await page.keyboard.press('Enter');
    await expect(page.locator('text=Searching the web for')).toBeVisible();
    await expect(page.locator('text=RESULTS')).toBeVisible();
    // timeline header should render even empty plan
    await expect(page.locator('img[alt="timeline graph"]')).toBeVisible();
    // clicking a task button (if any) shows a meta card
    const taskBtn = page.locator('button').filter({ hasText: 'task' }).first();
    if (await taskBtn.count()) {
      await taskBtn.click();
      await expect(page.locator('pre')).toBeVisible();
      // close it
      await page.locator('button', { hasText: 'Close' }).click();
    }
  });

  test('backend handles small talk', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await page.fill('textarea', 'how are you?');
    await page.keyboard.press('Enter');
    const bubble = page.locator('[aria-label^="message-"]:visible').last();
    await expect(bubble).not.toHaveText('');
  });

  test('header displays provider info when present', async ({ page }) => {
    // stub streaming response with llm metadata
    await page.route('**/api/v1/concierge/stream', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: `data: {\"type\":\"done\",\"result\":{\"response\":\"yo\",\"llm_provider\":\"gemini\",\"llm_error\":\"switched\"}}\n\n`,
      }),
    );

    await page.goto(BASE, { waitUntil: 'networkidle' });
    await page.fill('textarea', 'hey');
    await page.keyboard.press('Enter');
    // header should update with provider text (match exact to avoid duplicates)
    await expect(page.getByText('Provider: gemini', { exact: true })).toBeVisible();
  });

  test.skip('chat bubble shows provider/error when LLM metadata present', async ({ page }) => {
    // capture console output from the browser
    page.on('console', (msg) => console.log('BROWSER:', msg.text()));
    // stub the streaming endpoint with a done event containing llm info
    await page.route('**/api/v1/concierge/stream', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: `data: {\"type\":\"done\",\"result\":{\"response\":\"hey\",\"llm_provider\":\"gemini\",\"llm_error\":\"switched to Gemini provider\"}}\n\n`,
      }),
    );
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await page.fill('textarea', 'trigger');
    await page.keyboard.press('Enter');
    // debug: log meta attributes
    const metas3 = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('[aria-label^="message-"]'))
        .map((el) => el.getAttribute('data-meta'));
    });
    console.log('meta attributes after stream stub', metas3);
    const texts = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('[aria-label^="message-"]'))
        .map(el => el.textContent);
    });
    console.log('message texts after stub', texts);
    const rawStore = await page.evaluate(() => (window as any).__APP_STORE__);
    console.log('raw store after stub', rawStore);
    // provider badge should appear eventually
    await expect(page.locator('text=Provider: gemini')).toBeVisible();
    // details panel should include error message
    await page.click('[aria-label^="message-"]:visible').last();
    await expect(page.locator('text=switched to Gemini provider')).toBeVisible();
  });


  test('navigation includes how-to and page renders', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    // confirm link is present in header
    const link = page.locator('nav >> text=How‑To');
    await expect(link).toBeVisible();
    await link.click();
    // new page should have the heading we added (emoji/casing may vary)
    await expect(page.locator('h1')).toContainText('How to Use Concierge');
  });

  test('multi-media response triggers full-screen stage', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    // stub API to include two media URLs (an image and a video)
    await page.route('**/api/v1/concierge/message', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          data: { content: 'https://example.com/a.png https://example.com/b.mp4' },
        }),
      })
    );

    await page.fill('textarea', 'show me media');
    await page.keyboard.press('Enter');

    // the stage should auto-expand to full-screen mode (button title changes)
    const toggle = page.locator('role=button[title="Restore size"]');
    await expect(toggle).toBeVisible();
    // verify both media elements exist inside the stage
    await expect(page.locator('img[src*="a.png"]')).toBeVisible();
    await expect(page.locator('video[src*="b.mp4"]')).toBeVisible();
  });

  test('tasks page shows processing banner when jobs exist', async ({ page }) => {
    // stub tasks API to simulate an active job
    const now = new Date().toISOString();
    await page.route('**/api/v1/tasks', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          data: [
            { id: 'job1', label: 'Example job', status: 'running', started_at: now, statusObj: { status: 'running' } }
          ]
        }),
      })
    );
    await page.goto(BASE + '/tasks', { waitUntil: 'networkidle' });
    await expect(page.locator('text=Example job')).toBeVisible();
    await expect(page.locator('text=elapsed')).toBeVisible();
    await page.click('text=show details');
    await expect(page.locator('text=Example job')).toBeVisible();
  });

  test('goals page shows processing banner when jobs exist', async ({ page }) => {
    const now = new Date().toISOString();
    await page.route('**/api/v1/tasks', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          data: [
            { id: 'job2', label: 'Goal job', status: 'queued', started_at: now, statusObj: { status: 'queued' } }
          ]
        }),
      })
    );
    await page.goto(BASE + '/goals', { waitUntil: 'networkidle' });
    await expect(page.locator('text=Goal job')).toBeVisible();
    await expect(page.locator('text=elapsed')).toBeVisible();
    await page.click('text=show details');
    await expect(page.locator('text=Goal job')).toBeVisible();
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
