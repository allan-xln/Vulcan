import { expect, test } from "@playwright/test";

test("renders the control-plane heading", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", {
      name: /Telemetry control plane for auditable, tenant-isolated operational intelligence/i
    })
  ).toBeVisible();
});

