# Page snapshot

```yaml
- generic [ref=e3]:
  - banner [ref=e4]:
    - generic [ref=e5]:
      - link "Concierge" [ref=e7] [cursor=pointer]:
        - /url: /
      - navigation [ref=e8]:
        - link "Home" [ref=e9] [cursor=pointer]:
          - /url: /
        - link "Tasks" [ref=e10] [cursor=pointer]:
          - /url: /tasks
        - link "Goals" [ref=e11] [cursor=pointer]:
          - /url: /goals
  - complementary [ref=e12]:
    - generic [ref=e13]:
      - generic "message-welcome" [ref=e17]:
        - generic [ref=e18]: Welcome. I'm ready when you are. What would you like to work on today?
        - generic [ref=e19]: 3/4/2026, 1:01:31 PM
      - textbox "Type your message and press Enter to send" [ref=e22]
  - main [ref=e23]:
    - generic [ref=e24]:
      - text: Welcome to Concierge
      - button "Test Media" [ref=e25]
      - button "Enable Auto (authorize+populate)" [ref=e26]
  - button "Close" [ref=e29]
```