import { defineConfig, devices } from "@playwright/test";

const port = Number(process.env.FRONTEND_PORT ?? "3000");

export default defineConfig({
  testDir: "./tests/e2e",
  use: {
    baseURL: `http://127.0.0.1:${port}`
  },
  webServer: {
    command: `bash -lc 'set -a; [ -f ../../.env ] && source ../../.env; set +a; corepack pnpm dev --hostname 0.0.0.0 --port ${port}'`,
    port,
    reuseExistingServer: true,
    cwd: __dirname
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
