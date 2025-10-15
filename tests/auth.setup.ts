import { test as setup, expect } from '@playwright/test';
import * as fs from 'fs';

const authFile = 'playwright/.auth/user.json';

setup('authenticate as demo user', async ({ page }) => {
  console.log('🔐 Setting up authentication for E2E tests...');

  // Go to the login page
  await page.goto('/login');

  // Wait for the login form to be visible
  await expect(page.locator('input[type="email"], input[name="username"]')).toBeVisible();

  // Fill in the demo credentials
  await page.fill('input[type="email"], input[name="username"]', 'demo');
  await page.fill('input[type="password"]', 'Demo1234');

  // Submit the form
  await page.click('button[type="submit"], button:has-text("Login")');

  // Wait for successful login - should redirect to dashboard/chat
  await page.waitForURL(/.*\/(dashboard|chat|home).*/, { timeout: 15000 });

  // Verify we're authenticated by checking for authenticated content
  await expect(page.locator('text=/welcome|dashboard|chat/i')).toBeVisible();

  // Save authentication state
  await page.context().storageState({ path: authFile });

  console.log('✅ Authentication setup completed successfully');
});

setup('verify API authentication', async ({ request }) => {
  console.log('🔐 Setting up API authentication...');

  // Test API authentication
  const response = await request.post('/api/auth/login', {
    data: {
      identifier: 'demo',
      password: 'Demo1234'
    }
  });

  expect(response.status()).toBe(200);

  const authData = await response.json();
  expect(authData.access_token).toBeDefined();

  // Store API token for other tests
  const apiAuth = {
    token: authData.access_token,
    user: authData.user
  };

  fs.writeFileSync('playwright/.auth/api.json', JSON.stringify(apiAuth, null, 2));

  console.log('✅ API authentication setup completed successfully');
});