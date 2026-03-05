import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  expect: { timeout: 5000 },

  // normally the tests would start a dev server on port 5173, but that
  // port is already occupied by Docker on the CI machine. In order to be able
  // to run the e2e suite against whatever server the developer has running we
  // disable the automatic webServer here. Developers should start the
  // frontend (e.g. `npm run dev`) manually and set BASE_URL when invoking the
  // tests if it differs from the default.
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:5173',
  //   reuseExistingServer: false, // always start fresh so code changes are applied
  //   cwd: __dirname,
  // },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
