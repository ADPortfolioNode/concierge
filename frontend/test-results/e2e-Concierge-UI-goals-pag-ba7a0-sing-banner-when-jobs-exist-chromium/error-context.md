# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e2e.spec.ts >> Concierge UI >> goals page shows processing banner when jobs exist
- Location: tests\e2e.spec.ts:236:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text=Goal job')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('text=Goal job')

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
      - generic "message-welcome" [ref=e36]:
        - generic [ref=e37]: Welcome. I'm ready when you are. What would you like to work on today?
        - generic [ref=e38]: 4/24/2026, 11:54:01 AM
      - generic [ref=e40]:
        - generic [ref=e41]:
          - button "📎" [ref=e42] [cursor=pointer]
          - textbox "Message — Enter to send, Shift+Enter for newline" [ref=e43]
          - button "↑" [disabled] [ref=e44]
        - button "🗑 Clear memory" [ref=e46] [cursor=pointer]
  - main [ref=e47]:
    - generic [ref=e48]:
      - heading "🎯 Goals" [level=1] [ref=e49]
      - paragraph [ref=e50]: Goals are high-level outcomes. Describe what you want to achieve and Concierge will decompose it into a prioritised task tree, run specialist agents, and synthesise a final report. Click any prompt below to start a goal in the chat.
      - generic [ref=e51]:
        - generic [ref=e52]:
          - generic [ref=e53]: STEP 1
          - generic [ref=e54]: Describe outcome
          - generic [ref=e55]: Be specific — include a timeframe and measurable result.
        - generic [ref=e56]:
          - generic [ref=e57]: STEP 2
          - generic [ref=e58]: Planner decomposes
          - generic [ref=e59]: Goal → prioritised tasks with dependencies.
        - generic [ref=e60]:
          - generic [ref=e61]: STEP 3
          - generic [ref=e62]: Agents execute
          - generic [ref=e63]: Research, Coding, and Critic agents run in parallel.
        - generic [ref=e64]:
          - generic [ref=e65]: STEP 4
          - generic [ref=e66]: Synthesizer reports
          - generic [ref=e67]: Key points, risks, and recommendations returned.
      - generic [ref=e68]:
        - heading "🚀 Launch & delivery" [level=2] [ref=e69]
        - generic [ref=e70]:
          - button "\"Create a 4-week goal to launch a public-facing REST API for our SaaS product.\" Click to use →" [ref=e71] [cursor=pointer]:
            - generic [ref=e72]: "\"Create a 4-week goal to launch a public-facing REST API for our SaaS product.\""
            - generic [ref=e73]: Click to use →
          - button "\"Plan the rollout of a new authentication system — list tasks, risks, and milestones.\" Click to use →" [ref=e74] [cursor=pointer]:
            - generic [ref=e75]: "\"Plan the rollout of a new authentication system — list tasks, risks, and milestones.\""
            - generic [ref=e76]: Click to use →
          - button "\"I need to ship a mobile MVP in 6 weeks. Break it into weekly goals.\" Click to use →" [ref=e77] [cursor=pointer]:
            - generic [ref=e78]: "\"I need to ship a mobile MVP in 6 weeks. Break it into weekly goals.\""
            - generic [ref=e79]: Click to use →
          - button "\"Map out the go-to-market plan for the v2.0 release.\" Click to use →" [ref=e80] [cursor=pointer]:
            - generic [ref=e81]: "\"Map out the go-to-market plan for the v2.0 release.\""
            - generic [ref=e82]: Click to use →
      - generic [ref=e83]:
        - heading "⚙️ Technical improvement" [level=2] [ref=e84]
        - generic [ref=e85]:
          - button "\"Set a goal to reduce CI/CD pipeline time from 12 minutes to under 5.\" Click to use →" [ref=e86] [cursor=pointer]:
            - generic [ref=e87]: "\"Set a goal to reduce CI/CD pipeline time from 12 minutes to under 5.\""
            - generic [ref=e88]: Click to use →
          - button "\"Improve test coverage from 55% to 85% across all core modules in 3 weeks.\" Click to use →" [ref=e89] [cursor=pointer]:
            - generic [ref=e90]: "\"Improve test coverage from 55% to 85% across all core modules in 3 weeks.\""
            - generic [ref=e91]: Click to use →
          - button "\"Plan a database schema migration to support multi-tenancy.\" Click to use →" [ref=e92] [cursor=pointer]:
            - generic [ref=e93]: "\"Plan a database schema migration to support multi-tenancy.\""
            - generic [ref=e94]: Click to use →
          - button "\"Reduce React bundle size by 30% — identify the biggest wins first.\" Click to use →" [ref=e95] [cursor=pointer]:
            - generic [ref=e96]: "\"Reduce React bundle size by 30% — identify the biggest wins first.\""
            - generic [ref=e97]: Click to use →
      - generic [ref=e98]:
        - heading "📊 Research & analysis" [level=2] [ref=e99]
        - generic [ref=e100]:
          - button "\"Research the top 3 alternatives to Qdrant for our vector store and produce a comparison.\" Click to use →" [ref=e101] [cursor=pointer]:
            - generic [ref=e102]: "\"Research the top 3 alternatives to Qdrant for our vector store and produce a comparison.\""
            - generic [ref=e103]: Click to use →
          - button "\"Analyse our Q1 sprint velocity data and recommend process improvements.\" Click to use →" [ref=e104] [cursor=pointer]:
            - generic [ref=e105]: "\"Analyse our Q1 sprint velocity data and recommend process improvements.\""
            - generic [ref=e106]: Click to use →
          - button "\"Investigate why API p95 latency increased 40% after the last deploy.\" Click to use →" [ref=e107] [cursor=pointer]:
            - generic [ref=e108]: "\"Investigate why API p95 latency increased 40% after the last deploy.\""
            - generic [ref=e109]: Click to use →
          - button "\"Survey industry best practices for LLM observability in 2026.\" Click to use →" [ref=e110] [cursor=pointer]:
            - generic [ref=e111]: "\"Survey industry best practices for LLM observability in 2026.\""
            - generic [ref=e112]: Click to use →
      - generic [ref=e113]:
        - heading "🤝 Team & process" [level=2] [ref=e114]
        - generic [ref=e115]:
          - button "\"Create monthly goals for improving developer onboarding documentation.\" Click to use →" [ref=e116] [cursor=pointer]:
            - generic [ref=e117]: "\"Create monthly goals for improving developer onboarding documentation.\""
            - generic [ref=e118]: Click to use →
          - button "\"Plan a 2-week sprint to reduce the backlog of bug reports by 50%.\" Click to use →" [ref=e119] [cursor=pointer]:
            - generic [ref=e120]: "\"Plan a 2-week sprint to reduce the backlog of bug reports by 50%.\""
            - generic [ref=e121]: Click to use →
          - button "\"Outline a knowledge-transfer plan for the outgoing lead engineer.\" Click to use →" [ref=e122] [cursor=pointer]:
            - generic [ref=e123]: "\"Outline a knowledge-transfer plan for the outgoing lead engineer.\""
            - generic [ref=e124]: Click to use →
          - button "\"Set team objectives for improving code review turnaround to under 24 hours.\" Click to use →" [ref=e125] [cursor=pointer]:
            - generic [ref=e126]: "\"Set team objectives for improving code review turnaround to under 24 hours.\""
            - generic [ref=e127]: Click to use →
          - button "\"Design a promotional banner image for the goal.\" Click to use →" [ref=e128] [cursor=pointer]:
            - generic [ref=e129]: "\"Design a promotional banner image for the goal.\""
            - generic [ref=e130]: Click to use →
      - generic [ref=e131]:
        - heading "🖼️ Multimedia goals" [level=2] [ref=e132]
        - generic [ref=e133]:
          - button "\"Generate a logo for this goal/project.\" Click to use →" [ref=e134] [cursor=pointer]:
            - generic [ref=e135]: "\"Generate a logo for this goal/project.\""
            - generic [ref=e136]: Click to use →
          - button "\"What multimedia assets would support this objective?\" Click to use →" [ref=e137] [cursor=pointer]:
            - generic [ref=e138]: "\"What multimedia assets would support this objective?\""
            - generic [ref=e139]: Click to use →
```

# Test source

```ts
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
  242 |         body: JSON.stringify({
  243 |           status: 'success',
  244 |           data: [
  245 |             { id: 'job2', label: 'Goal job', status: 'queued', started_at: now, statusObj: { status: 'queued' } }
  246 |           ]
  247 |         }),
  248 |       })
  249 |     );
  250 |     await page.goto(BASE + '/goals', { waitUntil: 'networkidle' });
> 251 |     await expect(page.locator('text=Goal job')).toBeVisible();
      |                                                 ^ Error: expect(locator).toBeVisible() failed
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
  264 |     const responsePromise = page.waitForResponse(
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