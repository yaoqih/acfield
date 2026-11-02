import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/docs',
  fullyParallel: true,
  workers: process.env.CI ? 2 : 4,
  reporter: 'list',
  use: {
    baseURL: process.env.DOCS_TEST_URL || 'http://127.0.0.1:4175/acfield/',
    trace: 'retain-on-failure',
    ...devices['Desktop Chrome'],
    viewport: { width: 1440, height: 1000 },
    launchOptions: process.env.DOCS_CHROME_PATH
      ? { executablePath: process.env.DOCS_CHROME_PATH } : {}
  },
  webServer: process.env.DOCS_TEST_URL ? undefined : {
    command: 'npm run docs:preview -- --port 4175',
    url: 'http://127.0.0.1:4175/acfield/',
    reuseExistingServer: false
  }
})
