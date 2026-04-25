# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e2e.spec.ts >> Concierge UI >> search trigger returns results using ResearchAgent
- Location: tests\e2e.spec.ts:92:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text=Searching the web for')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('text=Searching the web for')

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
        - img "timeline graph" [ref=e31] [cursor=pointer]
        - button "▾" [ref=e32] [cursor=pointer]
      - generic [ref=e34]:
        - generic "message-1777045926183" [ref=e36]:
          - generic [ref=e37]: search for foo
          - generic [ref=e38]: 4/24/2026, 11:52:06 AM
        - generic "message-1777045926184" [ref=e40]:
          - generic [ref=e41]: …
          - generic [ref=e42]: 4/24/2026, 11:52:06 AM
      - generic [ref=e44]:
        - generic [ref=e45]:
          - button "📎" [ref=e46] [cursor=pointer]
          - textbox "Message — Enter to send, Shift+Enter for newline" [ref=e47]
          - button "↑" [disabled] [ref=e48]
        - button "🗑 Clear memory" [ref=e50] [cursor=pointer]
  - main [ref=e51]:
    - generic [ref=e52]:
      - generic [ref=e54]:
        - heading "Build smarter workflows, see results visually." [level=1] [ref=e55]:
          - text: Build smarter workflows,
          - text: see results visually.
        - paragraph [ref=e56]: Ask me to plan, execute, and monitor your work. I can also surface photo-driven insights, review your files, and turn your goals into a clear visual timeline.
        - generic [ref=e57]:
          - button "↗ Show me my current roadmap" [ref=e58] [cursor=pointer]:
            - generic [ref=e59]: ↗
            - generic [ref=e60]: Show me my current roadmap
          - button "↗ Create a visual status update" [ref=e61] [cursor=pointer]:
            - generic [ref=e62]: ↗
            - generic [ref=e63]: Create a visual status update
          - button "↗ Generate a media summary" [ref=e64] [cursor=pointer]:
            - generic [ref=e65]: ↗
            - generic [ref=e66]: Generate a media summary
      - generic [ref=e67]:
        - generic [ref=e69]:
          - generic [ref=e70]: Live Timeline
          - heading "See Concierge planning in one responsive view" [level=2] [ref=e71]
          - paragraph [ref=e72]: Your current plan updates, task progress, and visual graph are surfaced in a mobile-first timeline card that spans the full width of the landing page.
        - generic [ref=e73]:
          - generic [ref=e74]:
            - generic [ref=e75]:
              - paragraph [ref=e76]: Assistant timeline
              - heading "Assistant linear timeline" [level=2] [ref=e77]
              - paragraph [ref=e78]: Visualize the assistant's strategy as a linear timeline with tasks and progress.
            - button "View full timeline" [ref=e79] [cursor=pointer]
          - generic [ref=e80]:
            - img "Assistant linear timeline" [ref=e82]:
              - generic [ref=e86]: Assistant starts
              - generic [ref=e90]: Strategy branch
              - generic [ref=e94]: Plan tasks
              - generic [ref=e98]: Execute actions
              - generic [ref=e102]: Review results
            - generic [ref=e104]: No timeline tasks are available yet. Ask Concierge to create a plan or add a goal.
      - generic [ref=e105]:
        - heading "Quick actions" [level=2] [ref=e106]
        - generic [ref=e107]:
          - button "↗ What can you help me with?" [ref=e108] [cursor=pointer]:
            - generic [ref=e109]: ↗
            - generic [ref=e110]: What can you help me with?
          - button "↗ Show me what tasks are running." [ref=e111] [cursor=pointer]:
            - generic [ref=e112]: ↗
            - generic [ref=e113]: Show me what tasks are running.
          - button "↗ Create a 2-week sprint plan for a new feature." [ref=e114] [cursor=pointer]:
            - generic [ref=e115]: ↗
            - generic [ref=e116]: Create a 2-week sprint plan for a new feature.
          - button "↗ Summarise my last project context." [ref=e117] [cursor=pointer]:
            - generic [ref=e118]: ↗
            - generic [ref=e119]: Summarise my last project context.
          - button "↗ Help me prioritise my backlog." [ref=e120] [cursor=pointer]:
            - generic [ref=e121]: ↗
            - generic [ref=e122]: Help me prioritise my backlog.
      - generic [ref=e123]:
        - heading "Choose your outcome" [level=2] [ref=e124]
        - generic [ref=e125]:
          - generic [ref=e126]:
            - generic [ref=e127]:
              - generic [ref=e128]: 🎯
              - generic [ref=e129]:
                - generic [ref=e130]: Achieve Your Goals
                - generic [ref=e131]: Turn ambitions into results
            - paragraph [ref=e132]: Set high-level outcomes, let Concierge break them into prioritised tasks, and track progress automatically.
            - generic [ref=e133]:
              - button "↗ Create a 4-week goal to migrate our REST API to GraphQL." [ref=e134] [cursor=pointer]:
                - generic [ref=e135]: ↗
                - generic [ref=e136]: Create a 4-week goal to migrate our REST API to GraphQL.
              - button "↗ I want to reduce page load time by 40% — plan it out." [ref=e137] [cursor=pointer]:
                - generic [ref=e138]: ↗
                - generic [ref=e139]: I want to reduce page load time by 40% — plan it out.
              - button "↗ Set weekly goals for improving test coverage from 60% to 90%." [ref=e140] [cursor=pointer]:
                - generic [ref=e141]: ↗
                - generic [ref=e142]: Set weekly goals for improving test coverage from 60% to 90%.
            - link "Open Goals →" [ref=e143] [cursor=pointer]:
              - /url: /goals
          - generic [ref=e144]:
            - generic [ref=e145]:
              - generic [ref=e146]: ⚡
              - generic [ref=e147]:
                - generic [ref=e148]: Automate Your Work
                - generic [ref=e149]: Execute tasks without lifting a finger
            - paragraph [ref=e150]: "Run background tasks asynchronously: analyse files, generate code, process datasets, and get results delivered."
            - generic [ref=e151]:
              - button "↗ Analyse the CSV I uploaded and summarise the key trends." [ref=e152] [cursor=pointer]:
                - generic [ref=e153]: ↗
                - generic [ref=e154]: Analyse the CSV I uploaded and summarise the key trends.
              - button "↗ Generate a Python script to parse JSON logs and extract error counts." [ref=e155] [cursor=pointer]:
                - generic [ref=e156]: ↗
                - generic [ref=e157]: Generate a Python script to parse JSON logs and extract error counts.
              - button "↗ Read my uploaded spec and list all missing edge cases." [ref=e158] [cursor=pointer]:
                - generic [ref=e159]: ↗
                - generic [ref=e160]: Read my uploaded spec and list all missing edge cases.
            - link "Open Tasks →" [ref=e161] [cursor=pointer]:
              - /url: /tasks
          - generic [ref=e162]:
            - generic [ref=e163]:
              - generic [ref=e164]: 🗺️
              - generic [ref=e165]:
                - generic [ref=e166]: Plan Your Strategy
                - generic [ref=e167]: Think clearly, decide confidently
            - paragraph [ref=e168]: Apply OKRs, SWOT analysis, RICE scoring, and roadmapping frameworks. Let Concierge be your strategic thinking partner.
            - generic [ref=e169]:
              - button "↗ Write 3 OKRs for our product team for Q3 2026." [ref=e170] [cursor=pointer]:
                - generic [ref=e171]: ↗
                - generic [ref=e172]: Write 3 OKRs for our product team for Q3 2026.
              - button "↗ Run a SWOT analysis for a developer-tools startup." [ref=e173] [cursor=pointer]:
                - generic [ref=e174]: ↗
                - generic [ref=e175]: Run a SWOT analysis for a developer-tools startup.
              - button "↗ Build a 6-month product roadmap for a data-analytics platform." [ref=e176] [cursor=pointer]:
                - generic [ref=e177]: ↗
                - generic [ref=e178]: Build a 6-month product roadmap for a data-analytics platform.
            - link "Open Strategy →" [ref=e179] [cursor=pointer]:
              - /url: /strategy
          - generic [ref=e180]:
            - generic [ref=e181]:
              - generic [ref=e182]: 📁
              - generic [ref=e183]:
                - generic [ref=e184]: Manage Your Workspace
                - generic [ref=e185]: All your files and context in one place
            - paragraph [ref=e186]: Upload documents, images, CSVs, and PDFs. Attach them to projects and reference them in any conversation.
            - generic [ref=e187]:
              - button "↗ I've uploaded a PDF spec — summarise the authentication requirements." [ref=e188] [cursor=pointer]:
                - generic [ref=e189]: ↗
                - generic [ref=e190]: I've uploaded a PDF spec — summarise the authentication requirements.
              - button "↗ Attach the financial model CSV to the Q2 Planning project." [ref=e191] [cursor=pointer]:
                - generic [ref=e192]: ↗
                - generic [ref=e193]: Attach the financial model CSV to the Q2 Planning project.
              - button "↗ Transcribe the audio file I uploaded and summarise it." [ref=e194] [cursor=pointer]:
                - generic [ref=e195]: ↗
                - generic [ref=e196]: Transcribe the audio file I uploaded and summarise it.
            - link "Open Workspace →" [ref=e197] [cursor=pointer]:
              - /url: /workspace
      - generic [ref=e198]:
        - heading "More resources" [level=2] [ref=e199]
        - generic [ref=e200]:
          - link "📖 How-To Guide Learn core workflows" [ref=e201] [cursor=pointer]:
            - /url: /howto
            - generic [ref=e202]: 📖 How-To Guide
            - generic [ref=e203]: Learn core workflows
          - link "🔌 Integrations Browse plugins & tools" [ref=e204] [cursor=pointer]:
            - /url: /capabilities
            - generic [ref=e205]: 🔌 Integrations
            - generic [ref=e206]: Browse plugins & tools
