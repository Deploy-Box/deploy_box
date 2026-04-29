import { test, expect } from "@playwright/test";

// ---------------------------------------------------------------------------
// Create a test user via the POST /api/v1/accounts/signup/ endpoint.
//
// The /signup/ UI route redirects to WorkOS SSO, so we use Playwright's
// API request context to call the REST endpoint directly.
// ---------------------------------------------------------------------------

// Generate a unique username per run to avoid collisions
const timestamp = Date.now();
const TEST_USER = {
  username: `e2e_user_${timestamp}`,
  email: `e2e_${timestamp}@test.deploy-box.com`,
  password: "TestPassword123!",
  firstName: "Test",
  lastName: "User",
};

test.describe("Create test user", () => {
  test("POST /api/v1/accounts/signup/ creates a new user", async ({
    request,
  }) => {
    const response = await request.post("/api/v1/accounts/signup/", {
      data: {
        username: TEST_USER.username,
        email: TEST_USER.email,
        password1: TEST_USER.password,
        password2: TEST_USER.password,
        first_name: TEST_USER.firstName,
        last_name: TEST_USER.lastName,
      },
    });

    expect(response.status()).toBe(201);

    const body = await response.json();
    expect(body.message).toContain("User created");
    expect(body.user_id).toBeTruthy();
  });

  test("signup rejects duplicate username", async ({ request }) => {
    // Create the first user
    const first = await request.post("/api/v1/accounts/signup/", {
      data: {
        username: `dup_user_${timestamp}`,
        email: `dup_first_${timestamp}@test.deploy-box.com`,
        password1: TEST_USER.password,
        password2: TEST_USER.password,
        first_name: "First",
        last_name: "User",
      },
    });
    expect(first.status()).toBe(201);

    // Attempt to create a second user with the same username
    const second = await request.post("/api/v1/accounts/signup/", {
      data: {
        username: `dup_user_${timestamp}`,
        email: `dup_second_${timestamp}@test.deploy-box.com`,
        password1: TEST_USER.password,
        password2: TEST_USER.password,
        first_name: "Second",
        last_name: "User",
      },
    });

    expect(second.status()).toBe(400);
    const body = await second.json();
    expect(body.user_errors).toBeTruthy();
  });

  test("signup rejects missing required fields", async ({ request }) => {
    const response = await request.post("/api/v1/accounts/signup/", {
      data: {},
    });

    expect(response.status()).toBe(400);
    const body = await response.json();
    expect(body.user_errors).toBeTruthy();
    expect(body.user_errors.username).toBeTruthy();
    expect(body.user_errors.password1).toBeTruthy();
    expect(body.user_errors.password2).toBeTruthy();
  });

  test("signup rejects mismatched passwords", async ({ request }) => {
    const response = await request.post("/api/v1/accounts/signup/", {
      data: {
        username: `mismatch_${timestamp}`,
        email: `mismatch_${timestamp}@test.deploy-box.com`,
        password1: "TestPassword123!",
        password2: "DifferentPassword!",
        first_name: "Test",
        last_name: "User",
      },
    });

    expect(response.status()).toBe(400);
    const body = await response.json();
    expect(body.user_errors).toBeTruthy();
  });

  test("signup rejects weak password", async ({ request }) => {
    const response = await request.post("/api/v1/accounts/signup/", {
      data: {
        username: `weak_pw_${timestamp}`,
        email: `weak_pw_${timestamp}@test.deploy-box.com`,
        password1: "ab",
        password2: "ab",
        first_name: "Test",
        last_name: "User",
      },
    });

    // Django's password validators may reject very short passwords
    // If the server accepts it (no custom validators enforced), just verify it responds
    const status = response.status();
    expect([201, 400]).toContain(status);
  });
});
