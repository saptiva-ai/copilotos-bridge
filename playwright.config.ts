import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration for Copilot OS E2E Tests
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 3 : 1,
  workers: process.env.CI ? 2 : undefined,
  timeout: process.env.CI ? 60000 : 30000,

  reporter: [
    ['html', {
      outputFolder: 'playwright-report',
      open: process.env.CI ? 'never' : 'on-failure'
    }],
    ['junit', { outputFile: 'test-results/e2e-results.xml' }],
    ['json', { outputFile: 'test-results/e2e-results.json' }],
    ['github'], // GitHub Actions annotations
    process.env.CI ? ['dot'] : ['list']
  ],

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,
    navigationTimeout: 30000,

    // Better error handling
    ignoreHTTPSErrors: true,

    // Performance tracking
    extraHTTPHeaders: {
      'X-Test-Run': process.env.GITHUB_RUN_ID || 'local',
    },
  },

  expect: {
    timeout: 10000,
    toHaveScreenshot: { threshold: 0.3, mode: 'percent' },
    toMatchScreenshot: { threshold: 0.3, mode: 'percent' },
  },

  projects: [
    // Setup project for authentication
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },

    // Desktop browsers
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Use auth from setup
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },

    // Mobile devices (run in CI only on develop/main)
    ...(process.env.CI && ['develop', 'main'].includes(process.env.GITHUB_REF_NAME || '') ? [
      {
        name: 'Mobile Chrome',
        use: {
          ...devices['Pixel 5'],
          storageState: 'playwright/.auth/user.json',
        },
        dependencies: ['setup'],
      },
      {
        name: 'Mobile Safari',
        use: {
          ...devices['iPhone 12'],
          storageState: 'playwright/.auth/user.json',
        },
        dependencies: ['setup'],
      },
    ] : []),

    // API testing project
    {
      name: 'api',
      testMatch: /.*api\.spec\.ts/,
      use: {
        baseURL: process.env.API_BASE_URL || 'http://localhost:8001',
      },
    },

    // Performance testing project
    {
      name: 'performance',
      testMatch: /.*performance\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],

  webServer: process.env.CI ? undefined : {
    command: 'make dev',
    url: 'http://127.0.0.1:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
    stdout: 'ignore',
    stderr: 'pipe',
  },

  // Global setup and teardown
  globalSetup: './tests/global-setup.ts',
  globalTeardown: './tests/global-teardown.ts',
});