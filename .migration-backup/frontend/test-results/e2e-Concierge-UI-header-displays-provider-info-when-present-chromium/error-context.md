# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e2e.spec.ts >> Concierge UI >> header displays provider info when present
- Location: tests\e2e.spec.ts:127:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('Provider: gemini', { exact: true })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByText('Provider: gemini', { exact: true })

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
        - generic "message-1777045955505" [ref=e36]:
          - generic [ref=e37]: hey
          - generic [ref=e38]: 4/24/2026, 11:52:35 AM
        - generic "message-1777045955506" [ref=e40]:
          - generic [ref=e41]: yo
          - generic [ref=e42]: "Provider: gemini (switched)"
          - button "▸ details" [ref=e44] [cursor=pointer]:
            - generic [ref=e45]: ▸
            - text: details
          - generic [ref=e46]: 4/24/2026, 11:52:35 AM
      - generic [ref=e48]:
        - generic [ref=e49]:
          - button "📎" [ref=e50] [cursor=pointer]
          - textbox "Message — Enter to send, Shift+Enter for newline" [ref=e51]
          - button "↑" [disabled] [ref=e52]
        - button "🗑 Clear memory" [ref=e54] [cursor=pointer]
  - main [ref=e55]:
    - generic [ref=e56]:
      - generic [ref=e58]:
        - heading "Build smarter workflows, see results visually." [level=1] [ref=e59]:
          - text: Build smarter workflows,
          - text: see results visually.
        - paragraph [ref=e60]: Ask me to plan, execute, and monitor your work. I can also surface photo-driven insights, review your files, and turn your goals into a clear visual timeline.
        - generic [ref=e61]:
          - button "↗ Show me my current roadmap" [ref=e62] [cursor=pointer]:
            - generic [ref=e63]: ↗
            - generic [ref=e64]: Show me my current roadmap
          - button "↗ Create a visual status update" [ref=e65] [cursor=pointer]:
            - generic [ref=e66]: ↗
            - generic [ref=e67]: Create a visual status update
          - button "↗ Generate a media summary" [ref=e68] [cursor=pointer]:
            - generic [ref=e69]: ↗
            - generic [ref=e70]: Generate a media summary
      - generic [ref=e71]:
        - generic [ref=e73]:
          - generic [ref=e74]: Live Timeline
          - heading "See Concierge planning in one responsive view" [level=2] [ref=e75]
          - paragraph [ref=e76]: Your current plan updates, task progress, and visual graph are surfaced in a mobile-first timeline card that spans the full width of the landing page.
        - generic [ref=e77]:
          - generic [ref=e78]:
            - generic [ref=e79]:
              - paragraph [ref=e80]: Assistant timeline
              - heading "Assistant linear timeline" [level=2] [ref=e81]
              - paragraph [ref=e82]: Visualize the assistant's strategy as a linear timeline with tasks and progress.
            - button "View full timeline" [ref=e83] [cursor=pointer]
          - generic [ref=e84]:
            - img "Assistant linear timeline" [ref=e86]:
              - generic [ref=e90]: Assistant starts
              - generic [ref=e94]: Strategy branch
              - generic [ref=e98]: Plan tasks
              - generic [ref=e102]: Execute actions
              - generic [ref=e106]: Review results
            - generic [ref=e108]: No timeline tasks are available yet. Ask Concierge to create a plan or add a goal.
      - generic [ref=e109]:
        - heading "Quick actions" [level=2] [ref=e110]
        - generic [ref=e111]:
          - button "↗ What can you help me with?" [ref=e112] [cursor=pointer]:
            - generic [ref=e113]: ↗
            - generic [ref=e114]: What can you help me with?
          - button "↗ Show me what tasks are running." [ref=e115] [cursor=pointer]:
            - generic [ref=e116]: ↗
            - generic [ref=e117]: Show me what tasks are running.
          - button "↗ Create a 2-week sprint plan for a new feature." [ref=e118] [cursor=pointer]:
            - generic [ref=e119]: ↗
            - generic [ref=e120]: Create a 2-week sprint plan for a new feature.
          - button "↗ Summarise my last project context." [ref=e121] [cursor=pointer]:
            - generic [ref=e122]: ↗
            - generic [ref=e123]: Summarise my last project context.
          - button "↗ Help me prioritise my backlog." [ref=e124] [cursor=pointer]:
            - generic [ref=e125]: ↗
            - generic [ref=e126]: Help me prioritise my backlog.
      - generic [ref=e127]:
        - heading "Choose your outcome" [level=2] [ref=e128]
        - generic [ref=e129]:
          - generic [ref=e130]:
            - generic [ref=e131]:
              - generic [ref=e132]: 🎯
              - generic [ref=e133]:
                - generic [ref=e134]: Achieve Your Goals
                - generic [ref=e135]: Turn ambitions into results
            - paragraph [ref=e136]: Set high-level outcomes, let Concierge break them into prioritised tasks, and track progress automatically.
            - generic [ref=e137]:
              - button "↗ Create a 4-week goal to migrate our REST API to GraphQL." [ref=e138] [cursor=pointer]:
                - generic [ref=e139]: ↗
                - generic [ref=e140]: Create a 4-week goal to migrate our REST API to GraphQL.
              - button "↗ I want to reduce page load time by 40% — plan it out." [ref=e141] [cursor=pointer]:
                - generic [ref=e142]: ↗
                - generic [ref=e143]: I want to reduce page load time by 40% — plan it out.
              - button "↗ Set weekly goals for improving test coverage from 60% to 90%." [ref=e144] [cursor=pointer]:
                - generic [ref=e145]: ↗
                - generic [ref=e146]: Set weekly goals for improving test coverage from 60% to 90%.
            - link "Open Goals →" [ref=e147] [cursor=pointer]:
              - /url: /goals
          - generic [ref=e148]:
            - generic [ref=e149]:
              - generic [ref=e150]: ⚡
              - generic [ref=e151]:
                - generic [ref=e152]: Automate Your Work
                - generic [ref=e153]: Execute tasks without lifting a finger
            - paragraph [ref=e154]: "Run background tasks asynchronously: analyse files, generate code, process datasets, and get results delivered."
            - generic [ref=e155]:
              - button "↗ Analyse the CSV I uploaded and summarise the key trends." [ref=e156] [cursor=pointer]:
                - generic [ref=e157]: ↗
                - generic [ref=e158]: Analyse the CSV I uploaded and summarise the key trends.
              - button "↗ Generate a Python script to parse JSON logs and extract error counts." [ref=e159] [cursor=pointer]:
                - generic [ref=e160]: ↗
                - generic [ref=e161]: Generate a Python script to parse JSON logs and extract error counts.
              - button "↗ Read my uploaded spec and list all missing edge cases." [ref=e162] [cursor=pointer]:
                - generic [ref=e163]: ↗
                - generic [ref=e164]: Read my uploaded spec and list all missing edge cases.
            - link "Open Tasks →" [ref=e165] [cursor=pointer]:
              - /url: /tasks
          - generic [ref=e166]:
            - generic [ref=e167]:
              - generic [ref=e168]: 🗺️
              - generic [ref=e169]:
                - generic [ref=e170]: Plan Your Strategy
                - generic [ref=e171]: Think clearly, decide confidently
            - paragraph [ref=e172]: Apply OKRs, SWOT analysis, RICE scoring, and roadmapping frameworks. Let Concierge be your strategic thinking partner.
            - generic [ref=e173]:
              - button "↗ Write 3 OKRs for our product team for Q3 2026." [ref=e174] [cursor=pointer]:
                - generic [ref=e175]: ↗
                - generic [ref=e176]: Write 3 OKRs for our product team for Q3 2026.
              - button "↗ Run a SWOT analysis for a developer-tools startup." [ref=e177] [cursor=pointer]:
                - generic [ref=e178]: ↗
                - generic [ref=e179]: Run a SWOT analysis for a developer-tools startup.
              - button "↗ Build a 6-month product roadmap for a data-analytics platform." [ref=e180] [cursor=pointer]:
                - generic [ref=e181]: ↗
                - generic [ref=e182]: Build a 6-month product roadmap for a data-analytics platform.
            - link "Open Strategy →" [ref=e183] [cursor=pointer]:
              - /url: /strategy
          - generic [ref=e184]:
            - generic [ref=e185]:
              - generic [ref=e186]: 📁
              - generic [ref=e187]:
                - generic [ref=e188]: Manage Your Workspace
                - generic [ref=e189]: All your files and context in one place
            - paragraph [ref=e190]: Upload documents, images, CSVs, and PDFs. Attach them to projects and reference them in any conversation.
            - generic [ref=e191]:
              - button "↗ I've uploaded a PDF spec — summarise the authentication requirements." [ref=e192] [cursor=pointer]:
                - generic [ref=e193]: ↗
                - generic [ref=e194]: I've uploaded a PDF spec — summarise the authentication requirements.
              - button "↗ Attach the financial model CSV to the Q2 Planning project." [ref=e195] [cursor=pointer]:
                - generic [ref=e196]: ↗
                - generic [ref=e197]: Attach the financial model CSV to the Q2 Planning project.
              - button "↗ Transcribe the audio file I uploaded and summarise it." [ref=e198] [cursor=pointer]:
                - generic [ref=e199]: ↗
                - generic [ref=e200]: Transcribe the audio file I uploaded and summarise it.
            - link "Open Workspace →" [ref=e201] [cursor=pointer]:
              - /url: /workspace
      - generic [ref=e202]:
        - heading "More resources" [level=2] [ref=e203]
        - generic [ref=e204]:
          - link "📖 How-To Guide Learn core workflows" [ref=e205] [cursor=pointer]:
            - /url: /howto
            - generic [ref=e206]: 📖 How-To Guide
            - generic [ref=e207]: Learn core workflows
          - link "🔌 Integrations Browse plugins & tools" [ref=e208] [cursor=pointer]:
            - /url: /capabilities
            - generic [ref=e209]: 🔌 Integrations
            - generic [ref=e210]: Browse plugins & tools
