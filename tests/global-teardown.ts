import { FullConfig } from '@playwright/test';
import * as fs from 'fs';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Starting Copilot OS test environment cleanup...');

  // Clean up test environment file
  if (fs.existsSync('.env.test')) {
    fs.unlinkSync('.env.test');
    console.log('✅ Cleaned up test environment file');
  }

  // Clean up temporary test data (but keep auth state for debugging)
  const tempFiles = [
    'test-data/temp-*',
    'test-results/temp-*'
  ];

  for (const pattern of tempFiles) {
    try {
      const files = require('glob').sync(pattern);
      for (const file of files) {
        fs.unlinkSync(file);
      }
      if (files.length > 0) {
        console.log(`✅ Cleaned up ${files.length} temporary files`);
      }
    } catch (error) {
      // Ignore errors during cleanup
    }
  }

  // Log test results summary
  if (fs.existsSync('test-results/e2e-results.json')) {
    try {
      const results = JSON.parse(fs.readFileSync('test-results/e2e-results.json', 'utf8'));
      const stats = results.stats || {};
      console.log(`📊 Test Summary: ${stats.passed || 0} passed, ${stats.failed || 0} failed, ${stats.skipped || 0} skipped`);
    } catch (error) {
      console.log('📊 Could not parse test results');
    }
  }

  console.log('🎯 Global teardown completed!');
}

export default globalTeardown;