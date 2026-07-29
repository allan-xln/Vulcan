import { expect, test } from "@playwright/test";

const username = process.env.VULCAN_WALLBOARD_TEST_USERNAME;
const password = process.env.VULCAN_WALLBOARD_TEST_PASSWORD;

test("authenticates the read-only Wallboard and renders real operational data", async ({ page }) => {
  test.skip(!username || !password, "Wallboard production credentials were not provided.");

  await page.goto("/wallboard");
  await page.getByLabel("Usuário").fill(username!);
  await page.getByLabel("Senha").fill(password!);
  await page.getByRole("button", { name: "Acessar Wallboard" }).click();

  await expect(page.getByRole("heading", { name: "Inteligência operacional em tempo real" })).toBeVisible();
  await expect(page.getByText("Dados reais", { exact: true })).toBeVisible();
  await expect(page.getByText("Agentes online", { exact: true })).toBeVisible();
  await expect(page.getByText("Saúde da infraestrutura", { exact: true })).toBeVisible();
  await expect(page.getByText(/Última atualização:/)).not.toContainText("aguardando dados");
});
