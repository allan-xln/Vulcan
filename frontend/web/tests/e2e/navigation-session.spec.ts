import { expect, test } from "@playwright/test";

const username = process.env.VULCAN_ADMIN_TEST_USERNAME;
const password = process.env.VULCAN_ADMIN_TEST_PASSWORD;

test("keeps the authenticated Infrastructure subsection after a full reload", async ({ page }) => {
  test.skip(!username || !password, "Production administrator credentials were not provided.");

  await page.goto("/");
  await page.getByPlaceholder("E-mail ou usuário").fill(username!);
  await page.getByPlaceholder("Senha").fill(password!);
  await page.getByRole("button", { name: /Entrar na central/i }).click();

  await page.getByRole("button", { name: "Comando" }).click();
  await page.getByRole("button", { name: /Infrastructure/i }).click();
  await expect(
    page.getByRole("heading", { name: /Infraestrutura explicada pelo impacto/i })
  ).toBeVisible();
  await page.getByRole("button", { name: "Ativos", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Ativos — inventário real" })).toBeVisible();
  await expect(page).toHaveURL(/\/infrastructure\/assets$/);

  await page.reload();

  await expect(page.getByPlaceholder("E-mail ou usuário")).not.toBeVisible();
  await expect(
    page.getByRole("heading", { name: /Infraestrutura explicada pelo impacto/i })
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ativos — inventário real" })).toBeVisible();
  await expect(page).toHaveURL(/\/infrastructure\/assets$/);

  await page.getByRole("button", { name: "Filiais", exact: true }).click();
  await expect(page).toHaveURL(/\/infrastructure\/branches$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/infrastructure\/assets$/);
  await expect(page.getByRole("heading", { name: "Ativos — inventário real" })).toBeVisible();
});
