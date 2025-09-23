// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Copilot OS App', () => {
  test('should load homepage successfully', async ({ page }) => {
    await page.goto('/');

    // Check that the page loads
    await expect(page).toHaveTitle(/Copilot OS/);

    // Check for main navigation or key elements
    await expect(page.locator('body')).toBeVisible();
  });

  test('should navigate to chat page', async ({ page }) => {
    await page.goto('/');

    // Try to find and click a chat link (adjust selector as needed)
    const chatLink = page.locator('a[href*="chat"], button:has-text("Chat")').first();
    if (await chatLink.count() > 0) {
      await chatLink.click();
      await expect(page).toHaveURL(/.*chat.*/);
    }
  });

  test('should handle API health check', async ({ page }) => {
    // Test that the API health endpoint is accessible
    const response = await page.request.get('/api/health');
    expect(response.status()).toBe(200);

    const health = await response.json();
    expect(health.status).toBe('healthy');
  });

  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 }); // iPhone size
    await page.goto('/');

    await expect(page.locator('body')).toBeVisible();

    // Check that the layout adapts to mobile
    const mainContent = page.locator('main, [role="main"], .main-content').first();
    if (await mainContent.count() > 0) {
      await expect(mainContent).toBeVisible();
    }
  });

  test('should load without console errors', async ({ page }) => {
    const consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto('/');

    // Wait for the page to fully load
    await page.waitForLoadState('networkidle');

    // Check that there are no critical console errors
    const criticalErrors = consoleErrors.filter(error =>
      !error.includes('favicon') &&
      !error.includes('_next/static') &&
      !error.includes('chunk')
    );

    expect(criticalErrors).toHaveLength(0);
  });
});
