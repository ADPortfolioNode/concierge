# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: chat_workflows.spec.ts >> Concierge Chat Workflows >> should trigger internet search workflow
- Location: tests\chat_workflows.spec.ts:52:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByPlaceholder('Type a message...')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByPlaceholder('Type a message...')

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
  3   | test.describe('Concierge Chat Workflows', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('http://localhost:5173');
  6   |     // Wait for the main chat input to be visible, indicating the app has loaded
> 7   |     await expect(page.getByPlaceholder('Type a message...')).toBeVisible();
      |                                                              ^ Error: expect(locator).toBeVisible() failed
  8   |   });
  9   | 
  10  |   test('should handle greetings and small talk', async ({ page }) => {
  11  |     const messageInput = page.getByPlaceholder('Type a message...');
  12  |     await messageInput.fill('Hi there!');
  13  |     await messageInput.press('Enter');
  14  | 
  15  |     // Expect a conversational response
  16  |     await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/Hello! I'm Concierge/);
  17  |     // Check for the rule-based badge if no API key is set
  18  |     await expect(page.locator('.chat-message-bubble:last-child .llm-provider-badge')).toContainText('rule-based');
  19  |   });
  20  | 
  21  |   test('should trigger goal detection for complex inputs', async ({ page }) => {
  22  |     const messageInput = page.getByPlaceholder('Type a message...');
  23  |     await messageInput.fill('Plan a 6-week goal to launch a public REST API for our product.');
  24  |     await messageInput.press('Enter');
  25  | 
  26  |     // Expect a message indicating task processing
  27  |     await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/OK, I've started working on that/);
  28  |     // Optionally, check for the progress banner if it becomes visible
  29  |     await expect(page.locator('.progress-banner')).toBeVisible();
  30  |   });
  31  | 
  32  |   test('should handle fallback conversation for non-task-oriented inputs', async ({ page }) => {
  33  |     const messageInput = page.getByPlaceholder('Type a message...');
  34  |     await messageInput.fill('Tell me a fun fact about cats.');
  35  |     await messageInput.press('Enter');
  36  | 
  37  |     // Expect a friendly reply, not a task initiation
  38  |     await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I understand you're asking about "fun fact about cats"/);
  39  |     await expect(page.locator('.chat-message-bubble:last-child .llm-provider-badge')).toContainText('rule-based');
  40  |   });
  41  | 
  42  |   test('should handle image generation request', async ({ page }) => {
  43  |     const messageInput = page.getByPlaceholder('Type a message...');
  44  |     await messageInput.fill('Generate an image of a futuristic city at sunset.');
  45  |     await messageInput.press('Enter');
  46  | 
  47  |     // Expect a response indicating image generation is being processed or requires API key
  48  |     await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I'd love to generate that image for you!/);
  49  |     await expect(page.locator('.chat-message-bubble:last-child .llm-provider-badge')).toContainText('rule-based');
  50  |   });
  51  | 
  52  |   test('should trigger internet search workflow', async ({ page }) => {
  53  |     const messageInput = page.getByPlaceholder('Type a message...');
  54  |     await messageInput.fill('web search for the history of Playwright testing framework.');
  55  |     await messageInput.press('Enter');
  56  | 
  57  |     // Expect a message indicating a research task has started
  58  |     await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/OK, I've started working on that/);
  59  |     await expect(page.locator('.progress-banner')).toBeVisible();
  60  |   });
  61  | 
  62  |   test('should provide topic hints for "audio"', async ({ page }) => {
  63  |     const messageInput = page.getByPlaceholder('Type a message...');
  64  |     await messageInput.fill('I have an audio file.');
  65  |     await messageInput.press('Enter');
  66  | 
  67  |     // Expect a hint about audio transcription
  68  |     await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I understand you're asking about "audio"/);
  69  |     await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I can help with code!/); // This is a generic fallback, but the rule-based system might pick up on 'audio' and give a more specific hint if implemented.
  70  |   });
  71  | 
  72  |   test('should provide topic hints for "image"', async ({ page }) => {
  73  |     const messageInput = page.getByPlaceholder('Type a message...');
  74  |     await messageInput.fill('I have an image of a circuit board.');
  75  |     await messageInput.press('Enter');
  76  | 
  77  |     // Expect a hint about image analysis
  78  |     await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I understand you're asking about "image"/);
  79  |     await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I'd love to generate that image for you!/); // The rule-based system might offer image generation as a hint.
  80  |   });
  81  | 
  82  |   test('should handle code generation request', async ({ page }) => {
  83  |     const messageInput = page.getByPlaceholder('Type a message...');
  84  |     await messageInput.fill('Write a Python function to calculate Fibonacci sequence.');
  85  |     await messageInput.press('Enter');
  86  | 
  87  |     // Expect a response related to code generation
  88  |     await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I can help with code!/);
  89  |     await expect(page.locator('.chat-message-bubble:last-child .llm-provider-badge')).toContainText('rule-based');
  90  |   });
  91  | 
  92  |   test('should handle summarization request', async ({ page }) => {
  93  |     const messageInput = page.getByPlaceholder('Type a message...');
  94  |     await messageInput.fill('Summarize the following text: Large language models are a type of artificial intelligence program that can recognize and generate text, among other tasks.');
  95  |     await messageInput.press('Enter');
  96  | 
  97  |     // Expect a response indicating summarization capability
  98  |     await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I understand you're asking about "summarize"/);
  99  |     await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/Sure — paste the text you'd like summarized/);
  100 |   });
  101 | 
  102 |   test('should handle "what can you do" query', async ({ page }) => {
  103 |     const messageInput = page.getByPlaceholder('Type a message...');
  104 |     await messageInput.fill('What can you do?');
  105 |     await messageInput.press('Enter');
  106 | 
  107 |     // Expect a detailed list of capabilities
```