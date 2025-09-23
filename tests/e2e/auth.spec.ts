import { test, expect } from '@playwright/test';
import { getTestUsers, loginUser, measurePerformance } from '../utils/test-helpers';

test.describe('Authentication Flow', () => {
  const users = getTestUsers();

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display login form on unauthenticated access', async ({ page }) => {
    // Should redirect to login or show login form
    await expect(page).toHaveURL(/.*\/(login|auth).*/);

    // Check for login form elements
    await expect(page.locator('input[type="email"], input[name="username"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"], button:has-text("Login")').first()).toBeVisible();
  });

  test('should show validation errors for invalid credentials', async ({ page }) => {
    await page.goto('/login');

    // Fill invalid credentials
    await page.fill('input[type="email"], input[name="username"]', 'invalid@test.com');
    await page.fill('input[type="password"]', 'wrongpassword');

    // Submit form
    await page.click('button[type="submit"], button:has-text("Login")');

    // Wait for error message
    await expect(page.locator('text=/invalid.*credentials|error|failed/i').first()).toBeVisible({ timeout: 5000 });
  });

  test('should successfully login with demo credentials', async ({ page }) => {
    const { result: loginResult, duration } = await measurePerformance(
      async () => {
        await loginUser(page, users.demo_admin.username, users.demo_admin.password);
        return true;
      },
      'Login flow'
    );

    // Performance baseline: login should complete within 10 seconds
    expect(duration).toBeLessThan(10000);

    // Check for authenticated state indicators
    await expect(page.locator('text=/welcome|dashboard|chat/i').first()).toBeVisible();
  });

  test('should persist authentication across page reloads', async ({ page, context }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[type="email"], input[name="username"]', 'demo_admin');
    await page.fill('input[type="password"]', 'demo_password_123');
    await page.click('button[type="submit"], button:has-text("Login")');

    // Wait for redirect
    await page.waitForURL(/.*\/(dashboard|chat|home).*/, { timeout: 10000 });

    // Reload page
    await page.reload();

    // Should still be authenticated
    await expect(page).not.toHaveURL(/.*\/(login|auth).*/);
    await expect(page.locator('text=/welcome|dashboard|chat/i').first()).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[type="email"], input[name="username"]', 'demo_admin');
    await page.fill('input[type="password"]', 'demo_password_123');
    await page.click('button[type="submit"], button:has-text("Login")');

    await page.waitForURL(/.*\/(dashboard|chat|home).*/, { timeout: 10000 });

    // Find and click logout button
    const logoutButton = page.locator('button:has-text("Logout"), a:has-text("Logout"), [data-testid="logout"]').first();
    await logoutButton.click();

    // Should redirect to login
    await expect(page).toHaveURL(/.*\/(login|auth).*/, { timeout: 5000 });
  });
});