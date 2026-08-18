import { defineConfig, devices } from '@playwright/test';

/**
 * E2E config. Assumes the app stack (frontend :3001, backend :3081, and for
 * the core-workflow spec, celery-worker + vet-thorax-service) is already
 * running — see e2e/README.md. Playwright does not manage the stack itself
 * because it's a multi-container Docker Compose app, not a single dev server.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['html', { open: 'never' }], ['list']] : 'list',
  timeout: 60_000,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3001',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
