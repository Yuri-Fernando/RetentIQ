import { Router } from "express";
import { getDb } from "../lib/db";
import { getOverview, getRevenueByCountry } from "../services/metricsService";

export const metricsRouter = Router();

/** Visão geral (idea "1 — Dashboard de métricas SaaS" do repertório dev). */
metricsRouter.get("/overview", (_req, res) => {
  res.json(getOverview());
});

/** Receita por país (idea "9 — Análise de campanhas" / segmentação geográfica). */
metricsRouter.get("/revenue-by-country", (_req, res) => {
  res.json(getRevenueByCountry());
});

/** Série temporal de receita diária, para o gráfico principal do dashboard. */
metricsRouter.get("/revenue-timeseries", (_req, res) => {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT d.date, SUM(f.revenue) AS revenue, COUNT(DISTINCT f.invoice) AS orders
       FROM fact_sales f
       JOIN dim_date d ON d.date_id = f.date_id
       GROUP BY d.date
       ORDER BY d.date`
    )
    .all();
  res.json(rows);
});

/** Top produtos por receita (cruza com "17 — Sistema de recomendação"). */
metricsRouter.get("/top-products", (_req, res) => {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT p.stock_code, p.description, SUM(f.revenue) AS revenue, SUM(f.quantity) AS units
       FROM fact_sales f
       JOIN dim_product p ON p.stock_code = f.stock_code
       GROUP BY p.stock_code, p.description
       ORDER BY revenue DESC
       LIMIT 20`
    )
    .all();
  res.json(rows);
});

/** Rentabilidade por cliente (idea "15 — Análise de rentabilidade por cliente"). */
metricsRouter.get("/customer-value", (_req, res) => {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT c.customer_id, c.primary_country,
              COUNT(DISTINCT f.invoice) AS total_orders,
              SUM(f.revenue) AS total_revenue,
              AVG(f.revenue) AS avg_order_revenue,
              MAX(f.invoice_date) AS last_purchase
       FROM fact_sales f
       JOIN dim_customer c ON c.customer_id = f.customer_id
       GROUP BY c.customer_id, c.primary_country
       ORDER BY total_revenue DESC
       LIMIT 50`
    )
    .all();
  res.json(rows);
});
