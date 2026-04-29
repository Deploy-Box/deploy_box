/**
 * Playwright global setup — reads the session key created during Docker
 * container startup (setup_e2e management command), then persists the
 * session cookie as a Playwright storageState file.
 */
import { chromium, type FullConfig } from "@playwright/test";
import { execSync } from "child_process";
import * as fs from "fs";
import * as path from "path";

async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0]?.use?.baseURL ?? "http://localhost:8001";

  // Wait for Django to be ready (healthcheck may still be settling)
  await waitForServer(baseURL, 120);

  // Read the session key file that was created during container startup.
  // The startup command runs: python manage.py setup_e2e --create-org > /app/e2e_session.txt
  const output = execSync(
    "docker exec deploy-box-e2e-django cat /app/e2e_session.txt",
    { encoding: "utf-8", timeout: 10_000 }
  );

  const match = output.match(/E2E_SESSION_KEY=(\S+)/);
  if (!match) {
    throw new Error(`setup_e2e session key not found. File contents:\n${output}`);
  }
  const sessionId = match[1];

  console.log(`  ✓ E2E session ready (sessionid=${sessionId.slice(0, 8)}…)`);

  // Save storageState with the session cookie
  const authDir = path.join(__dirname, ".auth");
  fs.mkdirSync(authDir, { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext();

  await context.addCookies([
    {
      name: "sessionid",
      value: sessionId,
      domain: "localhost",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);

  await context.storageState({ path: path.join(authDir, "user.json") });
  await browser.close();
}

async function waitForServer(url: string, timeoutSecs: number) {
  const deadline = Date.now() + timeoutSecs * 1000;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
      if (res.ok || res.status === 302) return;
    } catch {
      // server not ready yet
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error(`Server at ${url} did not become ready within ${timeoutSecs}s`);
}

export default globalSetup;
