import "dotenv/config";
import cors from "cors";
import express from "express";
import rateLimit from "express-rate-limit";
import helmet from "helmet";
import { createServer } from "node:http";
import { createYoga } from "graphql-yoga";

import { authRouter } from "./routes/auth";
import { churnRouter } from "./routes/churn";
import { forecastRouter } from "./routes/forecast";
import { metricsRouter } from "./routes/metrics";
import { retentionRouter } from "./routes/retention";
import { requireAuth } from "./middleware/auth";
import { readCsv } from "./lib/csv";
import { createSocketServer } from "./lib/socket";
import { schema } from "./graphql/schema";
import { metricsHandler, metricsMiddleware } from "./lib/metrics";

const app = express();
const httpServer = createServer(app);
const io = createSocketServer(httpServer);

app.use(helmet());
app.use(cors({ origin: process.env.WEB_ORIGIN ?? "http://localhost:3000" }));
app.use(express.json());
app.use(metricsMiddleware);

// idea "19 — Sistema de rate limiting" do repertório dev: protege a API de abuso.
// Usa armazenamento em memória por padrão; ver infra/docker para trocar por Redis.
const limiter = rateLimit({ windowMs: 60_000, limit: 120, standardHeaders: true });
app.use(limiter);

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "retentiq-api", timestamp: new Date().toISOString() });
});

// idea dev "29 — Monitoramento de aplicação": sem requireAuth de propósito — é
// o endpoint que o Prometheus faz scrape (infra/monitoring/prometheus.yml),
// rodando na rede interna do docker-compose, não exposto publicamente na prática.
app.get("/metrics", metricsHandler);

app.use("/auth", authRouter);
app.use("/api/metrics", requireAuth, metricsRouter);
app.use("/api/churn", requireAuth, churnRouter);
app.use("/api/forecast", requireAuth, forecastRouter);
app.use("/api/retention", requireAuth, retentionRouter);

// idea dev "16 — API GraphQL": alternativa de leitura à API REST, protegida
// pelo mesmo middleware JWT. Se a inicialização do Yoga falhar por qualquer
// motivo, isso não pode derrubar o processo inteiro — mesmo princípio já
// seguido pelo rate limiter, que cai para memória se o Redis não estiver lá.
try {
  const yoga = createYoga({ schema, graphqlEndpoint: "/graphql" });
  app.use("/graphql", requireAuth, yoga);
} catch (err) {
  console.warn("[graphql] falha ao inicializar o Yoga — rota /graphql indisponível.", err);
}

app.use((_req, res) => {
  res.status(404).json({ error: "Rota não encontrada." });
});

// Error handler global — sem isso, o Express cai no handler default (página
// HTML com stack trace completo, inclusive caminho absoluto do disco). Bug
// real encontrado nesta sessão testando DELETE /api/retention/actions/:id
// (ver docs/HISTORICO.md): precisa vir depois de todas as rotas, com 4
// parâmetros (é assim que o Express reconhece um error handler).
// eslint-disable-next-line @typescript-eslint/no-unused-vars
app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error("[retentiq-api] erro não tratado:", err);
  res.status(500).json({ error: "Erro interno do servidor." });
});

// idea "14 — Sistema de notificações" (dev) cruzada com "6 — Análise de churn"
// (dados): a cada intervalo, reavalia se existem clientes de Alto risco recém
// carregados e emite um evento em tempo real para quem estiver com o dashboard
// aberto (WebSocket via Socket.io).
const CHURN_ALERT_INTERVAL_MS = 5 * 60_000;
function broadcastChurnAlertsIfAny() {
  try {
    const csvPath = process.env.CHURN_SCORES_CSV_PATH ?? "../../data-platform/warehouse/churn_scores.csv";
    const rows = readCsv(csvPath).filter((r) => r.risk_segment === "Alto");
    if (rows.length > 0) {
      io.emit("churn-alert", {
        high_risk_customers: rows.length,
        generated_at: new Date().toISOString(),
      });
    }
  } catch {
    // warehouse/scores ainda não gerados — silenciosamente ignora até existirem
  }
}
setInterval(broadcastChurnAlertsIfAny, CHURN_ALERT_INTERVAL_MS);

const PORT = Number(process.env.PORT ?? 4000);
httpServer.listen(PORT, () => {
  console.log(`[retentiq-api] rodando em http://localhost:${PORT}`);
});
