import { expect, test } from "@playwright/test";

const username = process.env.VULCAN_WALLBOARD_TEST_USERNAME;
const password = process.env.VULCAN_WALLBOARD_TEST_PASSWORD;
const apiBaseUrl = process.env.VULCAN_E2E_API_URL ?? "/api";

test("authenticates the read-only account and renders both real Wallboards", async ({ page }) => {
  test.skip(!username || !password, "Wallboard production credentials were not provided.");

  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/wallboard/workforce?scene=command");
  await page.getByLabel("Usuário").fill(username!);
  await page.getByLabel("Senha").fill(password!);
  await page.getByRole("button", { name: "Acessar painel" }).click();
  await page.locator("[data-command-center='workforce']").waitFor();
  await page.evaluate(() =>
    window.sessionStorage.setItem("vulcan-wallboard-rotation-paused", "true")
  );
  await page.goto("/wallboard/workforce?scene=command");

  await expect(page.getByRole("heading", { name: "Visão geral das equipes" })).toBeVisible();
  await expect(page.getByText("Pessoas ativas", { exact: true })).toBeVisible();
  await expect(page.getByText("Agentes online", { exact: true })).toBeVisible();
  await expect(page.getByText(/dados reais/i)).toBeVisible();
  await expect(page.getByText("AO VIVO", { exact: true })).toBeVisible();

  await page.goto("/wallboard/infra?scene=command");
  await expect(page.getByRole("heading", { name: "Visão geral da infraestrutura" })).toBeVisible();
  await expect(page.getByText("DISPONIBILIDADE OBSERVADA", { exact: true })).toBeVisible();
  await expect(page.getByText(/Fórmula:/)).toBeVisible();
  await expect(page.getByText(/dados reais/i)).toBeVisible();

  await page.reload();
  await expect(page.getByLabel("Usuário")).not.toBeVisible();
  await expect(page.getByRole("heading", { name: "Visão geral da infraestrutura" })).toBeVisible();

  for (const viewport of [
    { width: 1920, height: 1080 },
    { width: 2560, height: 1440 },
    { width: 3840, height: 2160 }
  ]) {
    await page.setViewportSize(viewport);
    await expect(page.locator("[data-command-center='infrastructure']")).toBeVisible();
    const layout = await page.evaluate(() => ({
      width: window.innerWidth,
      height: window.innerHeight,
      scrollWidth: document.documentElement.scrollWidth,
      scrollHeight: document.documentElement.scrollHeight,
      sceneHeight: Math.round(
        document.querySelector(".command-scene")?.getBoundingClientRect().height ?? 0
      )
    }));
    expect(layout.scrollWidth).toBe(layout.width);
    expect(layout.scrollHeight).toBe(layout.height);
    expect(layout.sceneHeight).toBeGreaterThan(layout.height * 0.7);
  }

  const token = await page.evaluate(() =>
    window.sessionStorage.getItem("vulcan-wallboard-access-token")
  );
  const profiles = await page.request.get(`${apiBaseUrl}/wallboards/profiles`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  expect(profiles.ok()).toBeTruthy();
  const [profile] = (await profiles.json()) as {
    id: string;
    tenantId: string;
    enabled: boolean;
  }[];
  const forbiddenMutation = await page.request.patch(
    `${apiBaseUrl}/wallboards/profiles/${profile.id}`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: { tenantId: profile.tenantId, enabled: profile.enabled }
    }
  );
  expect(forbiddenMutation.status()).toBe(403);
});
