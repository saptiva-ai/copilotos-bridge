import { test as setup, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const authFile = 'playwright/.auth/user.json';

setup('authenticate programmatically', async ({ request, page }) => {
  console.log('🔐 Performing programmatic login to stabilize sessions...');

  // Step 1: Programmatic API Login
  // We use the same credentials but hit the endpoint directly
  const response = await request.post('/api/auth/login', {
    data: {
      identifier: 'demo',
      password: process.env.E2E_USER_PASSWORD || 'Demo1234',
    }
  });

  if (response.status() !== 200) {
    const errorBody = await response.text();
    console.error('❌ Programmatic login failed:', errorBody);
    throw new Error(`Failed to login via API: ${response.status()}`);
  }

  const authData = await response.json();
  const token = authData.access_token;
  
  console.log('✅ API Token obtained successfully.');

  // Step 2: Manually construct the storage state to include the JWT
  // This avoids UI flakes and race conditions
  await page.goto('/login'); // Navigate to domain to set context
  
  await page.evaluate((token) => {
    // Inyectamos tanto en localStorage como en sessionStorage para cubrir todos los frentes
    localStorage.setItem('auth-storage', JSON.stringify({
      state: {
        accessToken: token,
        refreshToken: null, // Si el backend no devuelve uno aquí
        user: { id: 'demo-id', username: 'demo' }, // Datos mínimos para hidratación
        status: 'authenticated'
      },
      version: 0
    }));
    
    sessionStorage.setItem('accessToken', token);
  }, token);

  // Step 3: Verify navigation to chat works with this injected state
  await page.goto('/chat');
  await expect(page).toHaveURL(/.*\/chat/, { timeout: 10000 });
  
  // Step 4: Save the verified state
  await page.context().storageState({ path: authFile });
  console.log('✅ Storage state saved with valid token.');
});
