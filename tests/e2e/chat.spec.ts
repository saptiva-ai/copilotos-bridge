import { test, expect } from '@playwright/test';
import { getTestUsers, sendUIMessage, waitForChatResponse, measurePerformance } from '../utils/test-helpers';

test.describe('Chat Functionality', () => {
  const users = getTestUsers();

  test.beforeEach(async ({ page }) => {
    // Use stored authentication state from setup
    await page.goto('/chat');
  });

  test('should display chat interface', async ({ page }) => {
    // Check for main chat components
    await expect(page.locator('[data-testid="chat-input"], textarea, input[placeholder*="message"]').first()).toBeVisible();
    await expect(page.locator('button:has-text("Send"), [data-testid="send-button"]').first()).toBeVisible();
    await expect(page.locator('[data-testid="chat-messages"], .messages, .chat-history').first()).toBeVisible();
  });

  test('should send a simple message', async ({ page }) => {
    const testMessage = 'Hello, this is a test message';

    const { result, duration } = await measurePerformance(
      async () => {
        await sendUIMessage(page, testMessage);

        // Verify message appears in chat
        await expect(page.locator(`text="${testMessage}"`)).toBeVisible({ timeout: 5000 });

        // Wait for AI response
        await waitForChatResponse(page, 15000);
        return true;
      },
      'Send message and receive response'
    );

    // Performance baseline: message send + response should complete within 20 seconds
    expect(duration).toBeLessThan(20000);
  });

  test('should handle streaming responses', async ({ page }) => {
    const testMessage = 'Tell me about artificial intelligence';

    const chatInput = page.locator('[data-testid="chat-input"], textarea, input[placeholder*="message"]').first();
    const sendButton = page.locator('button:has-text("Send"), [data-testid="send-button"]').first();

    await chatInput.fill(testMessage);
    await sendButton.click();

    // Wait for streaming indicator or response
    await expect(page.locator('.typing, .loading, .streaming, [data-testid="typing"]').first()).toBeVisible({ timeout: 5000 });

    // Wait for complete response
    await expect(page.locator('.message, .chat-message').last()).toBeVisible({ timeout: 30000 });

    // Verify response contains content
    const lastMessage = page.locator('.message, .chat-message').last();
    await expect(lastMessage).toContainText(/\w+/); // Contains at least one word
  });

  test('should create new chat session', async ({ page }) => {
    // Look for new chat button
    const newChatButton = page.locator('button:has-text("New Chat"), [data-testid="new-chat"], .new-chat').first();

    if (await newChatButton.count() > 0) {
      await newChatButton.click();

      // Verify empty chat state
      const messages = page.locator('.message, .chat-message, [data-testid="message"]');
      await expect(messages).toHaveCount(0);
    }
  });

  test('should display chat history sidebar', async ({ page }) => {
    // Look for chat history/sidebar
    const sidebar = page.locator('.sidebar, .chat-history, [data-testid="chat-sidebar"]').first();

    if (await sidebar.count() > 0) {
      await expect(sidebar).toBeVisible();

      // Check for previous chats if any exist
      const chatItems = sidebar.locator('.chat-item, .session, [data-testid="chat-item"]');
      // Just verify the sidebar structure exists
      await expect(sidebar).toBeVisible();
    }
  });

  test('should handle message with research mode', async ({ page }) => {
    const researchMessage = 'Research the latest developments in quantum computing';

    // Look for research toggle or mode selector
    const researchToggle = page.locator('[data-testid="research-mode"], .research-toggle, input[type="checkbox"]').first();

    if (await researchToggle.count() > 0) {
      await researchToggle.click();
    }

    const chatInput = page.locator('[data-testid="chat-input"], textarea, input[placeholder*="message"]').first();
    const sendButton = page.locator('button:has-text("Send"), [data-testid="send-button"]').first();

    await chatInput.fill(researchMessage);
    await sendButton.click();

    // Wait for research indicators or extended processing
    await expect(page.locator('.research, .deep-research, [data-testid="research-indicator"]').first()).toBeVisible({ timeout: 10000 });

    // Wait for comprehensive response
    await expect(page.locator('.message, .chat-message').last()).toBeVisible({ timeout: 60000 });
  });

  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    // Verify mobile layout
    const chatContainer = page.locator('.chat-container, .chat-wrapper, main').first();
    await expect(chatContainer).toBeVisible();

    // Check that input is accessible
    const chatInput = page.locator('[data-testid="chat-input"], textarea, input[placeholder*="message"]').first();
    await expect(chatInput).toBeVisible();
  });
});