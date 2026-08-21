import client from "prom-client";
import type { NextFunction, Request, Response } from "express";

/**
 * Métricas Prometheus (idea dev "29 — Monitoramento de aplicação"): fecha a
 * ponta que `infra/monitoring/prometheus.yml` já esperava desde a v1 do
 * projeto (o scrape target `api:4000` existia, mas o endpoint `/metrics`
 * ainda não tinha sido implementado — pendência registrada em
 * docs/HISTORICO.md, resolvida aqui).
 */

const registry = new client.Registry();
client.collectDefaultMetrics({ register: registry });

const httpRequestDuration = new client.Histogram({
  name: "retentiq_http_request_duration_seconds",
  help: "Duração das requisições HTTP da API RetentIQ, em segundos.",
  labelNames: ["method", "route", "status_code"],
  buckets: [0.01, 0.05, 0.1, 0.3, 0.5, 1, 2, 5],
  registers: [registry],
});

const httpRequestsTotal = new client.Counter({
  name: "retentiq_http_requests_total",
  help: "Total de requisições HTTP recebidas pela API RetentIQ.",
  labelNames: ["method", "route", "status_code"],
  registers: [registry],
});

/** Middleware Express: mede duração e conta cada requisição por rota/método/status. */
export function metricsMiddleware(req: Request, res: Response, next: NextFunction) {
  const end = httpRequestDuration.startTimer();
  res.on("finish", () => {
    // req.route só existe depois do roteamento — usa req.path como fallback
    // pra não perder a métrica de rotas 404.
    const route = req.route?.path ?? req.path;
    const labels = { method: req.method, route, status_code: String(res.statusCode) };
    end(labels);
    httpRequestsTotal.inc(labels);
  });
  next();
}

/** Handler da rota GET /metrics — formato texto que o Prometheus sabe fazer scrape. */
export async function metricsHandler(_req: Request, res: Response) {
  res.set("Content-Type", registry.contentType);
  res.end(await registry.metrics());
}
