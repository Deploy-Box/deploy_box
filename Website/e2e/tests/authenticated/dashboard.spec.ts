import { test, expect } from "@playwright/test";

// ---------------------------------------------------------------------------
// Authenticated tests — uses the session cookie created by global-setup.ts
// storageState is set in playwright.config.ts for the "authenticated" project
// ---------------------------------------------------------------------------

test.describe("Dashboard", () => {
  test("authenticated user can access /dashboard/", async ({ page }) => {
    await page.goto("/dashboard/");
    // Should NOT redirect to /login
    await expect(page).not.toHaveURL(/\/login/);
  });

  test("dashboard shows organization selector or org dashboard", async ({
    page,
  }) => {
    await page.goto("/dashboard/");
    const url = page.url();
    // User with an org gets redirected to org dashboard; without, sees org selector
    const isOrgDashboard = /\/dashboard\/organizations\//.test(url);
    const isOrgSelector = /\/dashboard\/?$/.test(url) || /\/organizations\/?$/.test(url);
    expect(isOrgDashboard || isOrgSelector).toBe(true);
  });

  test("organization dashboard loads for test org", async ({ page }) => {
    // Go to dashboard — it should redirect to the test org's dashboard
    await page.goto("/dashboard/");
    // Wait for navigation to settle
    await page.waitForLoadState("networkidle");
    // Should see org dashboard content or org selector
    const heading = page.locator("h1, h2, h3").first();
    await expect(heading).toBeVisible();
  });
});

test.describe("Profile", () => {
  test("authenticated user can access /profile/", async ({ page }) => {
    await page.goto("/profile/");
    await expect(page).not.toHaveURL(/\/login/);
    expect(page.url()).toMatch(/\/profile\/?/);
  });
});

test.describe("Dashboard navigation", () => {
  test("org selector page loads", async ({ page }) => {
    await page.goto("/dashboard/organizations/");
    await expect(page).not.toHaveURL(/\/login/);
    const response = await page.goto("/dashboard/organizations/");
    expect(response?.status()).toBeLessThan(400);
  });

  test("transfer invitations page loads", async ({ page }) => {
    await page.goto("/dashboard/transfers/");
    await expect(page).not.toHaveURL(/\/login/);
    const response = await page.goto("/dashboard/transfers/");
    expect(response?.status()).toBeLessThan(400);
  });
});
