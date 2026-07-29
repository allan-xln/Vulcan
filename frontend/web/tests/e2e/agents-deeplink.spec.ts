import { expect, test } from "@playwright/test";

const username = process.env.VULCAN_ADMIN_TEST_USERNAME;
const password = process.env.VULCAN_ADMIN_TEST_PASSWORD;

test("opens the Agents view directly after production authentication", async ({ page }) => {
  test.skip(!username || !password, "Production administrator credentials were not provided.");

  await page.goto("/?view=agents");
  await page.getByPlaceholder("E-mail ou usuário").fill(username!);
  await page.getByPlaceholder("Senha").fill(password!);
  await page.getByRole("button", { name: /Entrar na central/i }).click();

  await expect(page.getByRole("heading", { name: "Agentes", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Instalação", exact: true }).click();
  await expect(page.getByText("Instalar Vulcan Agent", { exact: true })).toBeVisible();
});
