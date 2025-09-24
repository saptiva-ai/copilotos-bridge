import { test, expect } from '@playwright/test';

test.describe('Performance Tests', () => {
  test('should load homepage within acceptable time', async ({ page }) => {
    const startTime = Date.now();

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;

    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);

    // Check Core Web Vitals
    const metrics = await page.evaluate(() => {
      return new Promise((resolve) => {
        const observer = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          const vitals = {};

          entries.forEach((entry) => {
            if (entry.name === 'first-contentful-paint') {
              vitals.fcp = entry.startTime;
            }
            if (entry.name === 'largest-contentful-paint') {
              vitals.lcp = entry.startTime;
            }
          });

          resolve(vitals);
        });

        observer.observe({ entryTypes: ['paint', 'largest-contentful-paint'] });

        // Fallback after 3 seconds
        setTimeout(() => resolve({}), 3000);
      });
    });

    console.log('Performance metrics:', metrics);
  });

  test('should handle multiple concurrent users', async ({ browser }) => {
    const contexts = await Promise.all([
      browser.newContext(),
      browser.newContext(),
      browser.newContext()
    ]);

    const pages = await Promise.all(
      contexts.map(context => context.newPage())
    );

    // Login all users concurrently
    const loginPromises = pages.map(async (page, index) => {
      await page.goto('/login');
      await page.fill('input[type="email"], input[name="username"]', `demo_admin`);
      await page.fill('input[type="password"]', 'demo_password_123');
      await page.click('button[type="submit"], button:has-text("Login")');
      await page.waitForURL(/.*\/(dashboard|chat|home).*/, { timeout: 10000 });
    });

    await Promise.all(loginPromises);

    // Navigate to chat concurrently
    const chatPromises = pages.map(async (page, index) => {
      await page.goto('/chat');

      const chatInput = page.locator('[data-testid="chat-input"], textarea, input[placeholder*="message"]').first();
      const sendButton = page.locator('button:has-text("Send"), [data-testid="send-button"]').first();

      await chatInput.fill(`Concurrent user ${index + 1} message`);
      await sendButton.click();

      // Wait for response
      await expect(page.locator('.message, .chat-message').last()).toBeVisible({ timeout: 30000 });
    });

    await Promise.all(chatPromises);

    // Cleanup
    await Promise.all(contexts.map(context => context.close()));
  });

  test('should maintain responsive performance under load', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="email"], input[name="username"]', 'demo_admin');
    await page.fill('input[type="password"]', 'demo_password_123');
    await page.click('button[type="submit"], button:has-text("Login")');
    await page.waitForURL(/.*\/(dashboard|chat|home).*/, { timeout: 10000 });

    await page.goto('/chat');

    // Send multiple messages rapidly
    const chatInput = page.locator('[data-testid="chat-input"], textarea, input[placeholder*="message"]').first();
    const sendButton = page.locator('button:has-text("Send"), [data-testid="send-button"]').first();

    for (let i = 0; i < 5; i++) {
      const startTime = Date.now();

      await chatInput.fill(`Performance test message ${i + 1}`);
      await sendButton.click();

      // Wait for UI response (input clearing or send button state change)
      await page.waitForFunction(() => {
        const input = document.querySelector('[data-testid="chat-input"], textarea, input[placeholder*="message"]');
        return input && input.value === '';
      }, { timeout: 5000 });

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(3000); // UI should respond within 3 seconds

      // Small delay between messages
      await page.waitForTimeout(1000);
    }
  });

  test('should handle large chat history efficiently', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="email"], input[name="username"]', 'demo_admin');
    await page.fill('input[type="password"]', 'demo_password_123');
    await page.click('button[type="submit"], button:has-text("Login")');
    await page.waitForURL(/.*\/(dashboard|chat|home).*/, { timeout: 10000 });

    await page.goto('/chat');

    // Send several messages to build up history
    const chatInput = page.locator('[data-testid="chat-input"], textarea, input[placeholder*="message"]').first();
    const sendButton = page.locator('button:has-text("Send"), [data-testid="send-button"]').first();

    for (let i = 0; i < 10; i++) {
      await chatInput.fill(`History test message ${i + 1}: This is a longer message to test scrolling and rendering performance with substantial content.`);
      await sendButton.click();

      // Wait for message to appear
      await expect(page.locator('.message, .chat-message').last()).toBeVisible({ timeout: 15000 });
    }

    // Test scrolling performance
    const startScroll = Date.now();
    await page.evaluate(() => {
      const chatContainer = document.querySelector('.chat-container, .messages, .chat-history');
      if (chatContainer) {
        chatContainer.scrollTop = 0; // Scroll to top
      }
    });

    await page.waitForTimeout(100); // Allow scroll to complete

    await page.evaluate(() => {
      const chatContainer = document.querySelector('.chat-container, .messages, .chat-history');
      if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight; // Scroll to bottom
      }
    });

    const scrollTime = Date.now() - startScroll;
    expect(scrollTime).toBeLessThan(1000); // Scrolling should be smooth
  });

  test('should maintain performance on mobile devices', async ({ page }) => {
    // Simulate mobile device
    await page.setViewportSize({ width: 375, height: 667 });

    const startTime = Date.now();
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;

    // Mobile should load within reasonable time
    expect(loadTime).toBeLessThan(7000);

    // Test mobile interactions
    await page.goto('/login');
    await page.fill('input[type="email"], input[name="username"]', 'demo_admin');
    await page.fill('input[type="password"]', 'demo_password_123');
    await page.click('button[type="submit"], button:has-text("Login")');
    await page.waitForURL(/.*\/(dashboard|chat|home).*/, { timeout: 10000 });

    await page.goto('/chat');

    // Test mobile chat interaction
    const chatInput = page.locator('[data-testid="chat-input"], textarea, input[placeholder*="message"]').first();
    const sendButton = page.locator('button:has-text("Send"), [data-testid="send-button"]').first();

    const interactionStart = Date.now();
    await chatInput.fill('Mobile performance test');
    await sendButton.click();

    await expect(page.locator('.message, .chat-message').last()).toBeVisible({ timeout: 20000 });
    const interactionTime = Date.now() - interactionStart;

    expect(interactionTime).toBeLessThan(25000); // Mobile interactions should complete reasonably
  });
});