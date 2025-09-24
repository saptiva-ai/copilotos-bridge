import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility', () => {
  test('should not have any automatically detectable accessibility issues on the login page', async ({ page }) => {
    await page.goto('/login');

    const accessibilityScanResults = await new AxeBuilder({ page }).analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('should not have any automatically detectable accessibility issues on the chat page', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="email"], input[name="username"]', 'demo_admin');
    await page.fill('input[type="password"]', 'ChangeMe123!');
    await page.click('button[type="submit"], button:has-text("Login")');
    await page.waitForURL(/.*\/chat.*/);

    const accessibilityScanResults = await new AxeBuilder({ page }).analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });
});
