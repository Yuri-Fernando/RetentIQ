import { Queue } from "bullmq";
import IORedis from "ioredis";

/**
 * Fila assíncrona de e-mails de win-back (idea dev "14 — Sistema de notificações"
 * cruzada com "17 — Sistema de recomendação"): quando um card de Ações de Retenção
 * dispara uma oferta de win-back, o envio real do e-mail não deve bloquear a
 * requisição HTTP — é enfileirado aqui e processado por `winbackWorker.ts`.
 *
 * Conexão via REDIS_URL (.env.example já documenta a variável, reaproveitada do
 * rate limiter). Se o Redis não estiver disponível, a fila fica desabilitada mas
 * a API continua no ar — nunca deixamos infraestrutura opcional derrubar o
 * processo (mesmo princípio já seguido pelo rate limiter em server.ts).
 */
export interface WinbackRecommendation {
  customer_id: string;
  recommended_stock_code: string;
  recommended_description: string;
  score: number;
}

export interface WinbackJobData {
  customerId: number;
  recommendedProducts: WinbackRecommendation[];
}

let winbackQueue: Queue<WinbackJobData> | null = null;

function buildConnection() {
  const url = process.env.REDIS_URL ?? "redis://localhost:6379";
  // maxRetriesPerRequest: null é exigido pelo BullMQ; lazyConnect evita explodir
  // no import caso o Redis esteja fora do ar — o erro só aparece ao usar a fila.
  return new IORedis(url, { maxRetriesPerRequest: null, lazyConnect: true });
}

/**
 * Retorna a Queue singleton, criando-a sob demanda. Nunca lança — se a conexão
 * falhar, loga um aviso e devolve `null`, e quem chamar deve tratar esse caso
 * pulando o enfileiramento (ex.: rota de winback ainda responde 202 ao usuário,
 * só sem confirmar o envio do e-mail).
 */
export function getWinbackQueue(): Queue<WinbackJobData> | null {
  if (winbackQueue) return winbackQueue;

  try {
    const connection = buildConnection();
    winbackQueue = new Queue<WinbackJobData>("winback-emails", { connection });
    return winbackQueue;
  } catch (err) {
    console.warn(
      "[queue] Redis indisponível — fila desabilitada, ver docs/HISTORICO.md",
      err
    );
    return null;
  }
}
