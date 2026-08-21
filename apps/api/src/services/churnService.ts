import { readCsv } from "../lib/csv";

/**
 * Lógica de `routes/churn.ts` extraída em função pura para reaproveitar em
 * GraphQL (idea dev "16 — API GraphQL") sem duplicar a leitura do CSV.
 */

const CSV_ENV = process.env.CHURN_SCORES_CSV_PATH ?? "../../data-platform/warehouse/churn_scores.csv";

export interface ChurnSummary {
  total_customers: number;
  by_segment: Record<string, number>;
}

/** Resumo por segmento de risco, pronto para os cards do dashboard. */
export function getChurnSummary(): ChurnSummary {
  const rows = readCsv(CSV_ENV);
  const summary: Record<string, number> = { Alto: 0, Médio: 0, Baixo: 0 };
  for (const r of rows) {
    if (r.risk_segment in summary) summary[r.risk_segment] += 1;
  }
  return { total_customers: rows.length, by_segment: summary };
}
