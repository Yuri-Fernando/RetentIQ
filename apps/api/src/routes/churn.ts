import { Router } from "express";
import { readCsv } from "../lib/csv";
import { getChurnSummary } from "../services/churnService";

export const churnRouter = Router();

const CSV_ENV = process.env.CHURN_SCORES_CSV_PATH ?? "../../data-platform/warehouse/churn_scores.csv";

/** Lista de clientes com score de risco de churn (idea "6/11" do repertório de dados). */
churnRouter.get("/scores", (req, res) => {
  const segment = req.query.segment as string | undefined; // Alto | Médio | Baixo
  const limit = Number(req.query.limit ?? 100);

  let rows = readCsv(CSV_ENV);
  if (segment) {
    rows = rows.filter((r) => r.risk_segment === segment);
  }
  res.json(rows.slice(0, limit));
});

/** Resumo por segmento de risco, pronto para os cards do dashboard. */
churnRouter.get("/summary", (_req, res) => {
  res.json(getChurnSummary());
});
