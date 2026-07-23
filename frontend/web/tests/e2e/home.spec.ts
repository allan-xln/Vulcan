import { expect, test } from "@playwright/test";

test("logs into the Vulcan command dashboard", async ({ page }) => {
  await page.goto("/");

  await page.getByPlaceholder("E-mail ou usuário").fill("admin");
  await page.getByPlaceholder("Senha").fill("admin");
  await page.getByRole("button", { name: /Entrar na central/i }).click();

  await expect(
    page.getByRole("heading", {
      name: /Transformando operações em inteligência/i
    })
  ).toBeVisible();

  await page.getByRole("button", { name: "Comando" }).click();
  await page.getByRole("button", { name: /Infrastructure/i }).click();
  await expect(page.getByRole("heading", { name: /Infraestrutura explicada pelo impacto/i })).toBeVisible();
  await page.getByRole("button", { name: "Saúde da plataforma" }).click();
  await expect(page.getByText("vulcan-api", { exact: true }).first()).toBeVisible();

  await page.getByRole("button", { name: "Infrastructure" }).click();
  await page.getByRole("button", { name: /^Timeline/ }).click();
  await expect(page.getByRole("heading", { name: /Tudo o que aconteceu/i })).toBeVisible();
});
