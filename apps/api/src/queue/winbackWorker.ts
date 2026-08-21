import "dotenv/config";
import fs from "node:fs";
import path from "node:path";
import { Worker, type Job } from "bullmq";
import IORedis from "ioredis";
import type { WinbackJobData } from "./winbackQueue";

/**
 * Worker que processa a fila `winback-emails` (ver `winbackQueue.ts`).
 *
 * PENDENTE: plugar um provedor real (ex.: Resend, SendGrid) — ver docs/HISTORICO.md.
 * Por enquanto não existe integração SMTP nenhuma: cada job apenas simula o envio
 * escrevendo uma linha em `apps/api/data/winback_emails.log`, o que já é suficiente
 * para demonstrar o fluxo assíncrono ponta a ponta (rota -> fila -> worker).
 *
 * Roda separado da API via `npm run worker` (ver package.json).
 */
const LOG_PATH = path.resolve(__dirname, "../../data/winback_emails.log");

function ensureLogDir() {
  const dir = path.dirname(LOG_PATH);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

async function processWinbackJob(job: Job<WinbackJobData>) {
  ensureLogDir();
  const { customerId, recommendedProducts } = job.data;
  const productList = recommendedProducts
    .map((p) => p.recommended_description || p.recommended_stock_code)
    .join("; ");
  const line = `[${new Date().toISOString()}] win-back para customer_id=${customerId} — recomendações: ${productList || "(nenhuma)"}\n`;
  fs.appendFileSync(LOG_PATH, line, "utf-8");
  console.log(`[winback-worker] e-mail simulado registrado para customer_id=${customerId}`);
}

const connection = new IORedis(process.env.REDIS_URL ?? "redis://localhost:6379", {
  maxRetriesPerRequest: null,
});

const worker = new Worker<WinbackJobData>("winback-emails", processWinbackJob, { connection });

worker.on("failed", (job, err) => {
  console.error(`[winback-worker] job ${job?.id} falhou:`, err);
});

worker.on("ready", () => {
  console.log("[winback-worker] conectado ao Redis, aguardando jobs de winback-emails...");
});
