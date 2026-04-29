import { test, expect } from "@playwright/test";

// ---------------------------------------------------------------------------
// Smoke tests — verify every public page loads with correct content
// ---------------------------------------------------------------------------

test.describe("Home page", () => {
  test("renders hero section with tagline", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Deploy Box/i);
    await expect(page.locator("h1")).toContainText("faster than ever");
  });

  test("shows Explore Stacks CTA", async ({ page }) => {
    await page.goto("/");
    const cta = page.getByRole("link", { name: /explore stacks/i });
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute("href", /\/stacks\//);
  });

  test("displays DEPLOY_BOX_V2.0 badge", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("DEPLOY_BOX_V2.0")).toBeVisible();
  });

  test("shows 'Why Deploy Box?' features section", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Why Deploy Box?")).toBeVisible();
  });
});

test.describe("Stacks page", () => {
  test("renders stacks heading", async ({ page }) => {
    await page.goto("/stacks/");
    await expect(page.locator("h1")).toContainText("Stacks");
  });

  test("shows BUILD / SHIP / SCALE indicators", async ({ page }) => {
    await page.goto("/stacks/");
    await expect(page.getByText("BUILD", { exact: true })).toBeVisible();
    await expect(page.getByText("SHIP", { exact: true })).toBeVisible();
    await expect(page.getByText("SCALE", { exact: true })).toBeVisible();
  });
});

const stackPages = [
  { path: "/stacks/mern/", name: "MERN" },
  { path: "/stacks/django/", name: "Django" },
  { path: "/stacks/mean/", name: "MEAN" },
  { path: "/stacks/lamp/", name: "LAMP" },
  { path: "/stacks/mevn/", name: "MEVN" },
  { path: "/stacks/mobile/", name: "Mobile" },
  { path: "/stacks/llm/", name: "LLM" },
  { path: "/stacks/ai-data/", name: "AI Data" },
  { path: "/stacks/computer-vision/", name: "Computer Vision" },
  { path: "/stacks/image-generation/", name: "Image Generation" },
  { path: "/stacks/ai-agents/", name: "AI Agents" },
];

for (const stack of stackPages) {
  test(`Stack page: ${stack.name} loads successfully`, async ({ page }) => {
    const response = await page.goto(stack.path);
    expect(response?.status()).toBe(200);
    await expect(page).toHaveTitle(/Deploy Box/i);
  });
}

test.describe("Pricing page", () => {
  test("renders pricing heading", async ({ page }) => {
    await page.goto("/pricing/");
    await expect(page.locator("h1")).toContainText("Free to deploy");
  });

  test("shows stack pricing table", async ({ page }) => {
    await page.goto("/pricing/");
    await expect(page.getByRole("columnheader", { name: "Stack Tier" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Setup Fee" })).toBeVisible();
  });
});

test.describe("Contact page", () => {
  test("loads successfully", async ({ page }) => {
    const response = await page.goto("/contact/");
    expect(response?.status()).toBe(200);
    await expect(page).toHaveTitle(/Deploy Box/i);
  });
});

test.describe("Docs pages", () => {
  test("docs hub loads", async ({ page }) => {
    const response = await page.goto("/docs/");
    expect(response?.status()).toBe(200);
  });

  const docSubPages = [
    "/docs/getting-started/",
    "/docs/stacks/",
    "/docs/organizations/",
    "/docs/projects/",
    "/docs/billing/",
    "/docs/api/",
  ];

  for (const docPath of docSubPages) {
    test(`doc sub-page ${docPath} loads`, async ({ page }) => {
      const response = await page.goto(docPath);
      expect(response?.status()).toBe(200);
    });
  }
});

test.describe("Login page", () => {
  test("redirects to WorkOS OAuth endpoint", async ({ request }) => {
    // /login/ now redirects to the WorkOS OAuth flow rather than
    // rendering a local template.
    const response = await request.get("/login/", { maxRedirects: 0 });
    expect(response.status()).toBe(302);
    expect(response.headers()["location"]).toContain("/api/v1/accounts/oauth/workos/");
  });
});

test.describe("Signup page", () => {
  test("loads successfully", async ({ page }) => {
    const response = await page.goto("/signup/");
    expect(response?.status()).toBe(200);
  });
});

test.describe("Marketplace page", () => {
  test("loads successfully", async ({ page }) => {
    const response = await page.goto("/marketplace/");
    expect(response?.status()).toBe(200);
    await expect(page).toHaveTitle(/Deploy Box/i);
  });
});