```

# Test source

```ts
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
> 141 |     await expect(page.getByText('Provider: gemini', { exact: true })).toBeVisible();
      |                                                                       ^ Error: expect(locator).toBeVisible() failed
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
  206 |     // the stage should auto-expand to full-screen mode (button title changes)
  207 |     const toggle = page.locator('role=button[title="Restore size"]');
  208 |     await expect(toggle).toBeVisible();
  209 |     // verify both media elements exist inside the stage
  210 |     await expect(page.locator('img[src*="a.png"]')).toBeVisible();
  211 |     await expect(page.locator('video[src*="b.mp4"]')).toBeVisible();
  212 |   });
  213 | 
  214 |   test('tasks page shows processing banner when jobs exist', async ({ page }) => {
  215 |     // stub tasks API to simulate an active job
  216 |     const now = new Date().toISOString();
  217 |     await page.route('**/api/v1/tasks', route =>
  218 |       route.fulfill({
  219 |         status: 200,
  220 |         contentType: 'application/json',
  221 |         body: JSON.stringify({
  222 |           status: 'success',
  223 |           data: [
  224 |             { id: 'job1', label: 'Example job', status: 'running', started_at: now, statusObj: { status: 'running' } }
  225 |           ]
  226 |         }),
  227 |       })
  228 |     );
  229 |     await page.goto(BASE + '/tasks', { waitUntil: 'networkidle' });
  230 |     await expect(page.locator('text=Example job')).toBeVisible();
  231 |     await expect(page.locator('text=elapsed')).toBeVisible();
  232 |     await page.click('text=show details');
  233 |     await expect(page.locator('text=Example job')).toBeVisible();
  234 |   });
  235 | 
  236 |   test('goals page shows processing banner when jobs exist', async ({ page }) => {
  237 |     const now = new Date().toISOString();
  238 |     await page.route('**/api/v1/tasks', route =>
  239 |       route.fulfill({
  240 |         status: 200,
  241 |         contentType: 'application/json',
```