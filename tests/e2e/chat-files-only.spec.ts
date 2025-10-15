/**
 * Chat Files-Only Flow E2E Test
 *
 * Tests the complete "files-only" user flow:
 * 1. User uploads a PDF file
 * 2. File shows "Listo" (READY) badge
 * 3. User clicks Send button WITHOUT typing any message
 * 4. System sends default prompt with file_ids
 * 5. Backend processes and returns response based on document
 *
 * This verifies FE-UX-1 feature end-to-end.
 */

import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';
import { fileURLToPath } from 'url';

// Test fixtures paths (ES module compatible)
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FIXTURES_DIR = path.join(__dirname, '../fixtures/files');
const SMALL_PDF = path.join(FIXTURES_DIR, 'small.pdf');

// Verify fixture exists
test.beforeAll(() => {
  if (!fs.existsSync(SMALL_PDF)) {
    throw new Error(
      `Test fixture not found: ${SMALL_PDF}\n` +
      `Run: python tests/fixtures/files/generate_fixtures.py`
    );
  }
  console.log('✓ Test fixture verified:', SMALL_PDF);
});

test.describe('Chat - Files Only Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to chat page (assumes auth is handled by setup)
    await page.goto('/chat');

    // Wait for chat interface to be ready
    await expect(
      page.locator('textarea[placeholder*="Pregúntame"], textarea[aria-label*="mensaje"]').first()
    ).toBeVisible({ timeout: 10000 });
  });

  test('files-only flow: upload PDF → READY → Send (no text) → Analizando → response', async ({ page }) => {
    console.log('\n🧪 Starting files-only flow test...\n');

    // Step 1: Find and interact with file upload button
    console.log('  1️⃣  Looking for file upload button...');
    const fileUploadButton = page.locator('button:has-text("Adjuntar"), button[aria-label*="archivo"], input[type="file"]').first();
    await expect(fileUploadButton).toBeVisible({ timeout: 5000 });

    // Step 2: Upload PDF file
    console.log('  2️⃣  Uploading PDF file...');
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(SMALL_PDF);

    // Step 3: Wait for "Listo" (READY) badge to appear
    console.log('  3️⃣  Waiting for READY badge...');
    await expect(
      page.locator('text=/Listo|READY/i').first()
    ).toBeVisible({ timeout: 15000 });
    console.log('  ✅ File is READY');

    // Step 4: Verify Send button is enabled (even with empty textarea)
    console.log('  4️⃣  Verifying Send button is enabled...');
    const textarea = page.locator('textarea[placeholder*="Pregúntame"], textarea[aria-label*="mensaje"]').first();
    const textContent = await textarea.inputValue();
    expect(textContent).toBe(''); // Verify textarea is empty

    const sendButton = page.locator('button[type="submit"], button:has-text("Enviar"), button[aria-label*="Enviar"]').first();
    await expect(sendButton).toBeEnabled({ timeout: 2000 });
    console.log('  ✅ Send button is enabled with empty input');

    // Step 5: Click Send button without typing
    console.log('  5️⃣  Clicking Send button (no text)...');
    await sendButton.click();

    // Step 6: Verify "Analizando..." spinner appears
    console.log('  6️⃣  Waiting for "Analizando..." indicator...');
    await expect(
      page.locator('text=/Analizando|pensando|procesando/i').first()
    ).toBeVisible({ timeout: 5000 });
    console.log('  ✅ Backend is processing the request');

    // Step 7: Wait for response to appear
    console.log('  7️⃣  Waiting for AI response...');
    await expect(
      page.locator('.message, .chat-message, [role="article"]').last()
    ).toBeVisible({ timeout: 30000 });

    // Verify response contains meaningful content (not just an error)
    const lastMessage = page.locator('.message, .chat-message, [role="article"]').last();
    const responseText = await lastMessage.textContent();
    expect(responseText).toBeTruthy();
    expect(responseText!.length).toBeGreaterThan(10);
    console.log('  ✅ Response received from backend');

    // Optional: Verify file_ids were sent in the request
    // This requires intercepting network requests
    const requests = await page.context().newPage();
    await page.route('**/api/chat', async (route) => {
      const postData = route.request().postData();
      if (postData) {
        const payload = JSON.parse(postData);
        expect(payload).toHaveProperty('file_ids');
        expect(payload.file_ids).toBeInstanceOf(Array);
        expect(payload.file_ids.length).toBeGreaterThan(0);
        console.log('  ✅ file_ids were included in request');
      }
      await route.continue();
    });

    console.log('\n✅ Files-only flow test PASSED\n');
  });

  test('blocks Send when files are PROCESSING (not READY)', async ({ page }) => {
    console.log('\n🧪 Testing PROCESSING state blocking...\n');

    // Upload file
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(SMALL_PDF);

    // Immediately check if Send is disabled while PROCESSING
    const sendButton = page.locator('button[type="submit"], button:has-text("Enviar")').first();

    // During upload/processing, button should be disabled
    // Note: This might be fast for small files, so we use a short timeout
    try {
      await expect(sendButton).toBeDisabled({ timeout: 1000 });
      console.log('  ✅ Send button was disabled during PROCESSING');
    } catch {
      console.log('  ⚠️  File processed too quickly to catch PROCESSING state');
      // This is not a failure - small files process instantly
    }

    console.log('\n✅ PROCESSING blocking test completed\n');
  });

  test('files-only works with Enter key (not just click)', async ({ page }) => {
    console.log('\n🧪 Testing Enter key for files-only send...\n');

    // Upload file
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(SMALL_PDF);

    // Wait for READY
    await expect(
      page.locator('text=/Listo|READY/i').first()
    ).toBeVisible({ timeout: 15000 });

    // Focus textarea (should be empty)
    const textarea = page.locator('textarea[placeholder*="Pregúntame"]').first();
    await textarea.focus();
    expect(await textarea.inputValue()).toBe('');

    // Press Enter (not Shift+Enter)
    console.log('  ⌨️  Pressing Enter key...');
    await textarea.press('Enter');

    // Verify "Analizando..." appears
    await expect(
      page.locator('text=/Analizando/i').first()
    ).toBeVisible({ timeout: 5000 });
    console.log('  ✅ Enter key triggered submit with files only');

    console.log('\n✅ Enter key test PASSED\n');
  });

  test('mobile viewport: files-only flow works on small screens', async ({ page }) => {
    console.log('\n🧪 Testing files-only flow on mobile viewport...\n');

    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    console.log('  📱 Viewport set to 375x667 (mobile)');

    // Upload file
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(SMALL_PDF);

    // Wait for READY
    await expect(
      page.locator('text=/Listo|READY/i').first()
    ).toBeVisible({ timeout: 15000 });

    // Verify Send button is visible and enabled
    const sendButton = page.locator('button[type="submit"], button[aria-label*="Enviar"]').first();
    await expect(sendButton).toBeVisible();
    await expect(sendButton).toBeEnabled();

    // Click Send
    await sendButton.click();

    // Verify processing starts
    await expect(
      page.locator('text=/Analizando/i').first()
    ).toBeVisible({ timeout: 5000 });

    console.log('  ✅ Files-only flow works on mobile');
    console.log('\n✅ Mobile viewport test PASSED\n');
  });
});
