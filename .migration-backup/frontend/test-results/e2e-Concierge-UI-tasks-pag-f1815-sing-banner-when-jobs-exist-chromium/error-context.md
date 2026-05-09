# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e2e.spec.ts >> Concierge UI >> tasks page shows processing banner when jobs exist
- Location: tests\e2e.spec.ts:214:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text=Example job')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('text=Example job')

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
        - generic [ref=e38]: 4/24/2026, 11:53:29 AM
      - generic [ref=e40]:
        - generic [ref=e41]:
          - button "📎" [ref=e42] [cursor=pointer]
          - textbox "Message — Enter to send, Shift+Enter for newline" [ref=e43]
          - button "↑" [disabled] [ref=e44]
        - button "🗑 Clear memory" [ref=e46] [cursor=pointer]
  - main [ref=e47]:
    - generic [ref=e48]:
      - heading "✅ Tasks" [level=1] [ref=e49]
      - paragraph [ref=e50]: Tasks run in the background — read files, generate code, analyse datasets. Enqueue via chat or the Postman collection, then poll for results. Click any prompt to try one now.
      - generic [ref=e51]:
        - button "Overview" [ref=e52] [cursor=pointer]
        - button "Sample tasks" [ref=e53] [cursor=pointer]
        - button "Job history" [ref=e54] [cursor=pointer]
        - button "Quick prompts" [ref=e55] [cursor=pointer]
      - generic [ref=e56]: "Overview: check the current task queue, review active jobs, and explore task examples for common automations."
      - generic [ref=e57]:
        - heading "Live timeline" [level=2] [ref=e58]
        - generic [ref=e59]:
          - generic [ref=e60]:
            - generic [ref=e61]:
              - paragraph [ref=e62]: Assistant timeline
              - heading "Assistant linear timeline" [level=2] [ref=e63]
              - paragraph [ref=e64]: Visualize the assistant's strategy as a linear timeline with tasks and progress.
            - button "View full timeline" [ref=e65] [cursor=pointer]
          - generic [ref=e66]:
            - img "Assistant linear timeline" [ref=e68]:
              - generic [ref=e72]: Assistant starts
              - generic [ref=e76]: Strategy branch
              - generic [ref=e80]: Plan tasks
              - generic [ref=e84]: Execute actions
              - generic [ref=e88]: Review results
            - generic [ref=e90]: No timeline tasks are available yet. Ask Concierge to create a plan or add a goal.
      - generic [ref=e91]:
        - generic [ref=e92]:
          - img "Photo review workflow" [ref=e93]
          - generic [ref=e94]:
            - heading "Photo review workflow" [level=3] [ref=e95]
            - paragraph [ref=e96]: Use image-based tasks to summarize, tag, or clean up photos with realistic output.
        - generic [ref=e97]:
          - img "Report generation" [ref=e98]
          - generic [ref=e99]:
            - heading "Report generation" [level=3] [ref=e100]
            - paragraph [ref=e101]: Extract insights from uploads, create polished summaries, and generate final deliverables.
        - generic [ref=e102]:
          - img "Data-driven decisions" [ref=e103]
          - generic [ref=e104]:
            - heading "Data-driven decisions" [level=3] [ref=e105]
            - paragraph [ref=e106]: Turn spreadsheets and logs into actionable business recommendations.
      - generic [ref=e107]:
        - heading "🚀 Distributed Agent Job" [level=2] [ref=e108]
        - paragraph [ref=e109]:
          - text: Jobs are queued via Celery + Redis and executed in a background worker. Results are polled every 3 seconds. Monitor the Flower dashboard at
          - code [ref=e110]: localhost:5555
          - text: .
        - generic [ref=e111]:
          - textbox "Goal — what should the agent do?" [ref=e112]
          - textbox "Context (optional background information)" [ref=e113]
          - button "Submit Job" [disabled] [ref=e114]
      - generic [ref=e115]:
        - heading "Recent tasks" [level=2] [ref=e116]
        - generic [ref=e118]:
          - generic [ref=e119]: running
          - generic [ref=e120]: job1…
      - generic [ref=e121]:
        - heading "Available task types" [level=2] [ref=e122]
        - generic [ref=e123]:
          - generic [ref=e124]:
            - generic [ref=e126]: read_file
            - generic [ref=e127]: Read text from an uploaded file.
            - code [ref=e128]: "payload: { \"upload_id\": \"<id>\", \"filename\": \"notes.txt\" }"
          - generic [ref=e129]:
            - generic [ref=e131]: write_file
            - generic [ref=e132]: Write / overwrite a sandbox file.
            - code [ref=e133]: "payload: { \"upload_id\": \"<id>\", \"filename\": \"out.txt\", \"content\": \"Hello\" }"
          - generic [ref=e134]:
            - generic [ref=e136]: append_file
            - generic [ref=e137]: Append text to a sandbox file.
            - code [ref=e138]: "payload: { \"upload_id\": \"<id>\", \"filename\": \"log.txt\", \"content\": \"new line\" }"
          - generic [ref=e139]:
            - generic [ref=e141]: generate_code
            - generic [ref=e142]: Generate code from a natural-language context.
            - code [ref=e143]: "payload: { \"context\": \"parse CSV and plot bar chart\", \"language\": \"python\" }"
          - generic [ref=e144]:
            - generic [ref=e146]: dataset_analysis
            - generic [ref=e147]: Statistical analysis of a CSV file.
            - code [ref=e148]: "payload: { \"upload_id\": \"<id>\", \"filename\": \"sales.csv\" }"
      - generic [ref=e149]:
        - heading "📄 File operations" [level=2] [ref=e150]
        - generic [ref=e151]:
          - button "\"Read the spec I uploaded and list every functional requirement.\" Click to use →" [ref=e152] [cursor=pointer]:
            - generic [ref=e153]: "\"Read the spec I uploaded and list every functional requirement.\""
            - generic [ref=e154]: Click to use →
          - button "\"Read my uploaded README and suggest improvements to the Getting Started section.\" Click to use →" [ref=e155] [cursor=pointer]:
            - generic [ref=e156]: "\"Read my uploaded README and suggest improvements to the Getting Started section.\""
            - generic [ref=e157]: Click to use →
          - button "\"Append a timestamp and \"task complete\" to the log file in the current upload.\" Click to use →" [ref=e158] [cursor=pointer]:
            - generic [ref=e159]: "\"Append a timestamp and \"task complete\" to the log file in the current upload.\""
            - generic [ref=e160]: Click to use →
      - generic [ref=e161]:
        - heading "💻 Code generation" [level=2] [ref=e162]
        - generic [ref=e163]:
          - button "\"Generate a Python script that reads a CSV and outputs a bar chart with matplotlib.\" Click to use →" [ref=e164] [cursor=pointer]:
            - generic [ref=e165]: "\"Generate a Python script that reads a CSV and outputs a bar chart with matplotlib.\""
            - generic [ref=e166]: Click to use →
          - button "\"Write a TypeScript utility function that deep-merges two objects.\" Click to use →" [ref=e167] [cursor=pointer]:
            - generic [ref=e168]: "\"Write a TypeScript utility function that deep-merges two objects.\""
            - generic [ref=e169]: Click to use →
          - button "\"Generate a Bash script to tail all *.log files in /var/log and grep for ERROR.\" Click to use →" [ref=e170] [cursor=pointer]:
            - generic [ref=e171]: "\"Generate a Bash script to tail all *.log files in /var/log and grep for ERROR.\""
            - generic [ref=e172]: Click to use →
          - button "\"Create a SQL migration that adds a soft-delete column to a users table.\" Click to use →" [ref=e173] [cursor=pointer]:
            - generic [ref=e174]: "\"Create a SQL migration that adds a soft-delete column to a users table.\""
            - generic [ref=e175]: Click to use →
      - generic [ref=e176]:
        - heading "📊 Dataset analysis" [level=2] [ref=e177]
        - generic [ref=e178]:
          - button "\"Analyse sales.csv — what are the top 5 product categories by revenue?\" Click to use →" [ref=e179] [cursor=pointer]:
            - generic [ref=e180]: "\"Analyse sales.csv — what are the top 5 product categories by revenue?\""
            - generic [ref=e181]: Click to use →
          - button "\"Run a full statistical analysis on the uploaded CSV and highlight any anomalies.\" Click to use →" [ref=e182] [cursor=pointer]:
            - generic [ref=e183]: "\"Run a full statistical analysis on the uploaded CSV and highlight any anomalies.\""
            - generic [ref=e184]: Click to use →
          - button "\"What is the column distribution in my uploaded dataset? Show numeric stats.\" Click to use →" [ref=e185] [cursor=pointer]:
            - generic [ref=e186]: "\"What is the column distribution in my uploaded dataset? Show numeric stats.\""
            - generic [ref=e187]: Click to use →
          - button "\"Analyse financials.csv and identify the quarters with the highest variance.\" Click to use →" [ref=e188] [cursor=pointer]:
            - generic [ref=e189]: "\"Analyse financials.csv and identify the quarters with the highest variance.\""
            - generic [ref=e190]: Click to use →
      - generic [ref=e191]:
        - heading "🔍 Status & management" [level=2] [ref=e192]
        - generic [ref=e193]:
          - button "\"What tasks are currently queued or running?\" Click to use →" [ref=e194] [cursor=pointer]:
            - generic [ref=e195]: "\"What tasks are currently queued or running?\""
            - generic [ref=e196]: Click to use →
          - button "\"Show me the result of the last completed task.\" Click to use →" [ref=e197] [cursor=pointer]:
            - generic [ref=e198]: "\"Show me the result of the last completed task.\""
            - generic [ref=e199]: Click to use →
          - button "\"How many tasks have failed in the current session?\" Click to use →" [ref=e200] [cursor=pointer]:
            - generic [ref=e201]: "\"How many tasks have failed in the current session?\""
            - generic [ref=e202]: Click to use →
      - generic [ref=e203]:
        - heading "🎥 Multimedia tasks" [level=2] [ref=e204]
        - generic [ref=e205]:
          - button "\"Describe what is happening in the uploaded video.\" Click to use →" [ref=e206] [cursor=pointer]:
            - generic [ref=e207]: "\"Describe what is happening in the uploaded video.\""
            - generic [ref=e208]: Click to use →
          - button "\"Transcribe the voice memo I attached.\" Click to use →" [ref=e209] [cursor=pointer]:
            - generic [ref=e210]: "\"Transcribe the voice memo I attached.\""
            - generic [ref=e211]: Click to use →
          - button "\"Create an image summarising the data analysis results.\" Click to use →" [ref=e212] [cursor=pointer]:
            - generic [ref=e213]: "\"Create an image summarising the data analysis results.\""
            - generic [ref=e214]: Click to use →
```

# Test source

```ts
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
> 230 |     await expect(page.locator('text=Example job')).toBeVisible();
      |                                                    ^ Error: expect(locator).toBeVisible() failed
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