# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e2e.spec.ts >> Concierge UI >> capability question yields hint
- Location: tests\e2e.spec.ts:76:7

# Error details

```
Test timeout of 60000ms exceeded.
```

```
Error: page.fill: Test timeout of 60000ms exceeded.
Call log:
  - waiting for locator('textarea')

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - generic [ref=e4]:
    - img "Concierge" [ref=e5]
    - heading "Concierge" [level=1] [ref=e6]
  - paragraph [ref=e9]: Starting services...
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | // increase per-test timeout to accommodate slower backend/model startup
  4   | test.setTimeout(60000);
  5   | 
  6   | // Simple end-to-end smoke test for the Concierge UI
  7   | // Assumes the frontend dev server is available at http://localhost:5173
  8   | 
  9   | const BASE = process.env.BASE_URL || 'http://localhost:5173';
  10  | 
  11  | test.describe('Concierge UI', () => {
  12  |   test.beforeEach(async ({ page }) => {
  13  |     page.on('console', (msg) => console.log('BROWSER:', msg.text()));
  14  |   });
  15  |   test('loads homepage and posts a message', async ({ page }) => {
  16  |     await page.goto(BASE, { waitUntil: 'networkidle' });
  17  |     // tell the store to use POST instead of streaming
  18  |     await page.evaluate(() => (window as any).USE_POST = true);
  19  | 
  20  |     // Check the landing text
  21  |     await expect(page.locator('text=AI Ops Concierge')).toBeVisible();
  22  | 
  23  |     // stub the API so that when the UI sends a message we immediately return
  24  |     // a minimal success payload; verify the conversation updates accordingly.
  25  |     await page.route('**/api/v1/concierge/message', (route) =>
  26  |       route.fulfill({
  27  |         status: 200,
  28  |         contentType: 'application/json',
  29  |         body: JSON.stringify({
  30  |           status: 'success',
  31  |           data: { content: 'ok' },
  32  |         }),
  33  |       })
  34  |     );
  35  | 
  36  |     // type and send through the UI
  37  |     await page.fill('textarea', 'hello');
  38  |     await page.keyboard.press('Enter');
  39  | 
  40  |     // the stubbed response 'ok' should appear in the chat
  41  |     await expect(page.locator('text=ok')).toBeVisible();
  42  |   });
  43  | 
  44  |   test('shows error banner when API fails', async ({ page }) => {
  45  |     await page.goto(BASE, { waitUntil: 'networkidle' });
  46  |     await page.evaluate(() => (window as any).USE_POST = true);
  47  |     // first simulate a 400 response (e.g. missing message field)
  48  |     await page.route('**/api/v1/concierge/message', (route) =>
  49  |       route.fulfill({ status: 400, body: 'message required' })
  50  |     );
  51  |     await page.fill('textarea', 'will be blocked');
  52  |     await page.keyboard.press('Enter');
  53  |     let banner = page.locator('role=alert');
  54  |     await expect(banner).toContainText('400');
  55  | 
  56  |     // now simulate a generic server error
  57  |     await page.route('**/api/v1/concierge/message', (route) =>
  58  |       route.fulfill({ status: 500, body: 'server error' })
  59  |     );
  60  |     await page.fill('textarea', 'trigger error');
  61  |     await page.keyboard.press('Enter');
  62  |     banner = page.locator('role=alert');
  63  |     await expect(banner).toContainText('500');
  64  |   });
  65  | 
  66  |   test('backend returns greeting for hi with suggestions', async ({ page }) => {
  67  |     await page.goto(BASE, { waitUntil: 'networkidle' });
  68  |     await page.fill('textarea', 'hi');
  69  |     await page.keyboard.press('Enter');
  70  |     const bubble = page.locator('[aria-label^="message-"]:visible').last();
  71  |     await expect(bubble).toContainText('Hello');
  72  |     // should also mention at least one capability hint
  73  |     await expect(bubble).toContainText(/image|goal|file/i);
  74  |   });
  75  |   
  76  |   test('capability question yields hint', async ({ page }) => {
  77  |     await page.goto(BASE, { waitUntil: 'networkidle' });
> 78  |     await page.fill('textarea', 'what can you do?');
      |                ^ Error: page.fill: Test timeout of 60000ms exceeded.
  79  |     await page.keyboard.press('Enter');
  80  |     const bubble = page.locator('[aria-label^="message-"]:visible').last();
  81  |     await expect(bubble).toContainText(/image|audio|video|file/i);
  82  |   });
  83  | 
  84  |   test('mentioning a keyword adds a hint', async ({ page }) => {
  85  |     await page.goto(BASE, { waitUntil: 'networkidle' });
  86  |     await page.fill('textarea', 'here is an audio file');
  87  |     await page.keyboard.press('Enter');
  88  |     const bubble = page.locator('[aria-label^="message-"]:visible').last();
  89  |     await expect(bubble).toContainText(/audio/i);
  90  |   });
  91  | 
  92  |   test('search trigger returns results using ResearchAgent', async ({ page }) => {
  93  |     await page.route('**/api/v1/concierge/stream', (route) =>
  94  |       route.fulfill({
  95  |         status: 200,
  96  |         contentType: 'text/event-stream',
  97  |         body: `data:{"type":"progress","text":"Searching the web for 'foo'…"}\n\n` +
  98  |               `data:{"type":"token","text":"RESULTS"}\n\n` +
  99  |               `data:{"type":"done","result":{"response":"RESULTS"}}\n\n`,
  100 |       }),
  101 |     );
  102 |     await page.goto(BASE, { waitUntil: 'networkidle' });
  103 |     await page.fill('textarea', 'search for foo');
  104 |     await page.keyboard.press('Enter');
  105 |     await expect(page.locator('text=Searching the web for')).toBeVisible();
  106 |     await expect(page.locator('text=RESULTS')).toBeVisible();
  107 |     // timeline header should render even empty plan
  108 |     await expect(page.locator('img[alt="timeline graph"]')).toBeVisible();
  109 |     // clicking a task button (if any) shows a meta card
  110 |     const taskBtn = page.locator('button').filter({ hasText: 'task' }).first();
  111 |     if (await taskBtn.count()) {
  112 |       await taskBtn.click();
  113 |       await expect(page.locator('pre')).toBeVisible();
  114 |       // close it
  115 |       await page.locator('button', { hasText: 'Close' }).click();
  116 |     }
  117 |   });
  118 | 
  119 |   test('backend handles small talk', async ({ page }) => {
  120 |     await page.goto(BASE, { waitUntil: 'networkidle' });
  121 |     await page.fill('textarea', 'how are you?');
  122 |     await page.keyboard.press('Enter');
  123 |     const bubble = page.locator('[aria-label^="message-"]:visible').last();
  124 |     await expect(bubble).not.toHaveText('');
  125 |   });
  126 | 
  127 |   test('header displays provider info when present', async ({ page }) => {
  128 |     // stub streaming response with llm metadata
  129 |     await page.route('**/api/v1/concierge/stream', (route) =>
  130 |       route.fulfill({
  131 |         status: 200,
  132 |         contentType: 'text/event-stream',
  133 |         body: `data: {\"type\":\"done\",\"result\":{\"response\":\"yo\",\"llm_provider\":\"gemini\",\"llm_error\":\"switched\"}}\n\n`,
  134 |       }),
  135 |     );
  136 | 
  137 |     await page.goto(BASE, { waitUntil: 'networkidle' });
  138 |     await page.fill('textarea', 'hey');
  139 |     await page.keyboard.press('Enter');
  140 |     // header should update with provider text (match exact to avoid duplicates)
  141 |     await expect(page.getByText('Provider: gemini', { exact: true })).toBeVisible();
  142 |   });
  143 | 
  144 |   test.skip('chat bubble shows provider/error when LLM metadata present', async ({ page }) => {
  145 |     // capture console output from the browser
  146 |     page.on('console', (msg) => console.log('BROWSER:', msg.text()));
  147 |     // stub the streaming endpoint with a done event containing llm info
  148 |     await page.route('**/api/v1/concierge/stream', (route) =>
  149 |       route.fulfill({
  150 |         status: 200,
  151 |         contentType: 'text/event-stream',
  152 |         body: `data: {\"type\":\"done\",\"result\":{\"response\":\"hey\",\"llm_provider\":\"gemini\",\"llm_error\":\"switched to Gemini provider\"}}\n\n`,
  153 |       }),
  154 |     );
  155 |     await page.goto(BASE, { waitUntil: 'networkidle' });
  156 |     await page.fill('textarea', 'trigger');
  157 |     await page.keyboard.press('Enter');
  158 |     // debug: log meta attributes
  159 |     const metas3 = await page.evaluate(() => {
  160 |       return Array.from(document.querySelectorAll('[aria-label^="message-"]'))
  161 |         .map((el) => el.getAttribute('data-meta'));
  162 |     });
  163 |     console.log('meta attributes after stream stub', metas3);
  164 |     const texts = await page.evaluate(() => {
  165 |       return Array.from(document.querySelectorAll('[aria-label^="message-"]'))
  166 |         .map(el => el.textContent);
  167 |     });
  168 |     console.log('message texts after stub', texts);
  169 |     const rawStore = await page.evaluate(() => (window as any).__APP_STORE__);
  170 |     console.log('raw store after stub', rawStore);
  171 |     // provider badge should appear eventually
  172 |     await expect(page.locator('text=Provider: gemini')).toBeVisible();
  173 |     // details panel should include error message
  174 |     await page.click('[aria-label^="message-"]:visible').last();
  175 |     await expect(page.locator('text=switched to Gemini provider')).toBeVisible();
  176 |   });
  177 | 
  178 | 
```