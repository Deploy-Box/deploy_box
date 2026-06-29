import { test, expect } from "@playwright/test";

// ---------------------------------------------------------------------------
// Auth redirect tests — unauthenticated users should be sent to /login/
// ---------------------------------------------------------------------------

const protectedPaths = [
  "/dashboard/",
  "/profile/",
  "/dashboard/organizations/",
  "/dashboard/transfers/",
];

for (const path of protectedPaths) {
  test(`${path} redirects unauthenticated user to /login/`, async ({
    request,
  }) => {
    // Use the API request context with maxRedirects: 0 to verify
    // the middleware issues a 302 to /login/ without following
    // the redirect chain into WorkOS SSO.
    const response = await request.get(path, { maxRedirects: 0 });
    expect(response.status()).toBe(302);
    expect(response.headers()["location"]).toContain("/login");
  });
}

test.describe("Public pages do NOT redirect", () => {
  const publicPaths = [
    "/",
    "/stacks/",
    "/pricing/",
    "/contact/",
    "/login/",
    "/signup/",
    "/marketplace/",
    "/docs/",
  ];

  for (const path of publicPaths) {
    test(`${path} does not redirect to login`, async ({ request }) => {
      // Use API request with maxRedirects: 0 to check the response
      // doesn't redirect to /login/ at all.
      const response = await request.get(path, { maxRedirects: 0 });
      const status = response.status();
      if (status >= 300 && status < 400) {
        const location = response.headers()["location"] || "";
        expect(location).not.toContain("/login");
      } else {
        expect(status).toBeLessThan(400);
      }
    });
  }
});
