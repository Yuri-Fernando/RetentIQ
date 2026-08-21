import { getDb } from "../lib/db";

/**
 * Funções puras com a lógica de `routes/metrics.ts`, extraídas para serem
 * reaproveitadas tanto pela API REST quanto pelos resolvers GraphQL
 * (idea dev "16 — API GraphQL") — mesma query SQL, duas formas de expor.
 */

export interface OverviewMetrics {
  total_customers: number;
  total_orders: number;
  total_revenue: number;
  avg_line_revenue: number;
  total_cancelled: number;
}

export interface RevenueByCountry {
  country: string;
  revenue: number;
  orders: number;
}

/** Visão geral (idea "1 — Dashboard de métricas SaaS" do repertório dev). */
export function getOverview(): OverviewMetrics {
  const db = getDb();

  const overview = db
    .prepare(
      `SELECT
         COUNT(DISTINCT customer_id) AS total_customers,
         COUNT(DISTINCT invoice)     AS total_orders,
         SUM(revenue)                AS total_revenue,
         AVG(revenue)                AS avg_line_revenue
       FROM fact_sales`
    )
    .get();

  const cancelled = db
    .prepare(`SELECT COUNT(DISTINCT invoice) AS total_cancelled FROM fact_sales_cancelled`)
    .get();

  return { ...(overview as object), ...(cancelled as object) } as OverviewMetrics;
}

/** Receita por país (idea "9 — Análise de campanhas" / segmentação geográfica). */
export function getRevenueByCountry(): RevenueByCountry[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT c.country, SUM(f.revenue) AS revenue, COUNT(DISTINCT f.invoice) AS orders
       FROM fact_sales f
       JOIN dim_country c ON c.country_id = f.country_id
       GROUP BY c.country
       ORDER BY revenue DESC
       LIMIT 20`
    )
    .all() as RevenueByCountry[];
}
