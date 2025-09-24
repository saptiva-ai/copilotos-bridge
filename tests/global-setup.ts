import { FullConfig } from '@playwright/test';
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting Copilot OS test environment setup...');

  // Ensure test directories exist
  const testDirs = [
    'playwright/.auth',
    'test-results',
    'playwright-report',
    'test-data'
  ];

  for (const dir of testDirs) {
    const fullPath = path.join(process.cwd(), dir);
    if (!fs.existsSync(fullPath)) {
      fs.mkdirSync(fullPath, { recursive: true });
      console.log(`✅ Created directory: ${dir}`);
    }
  }

  // Create test environment file
  const envContent = `
# Test Environment Configuration
SAPTIVA_API_KEY=demo-key-for-testing
JWT_SECRET_KEY=test-jwt-secret-key-for-e2e-tests
MONGODB_URL=mongodb://localhost:27017/copilotos_test
REDIS_URL=redis://localhost:6379/1
LOG_LEVEL=error
NODE_ENV=test
NEXT_PUBLIC_API_URL=http://localhost:8001
API_BASE_URL=http://localhost:8001
BASE_URL=http://localhost:3000
`;

  fs.writeFileSync('.env.test', envContent);
  console.log('✅ Created test environment configuration');

  // Create test user data
  const testUserData = {
    demo_admin: {
      username: 'demo_admin',
      password: 'ChangeMe123!',
      email: 'demo@saptiva.ai'
    },
    test_user_1: {
      username: 'testuser1',
      password: 'TestPass123!',
      email: 'test1@example.com'
    },
    test_user_2: {
      username: 'testuser2',
      password: 'TestPass123!',
      email: 'test2@example.com'
    }
  };

  fs.writeFileSync(
    'test-data/users.json',
    JSON.stringify(testUserData, null, 2)
  );
  console.log('✅ Created test user data');

  // Check if services are running in CI mode
  if (process.env.CI) {
    console.log('🔄 CI mode detected - services should be managed by CI pipeline');
  } else {
    console.log('💻 Local mode - checking for running services...');

    // Check if services are already running
    try {
      execSync('curl -f http://localhost:8001/api/health', {
        stdio: 'pipe',
        timeout: 5000
      });
      console.log('✅ API service is already running');
    } catch {
      console.log('⚠️ API service not running - will attempt to start via webServer');
    }

    try {
      execSync('curl -f http://localhost:3000', {
        stdio: 'pipe',
        timeout: 5000
      });
      console.log('✅ Frontend service is already running');
    } catch {
      console.log('⚠️ Frontend service not running - will attempt to start via webServer');
    }
  }

  console.log('🎯 Global setup completed successfully!');
}

export default globalSetup;