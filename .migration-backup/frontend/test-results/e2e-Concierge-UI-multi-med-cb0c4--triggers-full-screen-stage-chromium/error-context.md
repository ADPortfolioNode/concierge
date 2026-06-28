# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e2e.spec.ts >> Concierge UI >> multi-media response triggers full-screen stage
- Location: tests\e2e.spec.ts:189:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('role=button[title="Restore size"]')
Expected: visible
Error: Unknown attribute "title", must be one of "checked", "disabled", "expanded", "include-hidden", "level", "name", "pressed", "selected".
    at validateAttributes (<anonymous>:4915:15)
    at Object.queryAll (<anonymous>:4975:23)
    at InjectedScript._queryEngineAll (<anonymous>:6645:49)
    at InjectedScript.querySelectorAll (<anonymous>:6632:30)
    at eval (eval at evaluate (:302:30), <anonymous>:2:42)
    at UtilityScript.evaluate (<anonymous>:304:16)
    at UtilityScript.<anonymous> (<anonymous>:1:44)

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('role=button[title="Restore size"]')

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
        - generic "message-1777045992964" [ref=e36]:
          - generic [ref=e37]: show me media
          - generic [ref=e38]: 4/24/2026, 11:53:12 AM
        - generic "message-1777045992965" [ref=e40]
      - generic [ref=e44]:
        - generic [ref=e45]:
          - button "📎" [disabled] [ref=e46]
          - textbox "Sending..." [disabled] [ref=e47]
          - button "↑" [disabled] [ref=e48]
        - generic [ref=e49]:
          - generic [ref=e50]: Streaming…
          - button "🗑 Clear memory" [disabled] [ref=e52]
  - main [ref=e53]:
    - generic [ref=e54]:
      - generic [ref=e56]:
        - heading "Build smarter workflows, see results visually." [level=1] [ref=e57]:
          - text: Build smarter workflows,
          - text: see results visually.
        - paragraph [ref=e58]: Ask me to plan, execute, and monitor your work. I can also surface photo-driven insights, review your files, and turn your goals into a clear visual timeline.
        - generic [ref=e59]:
          - button "↗ Show me my current roadmap" [ref=e60] [cursor=pointer]:
            - generic [ref=e61]: ↗
            - generic [ref=e62]: Show me my current roadmap
          - button "↗ Create a visual status update" [ref=e63] [cursor=pointer]:
            - generic [ref=e64]: ↗
            - generic [ref=e65]: Create a visual status update
          - button "↗ Generate a media summary" [ref=e66] [cursor=pointer]:
            - generic [ref=e67]: ↗
            - generic [ref=e68]: Generate a media summary
      - generic [ref=e69]:
        - generic [ref=e71]:
          - generic [ref=e72]: Live Timeline
          - heading "See Concierge planning in one responsive view" [level=2] [ref=e73]
          - paragraph [ref=e74]: Your current plan updates, task progress, and visual graph are surfaced in a mobile-first timeline card that spans the full width of the landing page.
        - generic [ref=e75]:
          - generic [ref=e76]:
            - generic [ref=e77]:
              - paragraph [ref=e78]: Assistant timeline
              - heading "Assistant linear timeline" [level=2] [ref=e79]
              - paragraph [ref=e80]: Visualize the assistant's strategy as a linear timeline with tasks and progress.
            - button "View full timeline" [ref=e81] [cursor=pointer]
          - generic [ref=e82]:
            - img "Assistant linear timeline" [ref=e84]:
              - generic [ref=e88]: Assistant starts
              - generic [ref=e92]: Strategy branch
              - generic [ref=e96]: Plan tasks
              - generic [ref=e100]: Execute actions
              - generic [ref=e104]: Review results
            - generic [ref=e106]: No timeline tasks are available yet. Ask Concierge to create a plan or add a goal.
      - generic [ref=e107]:
        - heading "Quick actions" [level=2] [ref=e108]
        - generic [ref=e109]:
          - button "↗ What can you help me with?" [ref=e110] [cursor=pointer]:
            - generic [ref=e111]: ↗
            - generic [ref=e112]: What can you help me with?
          - button "↗ Show me what tasks are running." [ref=e113] [cursor=pointer]:
            - generic [ref=e114]: ↗
            - generic [ref=e115]: Show me what tasks are running.
          - button "↗ Create a 2-week sprint plan for a new feature." [ref=e116] [cursor=pointer]:
            - generic [ref=e117]: ↗
            - generic [ref=e118]: Create a 2-week sprint plan for a new feature.
          - button "↗ Summarise my last project context." [ref=e119] [cursor=pointer]:
            - generic [ref=e120]: ↗
            - generic [ref=e121]: Summarise my last project context.
          - button "↗ Help me prioritise my backlog." [ref=e122] [cursor=pointer]:
            - generic [ref=e123]: ↗
            - generic [ref=e124]: Help me prioritise my backlog.
      - generic [ref=e125]:
        - heading "Choose your outcome" [level=2] [ref=e126]
        - generic [ref=e127]:
          - generic [ref=e128]:
            - generic [ref=e129]:
              - generic [ref=e130]: 🎯
              - generic [ref=e131]:
                - generic [ref=e132]: Achieve Your Goals
                - generic [ref=e133]: Turn ambitions into results
            - paragraph [ref=e134]: Set high-level outcomes, let Concierge break them into prioritised tasks, and track progress automatically.
            - generic [ref=e135]:
              - button "↗ Create a 4-week goal to migrate our REST API to GraphQL." [ref=e136] [cursor=pointer]:
                - generic [ref=e137]: ↗
                - generic [ref=e138]: Create a 4-week goal to migrate our REST API to GraphQL.
              - button "↗ I want to reduce page load time by 40% — plan it out." [ref=e139] [cursor=pointer]:
                - generic [ref=e140]: ↗
                - generic [ref=e141]: I want to reduce page load time by 40% — plan it out.
              - button "↗ Set weekly goals for improving test coverage from 60% to 90%." [ref=e142] [cursor=pointer]:
                - generic [ref=e143]: ↗
                - generic [ref=e144]: Set weekly goals for improving test coverage from 60% to 90%.
            - link "Open Goals →" [ref=e145] [cursor=pointer]:
              - /url: /goals
          - generic [ref=e146]:
            - generic [ref=e147]:
              - generic [ref=e148]: ⚡
              - generic [ref=e149]:
                - generic [ref=e150]: Automate Your Work
                - generic [ref=e151]: Execute tasks without lifting a finger
            - paragraph [ref=e152]: "Run background tasks asynchronously: analyse files, generate code, process datasets, and get results delivered."
            - generic [ref=e153]:
              - button "↗ Analyse the CSV I uploaded and summarise the key trends." [ref=e154] [cursor=pointer]:
                - generic [ref=e155]: ↗
                - generic [ref=e156]: Analyse the CSV I uploaded and summarise the key trends.
              - button "↗ Generate a Python script to parse JSON logs and extract error counts." [ref=e157] [cursor=pointer]:
                - generic [ref=e158]: ↗
                - generic [ref=e159]: Generate a Python script to parse JSON logs and extract error counts.
              - button "↗ Read my uploaded spec and list all missing edge cases." [ref=e160] [cursor=pointer]:
                - generic [ref=e161]: ↗
                - generic [ref=e162]: Read my uploaded spec and list all missing edge cases.
            - link "Open Tasks →" [ref=e163] [cursor=pointer]:
              - /url: /tasks
          - generic [ref=e164]:
            - generic [ref=e165]:
              - generic [ref=e166]: 🗺️
              - generic [ref=e167]:
                - generic [ref=e168]: Plan Your Strategy
                - generic [ref=e169]: Think clearly, decide confidently
            - paragraph [ref=e170]: Apply OKRs, SWOT analysis, RICE scoring, and roadmapping frameworks. Let Concierge be your strategic thinking partner.
            - generic [ref=e171]:
              - button "↗ Write 3 OKRs for our product team for Q3 2026." [ref=e172] [cursor=pointer]:
                - generic [ref=e173]: ↗
                - generic [ref=e174]: Write 3 OKRs for our product team for Q3 2026.
              - button "↗ Run a SWOT analysis for a developer-tools startup." [ref=e175] [cursor=pointer]:
                - generic [ref=e176]: ↗
                - generic [ref=e177]: Run a SWOT analysis for a developer-tools startup.
              - button "↗ Build a 6-month product roadmap for a data-analytics platform." [ref=e178] [cursor=pointer]:
                - generic [ref=e179]: ↗
                - generic [ref=e180]: Build a 6-month product roadmap for a data-analytics platform.
            - link "Open Strategy →" [ref=e181] [cursor=pointer]:
              - /url: /strategy
          - generic [ref=e182]:
            - generic [ref=e183]:
              - generic [ref=e184]: 📁
              - generic [ref=e185]:
                - generic [ref=e186]: Manage Your Workspace
                - generic [ref=e187]: All your files and context in one place
            - paragraph [ref=e188]: Upload documents, images, CSVs, and PDFs. Attach them to projects and reference them in any conversation.
            - generic [ref=e189]:
              - button "↗ I've uploaded a PDF spec — summarise the authentication requirements." [ref=e190] [cursor=pointer]:
                - generic [ref=e191]: ↗
                - generic [ref=e192]: I've uploaded a PDF spec — summarise the authentication requirements.
              - button "↗ Attach the financial model CSV to the Q2 Planning project." [ref=e193] [cursor=pointer]:
                - generic [ref=e194]: ↗
                - generic [ref=e195]: Attach the financial model CSV to the Q2 Planning project.
              - button "↗ Transcribe the audio file I uploaded and summarise it." [ref=e196] [cursor=pointer]:
                - generic [ref=e197]: ↗
                - generic [ref=e198]: Transcribe the audio file I uploaded and summarise it.
            - link "Open Workspace →" [ref=e199] [cursor=pointer]:
              - /url: /workspace
      - generic [ref=e200]:
        - heading "More resources" [level=2] [ref=e201]
        - generic [ref=e202]:
          - link "📖 How-To Guide Learn core workflows" [ref=e203] [cursor=pointer]:
            - /url: /howto
            - generic [ref=e204]: 📖 How-To Guide
            - generic [ref=e205]: Learn core workflows
          - link "🔌 Integrations Browse plugins & tools" [ref=e206] [cursor=pointer]:
            - /url: /capabilities
            - generic [ref=e207]: 🔌 Integrations
            - generic [ref=e208]: Browse plugins & tools
```