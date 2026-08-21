import { Router } from "express";
import { readCsv } from "../lib/csv";

export const forecastRouter = Router();

const CSV_ENV = process.env.DEMAND_FORECAST_CSV_PATH ?? "../../data-platform/warehouse/demand_forecast.csv";

/** Série histórica + previsão de demanda (idea "12 — Previsão de demanda"). */
forecastRouter.get("/demand", (_req, res) => {
  const rows = readCsv(CSV_ENV);
  res.json(rows);
});
