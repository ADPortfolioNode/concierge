# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e2e.spec.ts >> Concierge UI >> loads homepage and posts a message
- Location: tests\e2e.spec.ts:15:7

# Error details

```
Test timeout of 60000ms exceeded.
```

```
Error: page.goto: Test timeout of 60000ms exceeded.
Call log:
  - navigating to "http://localhost:5173/", waiting until "networkidle"

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - banner [ref=e4]:
    - generic [ref=e5]:
      - link "Concierge Concierge" [ref=e7] [cursor=pointer]:
        - /url: /
        - img "Concierge" [ref=e8]
        - generic [ref=e9]: Concierge
      - navigation "Main navigation" [ref=e10]:
        - link "Home" [ref=e11] [cursor=pointer]:
          - /url: /
        - link "Goals" [ref=e13] [cursor=pointer]:
          - /url: /goals
        - link "Strategy" [ref=e14] [cursor=pointer]:
          - /url: /strategy
        - link "Tasks" [ref=e16] [cursor=pointer]:
          - /url: /tasks
        - link "Workspace" [ref=e17] [cursor=pointer]:
          - /url: /workspace
        - link "Media" [ref=e18] [cursor=pointer]:
          - /url: /media
        - link "Guide" [ref=e20] [cursor=pointer]:
          - /url: /howto
        - link "Integrations" [ref=e21] [cursor=pointer]:
          - /url: /capabilities
  - complementary "AI Concierge chat" [ref=e22]:
    - generic [ref=e23]:
      - generic [ref=e24]:
        - img "Online" [ref=e25]
        - generic [ref=e26]:
          - generic [ref=e27]: Concierge
          - generic [ref=e28]: I'm ready to help
      - generic [ref=e30]:
        - img "timeline graph"
        - button "▾" [ref=e31] [cursor=pointer]
      - generic "message-welcome" [ref=e35]:
        - generic [ref=e36]: Welcome. I'm ready when you are. What would you like to work on today?
        - generic [ref=e37]: 4/24/2026, 11:50:44 AM
      - generic [ref=e39]:
        - generic [ref=e40]:
          - button "📎" [ref=e41] [cursor=pointer]
          - textbox "Message — Enter to send, Shift+Enter for newline" [ref=e42]
          - button "↑" [disabled] [ref=e43]
        - button "🗑 Clear memory" [ref=e45] [cursor=pointer]
  - main [ref=e46]:
    - generic [ref=e47]:
      - generic [ref=e49]:
        - heading "Build smarter workflows, see results visually." [level=1] [ref=e50]:
          - text: Build smarter workflows,
          - text: see results visually.
        - paragraph [ref=e51]: Ask me to plan, execute, and monitor your work. I can also surface photo-driven insights, review your files, and turn your goals into a clear visual timeline.
        - generic [ref=e52]:
          - button "↗ Show me my current roadmap" [ref=e53] [cursor=pointer]:
            - generic [ref=e54]: ↗
            - generic [ref=e55]: Show me my current roadmap
          - button "↗ Create a visual status update" [ref=e56] [cursor=pointer]:
            - generic [ref=e57]: ↗
            - generic [ref=e58]: Create a visual status update
          - button "↗ Generate a media summary" [ref=e59] [cursor=pointer]:
            - generic [ref=e60]: ↗
            - generic [ref=e61]: Generate a media summary
      - generic [ref=e62]:
        - generic [ref=e64]:
          - generic [ref=e65]: Live Timeline
          - heading "See Concierge planning in one responsive view" [level=2] [ref=e66]
          - paragraph [ref=e67]: Your current plan updates, task progress, and visual graph are surfaced in a mobile-first timeline card that spans the full width of the landing page.
        - generic [ref=e68]:
          - generic [ref=e69]:
            - generic [ref=e70]:
              - paragraph [ref=e71]: Assistant timeline
              - heading "Assistant linear timeline" [level=2] [ref=e72]
              - paragraph [ref=e73]: Visualize the assistant's strategy as a linear timeline with tasks and progress.
            - button "View full timeline" [ref=e74] [cursor=pointer]
          - generic [ref=e75]:
            - img "Assistant linear timeline" [ref=e77]:
              - generic [ref=e81]: Assistant starts
              - generic [ref=e85]: Strategy branch
              - generic [ref=e89]: Plan tasks
              - generic [ref=e93]: Execute actions
              - generic [ref=e97]: Review results
            - generic [ref=e99]: No timeline tasks are available yet. Ask Concierge to create a plan or add a goal.
      - generic [ref=e100]:
        - heading "Quick actions" [level=2] [ref=e101]
        - generic [ref=e102]:
          - button "↗ What can you help me with?" [ref=e103] [cursor=pointer]:
            - generic [ref=e104]: ↗
            - generic [ref=e105]: What can you help me with?
          - button "↗ Show me what tasks are running." [ref=e106] [cursor=pointer]:
            - generic [ref=e107]: ↗
            - generic [ref=e108]: Show me what tasks are running.
          - button "↗ Create a 2-week sprint plan for a new feature." [ref=e109] [cursor=pointer]:
            - generic [ref=e110]: ↗
            - generic [ref=e111]: Create a 2-week sprint plan for a new feature.
          - button "↗ Summarise my last project context." [ref=e112] [cursor=pointer]:
            - generic [ref=e113]: ↗
            - generic [ref=e114]: Summarise my last project context.
          - button "↗ Help me prioritise my backlog." [ref=e115] [cursor=pointer]:
            - generic [ref=e116]: ↗
            - generic [ref=e117]: Help me prioritise my backlog.
      - generic [ref=e118]:
        - heading "Choose your outcome" [level=2] [ref=e119]
        - generic [ref=e120]:
          - generic [ref=e121]:
            - generic [ref=e122]:
              - generic [ref=e123]: 🎯
              - generic [ref=e124]:
                - generic [ref=e125]: Achieve Your Goals
                - generic [ref=e126]: Turn ambitions into results
            - paragraph [ref=e127]: Set high-level outcomes, let Concierge break them into prioritised tasks, and track progress automatically.
            - generic [ref=e128]:
              - button "↗ Create a 4-week goal to migrate our REST API to GraphQL." [ref=e129] [cursor=pointer]:
                - generic [ref=e130]: ↗
                - generic [ref=e131]: Create a 4-week goal to migrate our REST API to GraphQL.
              - button "↗ I want to reduce page load time by 40% — plan it out." [ref=e132] [cursor=pointer]:
                - generic [ref=e133]: ↗
                - generic [ref=e134]: I want to reduce page load time by 40% — plan it out.
              - button "↗ Set weekly goals for improving test coverage from 60% to 90%." [ref=e135] [cursor=pointer]:
                - generic [ref=e136]: ↗
                - generic [ref=e137]: Set weekly goals for improving test coverage from 60% to 90%.
            - link "Open Goals →" [ref=e138] [cursor=pointer]:
              - /url: /goals
          - generic [ref=e139]:
            - generic [ref=e140]:
              - generic [ref=e141]: ⚡
              - generic [ref=e142]:
                - generic [ref=e143]: Automate Your Work
                - generic [ref=e144]: Execute tasks without lifting a finger
            - paragraph [ref=e145]: "Run background tasks asynchronously: analyse files, generate code, process datasets, and get results delivered."
            - generic [ref=e146]:
              - button "↗ Analyse the CSV I uploaded and summarise the key trends." [ref=e147] [cursor=pointer]:
                - generic [ref=e148]: ↗
                - generic [ref=e149]: Analyse the CSV I uploaded and summarise the key trends.
              - button "↗ Generate a Python script to parse JSON logs and extract error counts." [ref=e150] [cursor=pointer]:
                - generic [ref=e151]: ↗
                - generic [ref=e152]: Generate a Python script to parse JSON logs and extract error counts.
              - button "↗ Read my uploaded spec and list all missing edge cases." [ref=e153] [cursor=pointer]:
                - generic [ref=e154]: ↗
                - generic [ref=e155]: Read my uploaded spec and list all missing edge cases.
            - link "Open Tasks →" [ref=e156] [cursor=pointer]:
              - /url: /tasks
          - generic [ref=e157]:
            - generic [ref=e158]:
              - generic [ref=e159]: 🗺️
              - generic [ref=e160]:
                - generic [ref=e161]: Plan Your Strategy
                - generic [ref=e162]: Think clearly, decide confidently
            - paragraph [ref=e163]: Apply OKRs, SWOT analysis, RICE scoring, and roadmapping frameworks. Let Concierge be your strategic thinking partner.
            - generic [ref=e164]:
              - button "↗ Write 3 OKRs for our product team for Q3 2026." [ref=e165] [cursor=pointer]:
                - generic [ref=e166]: ↗
                - generic [ref=e167]: Write 3 OKRs for our product team for Q3 2026.
              - button "↗ Run a SWOT analysis for a developer-tools startup." [ref=e168] [cursor=pointer]:
                - generic [ref=e169]: ↗
                - generic [ref=e170]: Run a SWOT analysis for a developer-tools startup.
              - button "↗ Build a 6-month product roadmap for a data-analytics platform." [ref=e171] [cursor=pointer]:
                - generic [ref=e172]: ↗
                - generic [ref=e173]: Build a 6-month product roadmap for a data-analytics platform.
            - link "Open Strategy →" [ref=e174] [cursor=pointer]:
              - /url: /strategy
          - generic [ref=e175]:
            - generic [ref=e176]:
              - generic [ref=e177]: 📁
              - generic [ref=e178]:
                - generic [ref=e179]: Manage Your Workspace
                - generic [ref=e180]: All your files and context in one place
            - paragraph [ref=e181]: Upload documents, images, CSVs, and PDFs. Attach them to projects and reference them in any conversation.
            - generic [ref=e182]:
              - button "↗ I've uploaded a PDF spec — summarise the authentication requirements." [ref=e183] [cursor=pointer]:
                - generic [ref=e184]: ↗
                - generic [ref=e185]: I've uploaded a PDF spec — summarise the authentication requirements.
              - button "↗ Attach the financial model CSV to the Q2 Planning project." [ref=e186] [cursor=pointer]:
                - generic [ref=e187]: ↗
                - generic [ref=e188]: Attach the financial model CSV to the Q2 Planning project.
              - button "↗ Transcribe the audio file I uploaded and summarise it." [ref=e189] [cursor=pointer]:
                - generic [ref=e190]: ↗
                - generic [ref=e191]: Transcribe the audio file I uploaded and summarise it.
            - link "Open Workspace →" [ref=e192] [cursor=pointer]:
              - /url: /workspace
      - generic [ref=e193]:
        - heading "More resources" [level=2] [ref=e194]
        - generic [ref=e195]:
          - link "📖 How-To Guide Learn core workflows" [ref=e196] [cursor=pointer]:
            - /url: /howto
            - generic [ref=e197]: 📖 How-To Guide
            - generic [ref=e198]: Learn core workflows
          - link "🔌 Integrations Browse plugins & tools" [ref=e199] [cursor=pointer]:
            - /url: /capabilities
            - generic [ref=e200]: 🔌 Integrations
            - generic [ref=e201]: Browse plugins & tools
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
> 16  |     await page.goto(BASE, { waitUntil: 'networkidle' });
      |                ^ Error: page.goto: Test timeout of 60000ms exceeded.
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
  78  |     await page.fill('textarea', 'what can you do?');
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
```