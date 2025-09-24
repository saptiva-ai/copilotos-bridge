import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('UI Smoke Tests', () => {
  test('Landing page should load correctly and pass accessibility check', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Copilot OS/);
    await expect(page.locator('h1')).toContainText('Acceso a SAPTIVA');

    // Visual regression test
    await expect(page).toHaveScreenshot('landing-page.png');

    // Accessibility check
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('Login page should load correctly and pass accessibility check', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveTitle(/Login/);
    await expect(page.locator('h1')).toContainText('Iniciar sesión');

    // Visual regression test
    await expect(page).toHaveScreenshot('login-page.png');

    // Accessibility check
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('Register page should load correctly and pass accessibility check', async ({ page }) => {
    await page.goto('/register');
    await expect(page).toHaveTitle(/Crear cuenta/);
    await expect(page.locator('h1')).toContainText('Crear una cuenta');

    // Visual regression test
    await expect(page).toHaveScreenshot('register-page.png');

    // Accessibility check
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('Chat page should load correctly for an authenticated user and pass accessibility check', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[type="email"], input[name="username"]', 'demo_admin');
    await page.fill('input[type="password"]', 'ChangeMe123!');
    await page.click('button[type="submit"], button:has-text("Login")');
    await page.waitForURL(/.*\/chat.*/);

    await expect(page).toHaveTitle(/Chat/);

    // Visual regression test
    await expect(page).toHaveScreenshot('chat-page.png');

    // Accessibility check
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
    expect(accessibilityScanResults.violations).toEqual([]);
  });
});
