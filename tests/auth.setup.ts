import { test as setup, expect } from '@playwright/test';
import * as fs from 'fs';

const authFile = 'playwright/.auth/user.json';

setup('authenticate as demo user', async ({ page }) => {
  console.log('🔐 Setting up authentication for E2E tests...');

  // Go to the login page
  await page.goto('/login');

  // Wait for the login form to be visible using semantic selectors
  await expect(page.getByLabel('Correo electrónico o usuario')).toBeVisible();

  // Fill in the demo credentials using accessible labels
  await page.getByLabel('Correo electrónico o usuario').fill('demo');
  await page.getByLabel('Contraseña').fill('Demo1234');

  // Submit the form using accessible role
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();

  // Wait for successful login - should redirect to dashboard/chat
  await page.waitForURL(/.*\/(dashboard|chat|home).*/, { timeout: 15000 });

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