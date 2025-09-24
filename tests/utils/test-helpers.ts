import { Page, APIRequestContext, expect } from '@playwright/test';
import * as fs from 'fs';

export interface TestUser {
  username: string;
  password: string;
  email: string;
}

export interface ApiAuthData {
  token: string;
  user: any;
}

/**
 * Load test user data from JSON file
 */
export function getTestUsers(): Record<string, TestUser> {
  try {
    const userData = fs.readFileSync('test-data/users.json', 'utf8');
    return JSON.parse(userData);
  } catch (error) {
    console.warn('Could not load test users, using defaults');
    return {
      demo_admin: {
        username: 'demo_admin',
        password: 'ChangeMe123!',
        email: 'demo@saptiva.ai'
      }
    };
  }
}

/**
 * Get API authentication data
 */
export function getApiAuth(): ApiAuthData | null {
  try {
    const authData = fs.readFileSync('playwright/.auth/api.json', 'utf8');
    return JSON.parse(authData);
  } catch (error) {
    console.warn('Could not load API auth data');
    return null;
  }
}

/**
 * Login a user via the UI
 */
export async function loginUser(page: Page, username: string, password: string) {
  await page.goto('/login');
  await page.fill('input[type="email"], input[name="username"]', username);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"], button:has-text("Login")');
  await page.waitForURL(/.*\/(dashboard|chat|home).*/, { timeout: 15000 });
}

/**
 * Login via API and return token
 */
export async function loginApiUser(request: APIRequestContext, username: string, password: string): Promise<string> {
  const response = await request.post('/api/auth/login', {
    data: { username, password }
  });

  expect(response.status()).toBe(200);
  const authData = await response.json();
  return authData.access_token;
}

/**
 * Create a chat session via API
 */
export async function createChatSession(request: APIRequestContext, token: string, title: string = 'Test Session') {
  const response = await request.post('/api/chat/sessions', {
    headers: { 'Authorization': `Bearer ${token}` },
    data: { title }
  });

  expect(response.status()).toBe(201);
  return await response.json();
}

/**
 * Send a chat message via API
 */
export async function sendChatMessage(
  request: APIRequestContext,
  token: string,
  sessionId: string,
  message: string,
  model: string = 'default'
) {
  const response = await request.post('/api/chat/message', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    data: {
      session_id: sessionId,
      message,
      model
    }
  });

  expect(response.status()).toBe(200);
  return await response.json();
}

/**
 * Wait for chat response to appear in UI
 */
export async function waitForChatResponse(page: Page, timeout: number = 30000) {
  await expect(page.locator('.message, .chat-message').last()).toBeVisible({ timeout });
}

/**
 * Clear chat input and send a message
 */
export async function sendUIMessage(page: Page, message: string) {
  const chatInput = page.locator('[data-testid="chat-input"], textarea, input[placeholder*="message"]').first();
  const sendButton = page.locator('button:has-text("Send"), [data-testid="send-button"]').first();

  await chatInput.fill(message);
  await sendButton.click();
}

/**
 * Check if element exists without throwing
 */
export async function elementExists(page: Page, selector: string): Promise<boolean> {
  try {
    return await page.locator(selector).count() > 0;
  } catch {
    return false;
  }
}

/**
 * Wait for API health check
 */
export async function waitForApiHealth(request: APIRequestContext, maxRetries: number = 10) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await request.get('/api/health');
      if (response.status() === 200) {
        return true;
      }
    } catch (error) {
      // Continue retrying
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  throw new Error('API health check failed after maximum retries');
}

/**
 * Generate random test data
 */
export function generateTestData() {
  const timestamp = Date.now();
  return {
    username: `test_user_${timestamp}`,
    email: `test_${timestamp}@example.com`,
    sessionTitle: `Test Session ${timestamp}`,
    message: `Test message ${timestamp}`,
  };
}

/**
 * Performance measurement helper
 */
export async function measurePerformance<T>(
  operation: () => Promise<T>,
  name: string
): Promise<{ result: T; duration: number }> {
  const start = Date.now();
  const result = await operation();
  const duration = Date.now() - start;

  console.log(`⏱️ ${name}: ${duration}ms`);

  return { result, duration };
}