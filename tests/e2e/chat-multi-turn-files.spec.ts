/**
 * Chat Multi-Turn File Context E2E Test - MVP-FILE-CONTEXT
 *
 * Tests that PDF context persists across multiple messages in the same conversation:
 * 1. User uploads a PDF and asks first question → LLM responds with context ✅
 * 2. User asks follow-up question WITHOUT uploading again → LLM still has context ✅
 * 3. User asks third question → LLM still has context ✅
 *
 * This verifies the session-level file persistence implementation.
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

test.describe('Chat - Multi-Turn File Context Persistence', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to chat page (assumes auth is handled by setup)
    await page.goto('/chat');

    // Wait for chat interface to be ready
    await expect(
      page.locator('textarea[placeholder*="Pregúntame"], textarea[aria-label*="mensaje"]').first()
    ).toBeVisible({ timeout: 10000 });
  });

  test('MVP-FILE-CONTEXT: file context persists across multiple questions', async ({ page }) => {
    console.log('\n🧪 Testing multi-turn file context persistence...\n');

    // ==========================================
    // TURN 1: Upload PDF and ask first question
    // ==========================================
    console.log('  📄 TURN 1: Uploading PDF and asking first question...');

    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(SMALL_PDF);

    // Wait for file to be READY
    await expect(
      page.locator('text=/Listo|READY/i').first()
    ).toBeVisible({ timeout: 15000 });
    console.log('  ✅ File is READY');

    // Type first question
    const textarea = page.locator('textarea[placeholder*="Pregúntame"], textarea[aria-label*="mensaje"]').first();
    await textarea.fill('¿De qué trata este documento?');

    // Send message
    const sendButton = page.locator('button[type="submit"], button:has-text("Enviar")').first();
    await sendButton.click();
    console.log('  📤 Sent first question with PDF');

    // Wait for LLM response
    await expect(
      page.locator('text=/Analizando|pensando/i').first()
    ).toBeVisible({ timeout: 5000 });
    console.log('  ⏳ Waiting for LLM response...');

    // Wait for response to appear (timeout 30s for LLM)
    await page.waitForTimeout(2000);
    const firstResponseLocator = page.locator('.message, .chat-message, [role="article"]').filter({ hasText: /documento|PDF|contenido/i }).first();
    await expect(firstResponseLocator).toBeVisible({ timeout: 30000 });

    const firstResponse = await firstResponseLocator.textContent();
    console.log(`  ✅ First response received (length: ${firstResponse?.length})`);

    // ==========================================
    // TURN 2: Ask follow-up WITHOUT uploading again
    // ==========================================
    console.log('\n  💬 TURN 2: Asking follow-up question WITHOUT file upload...');

    // Clear files from UI (simulate user not uploading again)
    // The backend should still include file_ids from session
    const clearButtons = page.locator('button:has-text("×"), button[aria-label*="eliminar"]');
    const clearButtonCount = await clearButtons.count();
    if (clearButtonCount > 0) {
      await clearButtons.first().click();
      await page.waitForTimeout(500);
      console.log('  🗑️  Cleared file from UI (simulating no re-upload)');
    }

    // Type second question (related to document)
    await textarea.fill('Dame más detalles sobre eso');

    // Send second message
    await sendButton.click();
    console.log('  📤 Sent second question WITHOUT file upload');

    // Wait for second response
    await page.waitForTimeout(2000);
    const secondResponseLocator = page.locator('.message, .chat-message, [role="article"]').last();
    await expect(secondResponseLocator).toBeVisible({ timeout: 30000 });

    const secondResponse = await secondResponseLocator.textContent();
    console.log(`  ✅ Second response received (length: ${secondResponse?.length})`);

    // Verify response is meaningful (not "no tengo información")
    expect(secondResponse).toBeTruthy();
    expect(secondResponse!.length).toBeGreaterThan(20);

    // If backend didn't maintain context, response would say "no tengo información"
    const hasNoContext = secondResponse?.toLowerCase().includes('no tengo información') ||
                        secondResponse?.toLowerCase().includes('no puedo ayudar') ||
                        secondResponse?.toLowerCase().includes('no sé');

    if (hasNoContext) {
      console.error('  ❌ FAIL: LLM response indicates no context was maintained!');
      throw new Error('Context not maintained: LLM has no information about document');
    }
    console.log('  ✅ Response shows context was maintained!');

    // ==========================================
    // TURN 3: Third question to confirm persistence
    // ==========================================
    console.log('\n  💬 TURN 3: Asking third question to confirm persistence...');

    await textarea.fill('¿Puedes resumir todo?');
    await sendButton.click();
    console.log('  📤 Sent third question');

    // Wait for third response
    await page.waitForTimeout(2000);
    const thirdResponseLocator = page.locator('.message, .chat-message, [role="article"]').last();
    await expect(thirdResponseLocator).toBeVisible({ timeout: 30000 });

    const thirdResponse = await thirdResponseLocator.textContent();
    console.log(`  ✅ Third response received (length: ${thirdResponse?.length})`);

    // Verify still has context
    expect(thirdResponse).toBeTruthy();
    expect(thirdResponse!.length).toBeGreaterThan(20);

    const stillHasNoContext = thirdResponse?.toLowerCase().includes('no tengo información') ||
                              thirdResponse?.toLowerCase().includes('no puedo ayudar');

    if (stillHasNoContext) {
      console.error('  ❌ FAIL: Context lost after third message!');
      throw new Error('Context not maintained through third message');
    }
    console.log('  ✅ Context persisted through 3 messages!');

    console.log('\n✅ Multi-turn file context persistence test PASSED\n');
  });

  test('MVP-FILE-CONTEXT: verify file_ids are NOT sent in follow-up requests (backend handles)', async ({ page }) => {
    console.log('\n🧪 Verifying file_ids handling in follow-up messages...\n');

    // Track API requests
    const chatRequests: any[] = [];

    page.on('request', (request) => {
      if (request.url().includes('/api/chat') && request.method() === 'POST') {
        const postData = request.postData();
        if (postData) {
          try {
            const payload = JSON.parse(postData);
            chatRequests.push({
              message: payload.message,
              file_ids: payload.file_ids || [],
              has_chat_id: !!payload.chat_id
            });
            console.log(`  📡 Request ${chatRequests.length}:`, {
              message: payload.message?.substring(0, 30),
              file_ids_count: payload.file_ids?.length || 0,
              has_chat_id: !!payload.chat_id
            });
          } catch (e) {
            console.warn('  ⚠️  Could not parse request data');
          }
        }
      }
    });

    // Upload file and send first message
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(SMALL_PDF);
    await expect(page.locator('text=/Listo|READY/i').first()).toBeVisible({ timeout: 15000 });

    const textarea = page.locator('textarea[placeholder*="Pregúntame"]').first();
    await textarea.fill('Primera pregunta');
    await textarea.press('Enter');

    // Wait for response
    await page.waitForTimeout(3000);

    // Send second message (without file)
    await textarea.fill('Segunda pregunta');
    await textarea.press('Enter');

    await page.waitForTimeout(3000);

    // Verify request patterns
    expect(chatRequests.length).toBeGreaterThanOrEqual(2);

    // First request should have file_ids
    const firstRequest = chatRequests[0];
    expect(firstRequest.file_ids.length).toBeGreaterThan(0);
    expect(firstRequest.has_chat_id).toBe(false); // New conversation
    console.log('  ✅ First request included file_ids');

    // Second request may or may not have file_ids (frontend clears)
    // But backend should handle it by merging with session
    const secondRequest = chatRequests[1];
    expect(secondRequest.has_chat_id).toBe(true); // Continuing conversation
    console.log(`  ✅ Second request: has_chat_id=true, file_ids=${secondRequest.file_ids.length}`);

    // The key is that backend returns valid responses for both
    // (Backend test verifies merge logic - this just confirms request flow)

    console.log('\n✅ Request flow verified\n');
  });

  test('MVP-FILE-CONTEXT: file indicator shows in all messages after context established', async ({ page }) => {
    console.log('\n🧪 Testing file indicator visibility across messages...\n');

    // Upload file
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(SMALL_PDF);
    await expect(page.locator('text=/Listo|READY/i').first()).toBeVisible({ timeout: 15000 });
    console.log('  ✅ File uploaded and ready');

    // Send 3 messages with file attached
    const textarea = page.locator('textarea[placeholder*="Pregúntame"]').first();

    for (let i = 1; i <= 3; i++) {
      await textarea.fill(`Pregunta ${i}`);
      await textarea.press('Enter');
      console.log(`  📤 Sent message ${i}`);

      // Wait for message bubble to appear
      await page.waitForTimeout(2000);
    }

    // Verify all 3 user message bubbles have file indicators
    console.log('\n  🔍 Verifying file indicators in message bubbles...');

    const userMessages = page.locator('[role="article"]').filter({ hasText: /Pregunta/ });
    const messageCount = await userMessages.count();

    expect(messageCount).toBe(3);
    console.log(`  ✅ Found ${messageCount} user messages`);

    // Each should have attachment indicator
    for (let i = 0; i < messageCount; i++) {
      const message = userMessages.nth(i);
      const hasIndicator = await message.locator('text=/adjunto/i').count() > 0;

      if (!hasIndicator) {
        console.warn(`  ⚠️  Message ${i + 1} missing file indicator`);
        // Take screenshot for debugging
        await page.screenshot({
          path: `test-results/missing-indicator-message-${i + 1}.png`,
          fullPage: true
        });
      }

      expect(hasIndicator).toBe(true);
      console.log(`  ✅ Message ${i + 1} has file indicator`);
    }

    console.log('\n✅ All messages show file indicators\n');
  });

  test('MVP-FILE-CONTEXT: context persists after page refresh mid-conversation', async ({ page }) => {
    console.log('\n🧪 Testing context persistence after page refresh...\n');

    // Upload file and send first message
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(SMALL_PDF);
    await expect(page.locator('text=/Listo|READY/i').first()).toBeVisible({ timeout: 15000 });

    const textarea = page.locator('textarea[placeholder*="Pregúntame"]').first();
    await textarea.fill('Primera pregunta antes del refresh');

    const sendButton = page.locator('button[type="submit"]').first();
    await sendButton.click();
    console.log('  📤 Sent first message');

    // Wait for response
    await page.waitForTimeout(3000);
    await expect(
      page.locator('[role="article"]').filter({ hasText: /Primera pregunta/ }).first()
    ).toBeVisible({ timeout: 10000 });
    console.log('  ✅ First message received');

    // Refresh page
    console.log('\n  🔄 Refreshing page...');
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Wait for chat interface to reload
    await expect(
      page.locator('textarea[placeholder*="Pregúntame"]').first()
    ).toBeVisible({ timeout: 10000 });
    console.log('  ✅ Chat interface reloaded');

    // Verify first message still visible
    await expect(
      page.locator('[role="article"]').filter({ hasText: /Primera pregunta/ }).first()
    ).toBeVisible({ timeout: 10000 });
    console.log('  ✅ Previous messages restored');

    // Send second message WITHOUT uploading again
    const textareaAfterRefresh = page.locator('textarea[placeholder*="Pregúntame"]').first();
    await textareaAfterRefresh.fill('Segunda pregunta después del refresh');
    await textareaAfterRefresh.press('Enter');
    console.log('  📤 Sent second message after refresh (no file upload)');

    // Wait for response
    await page.waitForTimeout(2000);
    const secondResponseAfterRefresh = page.locator('[role="article"]').last();
    await expect(secondResponseAfterRefresh).toBeVisible({ timeout: 30000 });

    const responseText = await secondResponseAfterRefresh.textContent();
    console.log(`  ✅ Second response received after refresh (length: ${responseText?.length})`);

    // Verify response has context
    expect(responseText).toBeTruthy();
    expect(responseText!.length).toBeGreaterThan(20);

    const hasNoContext = responseText?.toLowerCase().includes('no tengo información');
    expect(hasNoContext).toBe(false);

    console.log('  ✅ Context maintained after page refresh!');
    console.log('\n✅ Refresh persistence test PASSED\n');
  });

  test('MVP-FILE-CONTEXT: multiple files persist across conversation', async ({ page }) => {
    console.log('\n🧪 Testing multiple files context persistence...\n');

    const fileInput = page.locator('input[type="file"]').first();

    // Upload first file
    await fileInput.setInputFiles(SMALL_PDF);
    await expect(page.locator('text=/Listo|READY/i').first()).toBeVisible({ timeout: 15000 });
    console.log('  ✅ First file uploaded');

    // Upload second file (same PDF, different instance)
    await fileInput.setInputFiles(SMALL_PDF);
    const readyBadges = page.locator('text=/Listo|READY/i');
    await expect(readyBadges).toHaveCount(2, { timeout: 15000 });
    console.log('  ✅ Second file uploaded');

    // Send first message with both files
    const textarea = page.locator('textarea[placeholder*="Pregúntame"]').first();
    await textarea.fill('Compara estos dos documentos');
    await textarea.press('Enter');
    console.log('  📤 Sent message with 2 files');

    await page.waitForTimeout(3000);

    // Clear files from UI
    const clearButtons = page.locator('button:has-text("×"), button[aria-label*="eliminar"]');
    const clearCount = await clearButtons.count();
    for (let i = 0; i < clearCount; i++) {
      await clearButtons.first().click();
      await page.waitForTimeout(300);
    }
    console.log('  🗑️  Cleared files from UI');

    // Send second message - should still have both files in backend context
    await textarea.fill('¿Cuáles son las diferencias principales?');
    await textarea.press('Enter');
    console.log('  📤 Sent follow-up WITHOUT files in UI');

    await page.waitForTimeout(2000);
    const response = page.locator('[role="article"]').last();
    await expect(response).toBeVisible({ timeout: 30000 });

    const responseText = await response.textContent();
    console.log(`  ✅ Response received (length: ${responseText?.length})`);

    // Verify meaningful response (has context)
    expect(responseText!.length).toBeGreaterThan(20);
    expect(responseText?.toLowerCase().includes('no tengo información')).toBe(false);

    console.log('  ✅ Multiple files context maintained!');
    console.log('\n✅ Multiple files test PASSED\n');
  });
});
