import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  expect: { timeout: 5000 },

  // Normally the tests would start a dev server on port 5173, but that
  // port may be occupied in some CI environments. Tests run against whatever
  // server the developer has running (start with `npm run dev`). Set BASE_URL
  // when invoking the tests if it differs from the default.

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
