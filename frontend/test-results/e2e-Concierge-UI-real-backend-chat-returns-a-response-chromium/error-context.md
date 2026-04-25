# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e2e.spec.ts >> Concierge UI >> real backend chat returns a response
- Location: tests\e2e.spec.ts:258:7

# Error details

```
Test timeout of 60000ms exceeded.
```

```
Error: page.waitForResponse: Test timeout of 60000ms exceeded.
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
        - generic "message-1777046068638" [ref=e36]:
          - generic [ref=e37]: integration test
          - generic [ref=e38]: 4/24/2026, 11:54:28 AM
        - generic "message-1777046068639" [ref=e40]:
          - generic [ref=e41]: ⚠️ Failed to fetch
          - generic [ref=e42]: 4/24/2026, 11:54:28 AM
      - generic [ref=e44]:
        - generic [ref=e45]:
          - button "📎" [ref=e46] [cursor=pointer]
          - textbox "Message — Enter to send, Shift+Enter for newline" [ref=e47]
          - button "↑" [disabled] [ref=e48]
        - button "🗑 Clear memory" [ref=e50] [cursor=pointer]
  - alert [ref=e51]:
    - generic "Failed to fetch" [ref=e52]
    - button "Dismiss error" [ref=e53] [cursor=pointer]: ✕
  - main [ref=e54]:
    - generic [ref=e55]:
      - generic [ref=e57]:
        - heading "Build smarter workflows, see results visually." [level=1] [ref=e58]:
          - text: Build smarter workflows,
          - text: see results visually.
        - paragraph [ref=e59]: Ask me to plan, execute, and monitor your work. I can also surface photo-driven insights, review your files, and turn your goals into a clear visual timeline.
        - generic [ref=e60]:
          - button "↗ Show me my current roadmap" [ref=e61] [cursor=pointer]:
            - generic [ref=e62]: ↗
            - generic [ref=e63]: Show me my current roadmap
          - button "↗ Create a visual status update" [ref=e64] [cursor=pointer]:
            - generic [ref=e65]: ↗
            - generic [ref=e66]: Create a visual status update
          - button "↗ Generate a media summary" [ref=e67] [cursor=pointer]:
            - generic [ref=e68]: ↗
            - generic [ref=e69]: Generate a media summary
      - generic [ref=e70]:
        - generic [ref=e72]:
          - generic [ref=e73]: Live Timeline
          - heading "See Concierge planning in one responsive view" [level=2] [ref=e74]
          - paragraph [ref=e75]: Your current plan updates, task progress, and visual graph are surfaced in a mobile-first timeline card that spans the full width of the landing page.
        - generic [ref=e76]:
          - generic [ref=e77]:
            - generic [ref=e78]:
              - paragraph [ref=e79]: Assistant timeline
              - heading "Assistant linear timeline" [level=2] [ref=e80]
              - paragraph [ref=e81]: Visualize the assistant's strategy as a linear timeline with tasks and progress.
            - button "View full timeline" [ref=e82] [cursor=pointer]
          - generic [ref=e83]:
            - img "Assistant linear timeline" [ref=e85]:
              - generic [ref=e89]: Assistant starts
              - generic [ref=e93]: Strategy branch
              - generic [ref=e97]: Plan tasks
              - generic [ref=e101]: Execute actions
              - generic [ref=e105]: Review results
            - generic [ref=e107]: No timeline tasks are available yet. Ask Concierge to create a plan or add a goal.
      - generic [ref=e108]:
        - heading "Quick actions" [level=2] [ref=e109]
        - generic [ref=e110]:
          - button "↗ What can you help me with?" [ref=e111] [cursor=pointer]:
            - generic [ref=e112]: ↗
            - generic [ref=e113]: What can you help me with?
          - button "↗ Show me what tasks are running." [ref=e114] [cursor=pointer]:
            - generic [ref=e115]: ↗
            - generic [ref=e116]: Show me what tasks are running.
          - button "↗ Create a 2-week sprint plan for a new feature." [ref=e117] [cursor=pointer]:
            - generic [ref=e118]: ↗
            - generic [ref=e119]: Create a 2-week sprint plan for a new feature.
          - button "↗ Summarise my last project context." [ref=e120] [cursor=pointer]:
            - generic [ref=e121]: ↗
            - generic [ref=e122]: Summarise my last project context.
          - button "↗ Help me prioritise my backlog." [ref=e123] [cursor=pointer]:
            - generic [ref=e124]: ↗
            - generic [ref=e125]: Help me prioritise my backlog.
      - generic [ref=e126]:
        - heading "Choose your outcome" [level=2] [ref=e127]
        - generic [ref=e128]:
          - generic [ref=e129]:
            - generic [ref=e130]:
              - generic [ref=e131]: 🎯
              - generic [ref=e132]:
                - generic [ref=e133]: Achieve Your Goals
                - generic [ref=e134]: Turn ambitions into results
            - paragraph [ref=e135]: Set high-level outcomes, let Concierge break them into prioritised tasks, and track progress automatically.
            - generic [ref=e136]:
              - button "↗ Create a 4-week goal to migrate our REST API to GraphQL." [ref=e137] [cursor=pointer]:
                - generic [ref=e138]: ↗
                - generic [ref=e139]: Create a 4-week goal to migrate our REST API to GraphQL.
              - button "↗ I want to reduce page load time by 40% — plan it out." [ref=e140] [cursor=pointer]:
                - generic [ref=e141]: ↗
                - generic [ref=e142]: I want to reduce page load time by 40% — plan it out.
              - button "↗ Set weekly goals for improving test coverage from 60% to 90%." [ref=e143] [cursor=pointer]:
                - generic [ref=e144]: ↗
                - generic [ref=e145]: Set weekly goals for improving test coverage from 60% to 90%.
            - link "Open Goals →" [ref=e146] [cursor=pointer]:
              - /url: /goals
          - generic [ref=e147]:
            - generic [ref=e148]:
              - generic [ref=e149]: ⚡
              - generic [ref=e150]:
                - generic [ref=e151]: Automate Your Work
                - generic [ref=e152]: Execute tasks without lifting a finger
            - paragraph [ref=e153]: "Run background tasks asynchronously: analyse files, generate code, process datasets, and get results delivered."
            - generic [ref=e154]:
              - button "↗ Analyse the CSV I uploaded and summarise the key trends." [ref=e155] [cursor=pointer]:
                - generic [ref=e156]: ↗
                - generic [ref=e157]: Analyse the CSV I uploaded and summarise the key trends.
              - button "↗ Generate a Python script to parse JSON logs and extract error counts." [ref=e158] [cursor=pointer]:
                - generic [ref=e159]: ↗
                - generic [ref=e160]: Generate a Python script to parse JSON logs and extract error counts.
              - button "↗ Read my uploaded spec and list all missing edge cases." [ref=e161] [cursor=pointer]:
                - generic [ref=e162]: ↗
                - generic [ref=e163]: Read my uploaded spec and list all missing edge cases.
            - link "Open Tasks →" [ref=e164] [cursor=pointer]:
              - /url: /tasks
          - generic [ref=e165]:
            - generic [ref=e166]:
              - generic [ref=e167]: 🗺️
              - generic [ref=e168]:
                - generic [ref=e169]: Plan Your Strategy
                - generic [ref=e170]: Think clearly, decide confidently
            - paragraph [ref=e171]: Apply OKRs, SWOT analysis, RICE scoring, and roadmapping frameworks. Let Concierge be your strategic thinking partner.
            - generic [ref=e172]:
              - button "↗ Write 3 OKRs for our product team for Q3 2026." [ref=e173] [cursor=pointer]:
                - generic [ref=e174]: ↗
                - generic [ref=e175]: Write 3 OKRs for our product team for Q3 2026.
              - button "↗ Run a SWOT analysis for a developer-tools startup." [ref=e176] [cursor=pointer]:
                - generic [ref=e177]: ↗
                - generic [ref=e178]: Run a SWOT analysis for a developer-tools startup.
              - button "↗ Build a 6-month product roadmap for a data-analytics platform." [ref=e179] [cursor=pointer]:
                - generic [ref=e180]: ↗
                - generic [ref=e181]: Build a 6-month product roadmap for a data-analytics platform.
            - link "Open Strategy →" [ref=e182] [cursor=pointer]:
              - /url: /strategy
          - generic [ref=e183]:
            - generic [ref=e184]:
              - generic [ref=e185]: 📁
              - generic [ref=e186]:
                - generic [ref=e187]: Manage Your Workspace
                - generic [ref=e188]: All your files and context in one place
            - paragraph [ref=e189]: Upload documents, images, CSVs, and PDFs. Attach them to projects and reference them in any conversation.
            - generic [ref=e190]:
              - button "↗ I've uploaded a PDF spec — summarise the authentication requirements." [ref=e191] [cursor=pointer]:
                - generic [ref=e192]: ↗
                - generic [ref=e193]: I've uploaded a PDF spec — summarise the authentication requirements.
              - button "↗ Attach the financial model CSV to the Q2 Planning project." [ref=e194] [cursor=pointer]:
                - generic [ref=e195]: ↗
                - generic [ref=e196]: Attach the financial model CSV to the Q2 Planning project.
              - button "↗ Transcribe the audio file I uploaded and summarise it." [ref=e197] [cursor=pointer]:
                - generic [ref=e198]: ↗
                - generic [ref=e199]: Transcribe the audio file I uploaded and summarise it.
            - link "Open Workspace →" [ref=e200] [cursor=pointer]:
              - /url: /workspace
      - generic [ref=e201]:
        - heading "More resources" [level=2] [ref=e202]
        - generic [ref=e203]:
          - link "📖 How-To Guide Learn core workflows" [ref=e204] [cursor=pointer]:
            - /url: /howto
            - generic [ref=e205]: 📖 How-To Guide
            - generic [ref=e206]: Learn core workflows
          - link "🔌 Integrations Browse plugins & tools" [ref=e207] [cursor=pointer]:
            - /url: /capabilities
            - generic [ref=e208]: 🔌 Integrations
            - generic [ref=e209]: Browse plugins & tools
```

