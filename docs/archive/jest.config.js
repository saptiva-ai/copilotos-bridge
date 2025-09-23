const nextJest = require('next/jest')

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files
  dir: './apps/web',
})

// Add any custom config to be passed to Jest
const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  collectCoverageFrom: [
    'apps/web/src/**/*.{js,jsx,ts,tsx}',
    '!apps/web/src/**/*.d.ts',
    '!apps/web/src/**/*.stories.{js,jsx,ts,tsx}',
    '!apps/web/src/**/node_modules/**',
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
  testMatch: [
    '<rootDir>/apps/web/src/**/__tests__/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/apps/web/src/**/*.(test|spec).{js,jsx,ts,tsx}',
    '<rootDir>/tests/**/*.(test|spec).{js,jsx,ts,tsx}',
  ],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/apps/web/src/$1',
    '^@/components/(.*)$': '<rootDir>/apps/web/src/components/$1',
    '^@/lib/(.*)$': '<rootDir>/apps/web/src/lib/$1',
  },
}

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig)