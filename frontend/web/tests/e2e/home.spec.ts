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
});