# Test source

```ts
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
  242 |         body: JSON.stringify({
  243 |           status: 'success',
  244 |           data: [
  245 |             { id: 'job2', label: 'Goal job', status: 'queued', started_at: now, statusObj: { status: 'queued' } }
  246 |           ]
  247 |         }),
  248 |       })
  249 |     );
  250 |     await page.goto(BASE + '/goals', { waitUntil: 'networkidle' });
  251 |     await expect(page.locator('text=Goal job')).toBeVisible();
  252 |     await expect(page.locator('text=elapsed')).toBeVisible();
  253 |     await page.click('text=show details');
  254 |     await expect(page.locator('text=Goal job')).toBeVisible();
  255 |   });
  256 | 
  257 | 
  258 |   test('real backend chat returns a response', async ({ page }) => {
  259 |     await page.goto(BASE, { waitUntil: 'networkidle' });
  260 |     // send a message without stubbing to ensure backend interaction
  261 |     const message = 'integration test';
  262 | 
  263 |     // intercept the response so we can check it even if the UI lags
> 264 |     const responsePromise = page.waitForResponse(
      |                                  ^ Error: page.waitForResponse: Test timeout of 60000ms exceeded.
  265 |       (resp) => resp.url().includes('/api/v1/concierge/message') && resp.request().method() === 'POST',
  266 |       { timeout: 90000 }
  267 |     );
  268 | 
  269 |     await page.fill('textarea', message);
  270 |     await page.keyboard.press('Enter');
  271 | 
  272 |     const resp = await responsePromise;
  273 |     expect(resp.status()).toBe(200);
  274 |     const body = await resp.json();
  275 |     expect(body.status).toBe('success');
  276 |     // make sure the backend actually returned something useful
  277 |     expect(body.data).toBeDefined();
  278 |   });
  279 | });
  280 | 
```