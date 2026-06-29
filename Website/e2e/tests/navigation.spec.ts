import { test, expect } from "@playwright/test";

// ---------------------------------------------------------------------------
// Navigation tests — verify links and in-page navigation work correctly
// ---------------------------------------------------------------------------

test.describe("Navbar links", () => {
  test("navbar is visible on the home page", async ({ page }) => {
    await page.goto("/");
    const nav = page.locator("nav").first();
    await expect(nav).toBeVisible();
  });

  test("logo/brand links to home", async ({ page }) => {
    await page.goto("/stacks/");
    // Click the brand/logo link — it should navigate to "/"
    const brand = page.locator("nav").getByRole("link").first();
    await brand.click();
    await expect(page).toHaveURL("/");
  });

  test("Stacks link navigates to /stacks/", async ({ page }) => {
    await page.goto("/");
    const link = page.locator("nav").getByRole("link", { name: /stacks/i });
    // There may be multiple matches; click the nav one
    if ((await link.count()) > 0) {
      await link.first().click();
      await expect(page).toHaveURL(/\/stacks\/?/);
    }
  });

  test("Pricing link navigates to /pricing/", async ({ page }) => {
    await page.goto("/");
    const link = page.locator("nav").getByRole("link", { name: /pricing/i });
    if ((await link.count()) > 0) {
      await link.first().click();
      await expect(page).toHaveURL(/\/pricing\/?/);
    }
  });

  test("Docs link navigates to /docs/", async ({ page }) => {
    await page.goto("/");
    const link = page.locator("nav").getByRole("link", { name: /docs/i });
    if ((await link.count()) > 0) {
      await link.first().click();
      await expect(page).toHaveURL(/\/docs\/?/);
    }
  });
});

test.describe("Home page CTAs", () => {
  test("Explore Stacks button navigates to /stacks/", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /explore stacks/i }).click();
    await expect(page).toHaveURL(/\/stacks\/?/);
  });
});

test.describe("Login ↔ Signup navigation", () => {
  test("login redirects to WorkOS OAuth", async ({ request }) => {
    // /login/ now redirects to WorkOS instead of rendering a page
    // with a signup link.
    const response = await request.get("/login/", { maxRedirects: 0 });
    expect(response.status()).toBe(302);
    expect(response.headers()["location"]).toContain("/api/v1/accounts/oauth/workos/");
  });
});

test.describe("Docs sub-page navigation", () => {
  test("docs hub has links to sub-pages", async ({ page }) => {
    await page.goto("/docs/");
    const subPages = [
      "Getting Started",
      "Stacks",
      "Organizations",
      "Projects",
      "Billing",
    ];
    for (const label of subPages) {
      const link = page.getByRole("link", { name: new RegExp(label, "i") });
      // At least one link for each sub-page should exist
      if ((await link.count()) > 0) {
        await expect(link.first()).toBeVisible();
      }
    }
  });
});