```

# Test source

```ts
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
> 105 |     await expect(page.locator('text=Searching the web for')).toBeVisible();
      |                                                              ^ Error: expect(locator).toBeVisible() failed
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
  179 |   test('navigation includes how-to and page renders', async ({ page }) => {
  180 |     await page.goto(BASE, { waitUntil: 'networkidle' });
  181 |     // confirm link is present in header (label was renamed to "Guide")
  182 |     const link = page.locator('nav >> text=Guide');
  183 |     await expect(link).toBeVisible();
  184 |     await link.click();
  185 |     // new page should have the heading we added (emoji/casing may vary)
  186 |     await expect(page.locator('h1')).toContainText('How to Use Concierge');
  187 |   });
  188 | 
  189 |   test('multi-media response triggers full-screen stage', async ({ page }) => {
  190 |     await page.goto(BASE, { waitUntil: 'networkidle' });
  191 |     // stub API to include two media URLs (an image and a video)
  192 |     await page.route('**/api/v1/concierge/message', (route) =>
  193 |       route.fulfill({
  194 |         status: 200,
  195 |         contentType: 'application/json',
  196 |         body: JSON.stringify({
  197 |           status: 'success',
  198 |           data: { content: 'https://example.com/a.png https://example.com/b.mp4' },
  199 |         }),
  200 |       })
  201 |     );
  202 | 
  203 |     await page.fill('textarea', 'show me media');
  204 |     await page.keyboard.press('Enter');
  205 | 
```