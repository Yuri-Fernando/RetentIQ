/**
 * RetentIQ — E2E do módulo de Ações de Retenção (idea "30 — Framework de
 * testes automatizados" do repertório dev, agora cobrindo o Kanban criado no
 * v2.0.0 do projeto, além do login já coberto em login-e-dashboard.spec.ts).
 *
 * PENDENTE: requer a API rodando com o warehouse populado e credenciais demo
 * definidas em apps/api/.env (mesmo pré-requisito do outro spec E2E).
 */
import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.getByPlaceholder("email").fill(process.env.E2E_EMAIL ?? "admin@retentiq.dev");
  await page.getByPlaceholder("senha").fill(process.env.E2E_PASSWORD ?? "");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page).toHaveURL(/\/dashboard/);
});

test("navega até o Kanban de retenção e cria um card novo", async ({ page }) => {
  await page.getByRole("link", { name: /ações de retenção/i }).click();
  await expect(page).toHaveURL(/\/dashboard\/retention/);
  await expect(page.getByText("Ações de Retenção")).toBeVisible();

  await page.getByRole("button", { name: /\+ nova ação/i }).click();
  await page.getByLabel("Customer ID").fill("99999");
  await page.getByLabel("Título da ação").fill("Card criado pelo teste E2E");
  await page.getByRole("button", { name: "Criar" }).click();

  await expect(page.getByText("Card criado pelo teste E2E")).toBeVisible();
});

test("busca filtra os cards do board", async ({ page }) => {
  await page.getByRole("link", { name: /ações de retenção/i }).click();
  await expect(page).toHaveURL(/\/dashboard\/retention/);

  await page.getByPlaceholder(/buscar por cliente ou título/i).fill("termo-que-nao-deve-existir-em-nenhum-card");
  await expect(page.getByText("Nenhum card nesta coluna.")).toHaveCount(3);
});
