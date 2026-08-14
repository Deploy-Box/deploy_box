import { defineConfig, devices } from "@playwright/test";

const BASE_URL = process.env.BASE_URL ?? "http://localhost:8001";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["html", { open: "never" }], ["list"]],

  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  globalSetup: "./global-setup.ts",

  projects: [
    // Public pages — no auth needed
    {
      name: "public",
      testMatch: [
        "public-pages.spec.ts",
        "navigation.spec.ts",
        "auth-redirects.spec.ts",
        "create-user.spec.ts",
      ],
      use: { ...devices["Desktop Chrome"] },
    },

    // Authenticated pages — use stored session state
    {
      name: "authenticated",
      testDir: "./tests/authenticated",
      use: {
        ...devices["Desktop Chrome"],
        storageState: ".auth/user.json",
      },
    },
  ],
});
