/**
 * RetentIQ — E2E (idea "30 — Framework de testes automatizados" do repertório
 * dev). Cobre o fluxo crítico: login -> dashboard carrega os KPIs principais.
 *
 * PENDENTE: requer a API rodando em http://localhost:4000 com o warehouse já
 * populado (rode o pipeline em data-platform/ antes) e as credenciais demo
 * definidas em apps/api/.env. Rodar com: npm run test:e2e (dentro de apps/web).
 */
import { expect, test } from "@playwright/test";

test("login com credenciais válidas leva ao dashboard com KPIs", async ({ page }) => {
  await page.goto("/");

  await page.getByPlaceholder("email").fill(process.env.E2E_EMAIL ?? "admin@retentiq.dev");
  await page.getByPlaceholder("senha").fill(process.env.E2E_PASSWORD ?? "");
  await page.getByRole("button", { name: /entrar/i }).click();

  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByText("RetentIQ Dashboard")).toBeVisible();
  await expect(page.getByText("Clientes")).toBeVisible();
  await expect(page.getByText("Receita total")).toBeVisible();
});

test("login com credenciais inválidas mostra erro e não navega", async ({ page }) => {
  await page.goto("/");

  await page.getByPlaceholder("email").fill("errado@retentiq.dev");
  await page.getByPlaceholder("senha").fill("senha-errada");
  await page.getByRole("button", { name: /entrar/i }).click();

  await expect(page.getByText(/credenciais inválidas/i)).toBeVisible();
  await expect(page).toHaveURL("/");
});
