import { defineConfig, devices } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:5174';

export default defineConfig({
  testDir: '.',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,
  workers: 2,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    // Order matters: login is rate-limited to 5/min per IP.
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
      testIgnore: /cross-cutting\.spec\.ts/,
    },
    {
      // Exhausts the login limit, so it runs last.
      name: 'rate-limit',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['chromium'],
      testMatch: /cross-cutting\.spec\.ts/,
    },
  ],
});
