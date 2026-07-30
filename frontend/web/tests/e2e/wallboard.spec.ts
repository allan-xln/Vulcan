import { expect, test } from "@playwright/test";

const username = process.env.VULCAN_WALLBOARD_TEST_USERNAME;
const password = process.env.VULCAN_WALLBOARD_TEST_PASSWORD;

test("authenticates the read-only account and renders both real Wallboards", async ({ page }) => {
  test.skip(!username || !password, "Wallboard production credentials were not provided.");

  await page.goto("/wallboard/workforce");
  await page.getByLabel("Usuário").fill(username!);
  await page.getByLabel("Senha").fill(password!);
  await page.getByRole("button", { name: "Acessar painel" }).click();

  await expect(page.getByRole("heading", { name: "Visão geral das equipes" })).toBeVisible();
  await expect(page.getByText("Agentes online", { exact: true })).toBeVisible();
  await expect(page.getByText(/Dados reais · leitura somente/)).toBeVisible();
  await expect(page.getByText(/Atualizado em/)).not.toContainText("aguardando coleta");

  await page.goto("/wallboard/infra");
  await expect(page.getByRole("heading", { name: "Visão geral da infraestrutura" })).toBeVisible();
  await expect(page.getByText("Disponibilidade", { exact: true })).toBeVisible();
  await expect(page.getByText("Integrações somente leitura", { exact: true })).toBeVisible();
  await expect(page.getByText(/Dados reais · leitura somente/)).toBeVisible();

  await page.reload();
  await expect(page.getByLabel("Usuário")).not.toBeVisible();
  await expect(page.getByRole("heading", { name: "Visão geral da infraestrutura" })).toBeVisible();
});
