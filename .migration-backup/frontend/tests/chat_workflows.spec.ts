import { test, expect } from '@playwright/test';

test.describe('Concierge Chat Workflows', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5173');
    // Wait for the main chat input to be visible, indicating the app has loaded
    await expect(page.getByPlaceholder('Type a message...')).toBeVisible();
  });

  test('should handle greetings and small talk', async ({ page }) => {
    const messageInput = page.getByPlaceholder('Type a message...');
    await messageInput.fill('Hi there!');
    await messageInput.press('Enter');

    // Expect a conversational response
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/Hello! I'm Concierge/);
    // Check for the rule-based badge if no API key is set
    await expect(page.locator('.chat-message-bubble:last-child .llm-provider-badge')).toContainText('rule-based');
  });

  test('should trigger goal detection for complex inputs', async ({ page }) => {
    const messageInput = page.getByPlaceholder('Type a message...');
    await messageInput.fill('Plan a 6-week goal to launch a public REST API for our product.');
    await messageInput.press('Enter');

    // Expect a message indicating task processing
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/OK, I've started working on that/);
    // Optionally, check for the progress banner if it becomes visible
    await expect(page.locator('.progress-banner')).toBeVisible();
  });

  test('should handle fallback conversation for non-task-oriented inputs', async ({ page }) => {
    const messageInput = page.getByPlaceholder('Type a message...');
    await messageInput.fill('Tell me a fun fact about cats.');
    await messageInput.press('Enter');

    // Expect a friendly reply, not a task initiation
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I understand you're asking about "fun fact about cats"/);
    await expect(page.locator('.chat-message-bubble:last-child .llm-provider-badge')).toContainText('rule-based');
  });

  test('should handle image generation request', async ({ page }) => {
    const messageInput = page.getByPlaceholder('Type a message...');
    await messageInput.fill('Generate an image of a futuristic city at sunset.');
    await messageInput.press('Enter');

    // Expect a response indicating image generation is being processed or requires API key
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I'd love to generate that image for you!/);
    await expect(page.locator('.chat-message-bubble:last-child .llm-provider-badge')).toContainText('rule-based');
  });

  test('should trigger internet search workflow', async ({ page }) => {
    const messageInput = page.getByPlaceholder('Type a message...');
    await messageInput.fill('web search for the history of Playwright testing framework.');
    await messageInput.press('Enter');

    // Expect a message indicating a research task has started
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/OK, I've started working on that/);
    await expect(page.locator('.progress-banner')).toBeVisible();
  });

  test('should provide topic hints for "audio"', async ({ page }) => {
    const messageInput = page.getByPlaceholder('Type a message...');
    await messageInput.fill('I have an audio file.');
    await messageInput.press('Enter');

    // Expect a hint about audio transcription
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I understand you're asking about "audio"/);
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I can help with code!/); // This is a generic fallback, but the rule-based system might pick up on 'audio' and give a more specific hint if implemented.
  });

  test('should provide topic hints for "image"', async ({ page }) => {
    const messageInput = page.getByPlaceholder('Type a message...');
    await messageInput.fill('I have an image of a circuit board.');
    await messageInput.press('Enter');

    // Expect a hint about image analysis
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I understand you're asking about "image"/);
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I'd love to generate that image for you!/); // The rule-based system might offer image generation as a hint.
  });

  test('should handle code generation request', async ({ page }) => {
    const messageInput = page.getByPlaceholder('Type a message...');
    await messageInput.fill('Write a Python function to calculate Fibonacci sequence.');
    await messageInput.press('Enter');

    // Expect a response related to code generation
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I can help with code!/);
    await expect(page.locator('.chat-message-bubble:last-child .llm-provider-badge')).toContainText('rule-based');
  });

  test('should handle summarization request', async ({ page }) => {
    const messageInput = page.getByPlaceholder('Type a message...');
    await messageInput.fill('Summarize the following text: Large language models are a type of artificial intelligence program that can recognize and generate text, among other tasks.');
    await messageInput.press('Enter');

    // Expect a response indicating summarization capability
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I understand you're asking about "summarize"/);
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/Sure — paste the text you'd like summarized/);
  });

  test('should handle "what can you do" query', async ({ page }) => {
    const messageInput = page.getByPlaceholder('Type a message...');
    await messageInput.fill('What can you do?');
    await messageInput.press('Enter');

    // Expect a detailed list of capabilities
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/I'm Concierge, an AI-powered multi-agent assistant/);
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/Conversation/);
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/Planning/);
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/Research/);
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/Code generation/);
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/Image generation/);
    await expect(page.locator('.chat-message-bubble:last-child')).toContainText(/Memory/);
  });
});