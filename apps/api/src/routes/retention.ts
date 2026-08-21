import { Router } from "express";
import { z } from "zod";

import { getAppDb } from "../lib/appDb";
import { readCsv } from "../lib/csv";
import { getIo } from "../lib/socket";
import { getWinbackQueue } from "../queue/winbackQueue";

/**
 * Módulo "Ações de Retenção" — junta três ideias do repertório de origem:
 *
 * - Kanban estilo Trello (idea dev "8"): cada `retention_actions` é um card
 *   (`todo` -> `in_progress` -> `done`) associado a um cliente.
 * - Editor visual estilo Notion (idea dev "4"): aqui reduzido a notas em blocos
 *   por card (`notes_json`), em vez de um editor de documentos completo — cada
 *   bloco é `{type:'text'|'heading'|'checklist', content, checked?}`.
 * - Funil de retenção (`GET /funnel`): reformulação da idea de dados "7 — funil
 *   de recrutamento", que não faz sentido no domínio deste produto (não é RH).
 *   Em vez de estágios de contratação, rastreamos o funil de retenção real:
 *   cliente identificado como Alto risco -> Contatado (card criado) -> card em
 *   andamento -> Resolvido/Perdido (card concluído).
 *
 * Todas as rotas ficam atrás de `requireAuth` (montado em server.ts, prefixo
 * `/api/retention`).
 */
export const retentionRouter = Router();

const CHURN_CSV_ENV =
  process.env.CHURN_SCORES_CSV_PATH ?? "../../data-platform/warehouse/churn_scores.csv";
const RECOMMENDATIONS_CSV_ENV =
  process.env.CUSTOMER_RECOMMENDATIONS_CSV_PATH ??
  "../../data-platform/warehouse/customer_recommendations.csv";

function nowIso() {
  return new Date().toISOString();
}

interface RetentionActionRow {
  id: number;
  customer_id: number;
  title: string;
  status: string;
  notes_json: string;
  created_at: string;
  updated_at: string;
}

/**
 * `notes_json` é armazenado como string no SQLite (better-sqlite3 não tem tipo
 * JSON nativo). Todo endpoint que devolve uma action pro frontend precisa
 * passar por aqui, senão o cliente recebe uma STRING onde espera um array de
 * blocos (`Block[]`) — o componente `NotionEditor`/`RetentionCardDetail` no
 * frontend assume `notes_json` já parseado, então o parse tem que acontecer
 * de um lado só (aqui, no backend, fonte única da verdade) para não depender
 * de cada tela lembrar de fazer `JSON.parse`.
 */
function serializeAction(row: RetentionActionRow) {
  let notes: unknown = [];
  try {
    notes = JSON.parse(row.notes_json);
  } catch {
    notes = [];
  }
  return { ...row, notes_json: notes };
}

interface CustomerRecommendation {
  customer_id: string;
  recommended_stock_code: string;
  recommended_description: string;
  score: number;
}

/**
 * Lê as recomendações de win-back de um cliente. Devolve [] se o CSV ainda não
 * existir. `readCsv` devolve todas as colunas como string (é um parser de CSV
 * genérico) — aqui convertemos `score` para number, porque o frontend
 * (`RetentionCardDetail.tsx`) chama `r.score.toFixed(2)` esperando um número;
 * deixar essa conversão pro frontend faria mais sentido só se todo consumidor
 * lembrasse de fazer isso — melhor centralizar aqui, igual ao `serializeAction`.
 */
function readRecommendationsFor(customerId: string): CustomerRecommendation[] {
  try {
    const rows = readCsv(RECOMMENDATIONS_CSV_ENV);
    return rows
      .filter((r) => r.customer_id === customerId)
      .map((r) => ({
        customer_id: r.customer_id,
        recommended_stock_code: r.recommended_stock_code,
        recommended_description: r.recommended_description,
        score: Number(r.score) || 0,
      }));
  } catch {
    // idea dev "17 — Sistema de recomendação": o script Python que gera esse CSV
    // pode não ter rodado ainda — não é um erro do card, só ausência de dado.
    return [];
  }
}

// ---------------------------------------------------------------------------
// Kanban — CRUD de cards
// ---------------------------------------------------------------------------

const createActionSchema = z.object({
  customer_id: z.number().int(),
  title: z.string().min(1),
});

const noteBlockSchema = z.object({
  type: z.enum(["text", "heading", "checklist"]),
  content: z.string(),
  checked: z.boolean().optional(),
});

const patchActionSchema = z
  .object({
    status: z.enum(["todo", "in_progress", "done"]).optional(),
    title: z.string().min(1).optional(),
    notes_json: z.array(noteBlockSchema).optional(),
  })
  .refine((data) => Object.keys(data).length > 0, {
    message: "Informe ao menos um campo para atualizar (status, title ou notes_json).",
  });

/** Lista todos os cards do Kanban, opcionalmente filtrando por status. */
retentionRouter.get("/actions", (req, res) => {
  const db = getAppDb();
  const status = req.query.status as string | undefined;

  const rows = (
    status
      ? db.prepare("SELECT * FROM retention_actions WHERE status = ? ORDER BY updated_at DESC").all(status)
      : db.prepare("SELECT * FROM retention_actions ORDER BY updated_at DESC").all()
  ) as RetentionActionRow[];

  res.json(rows.map(serializeAction));
});

/** Cria um novo card, sempre iniciando em `todo`. */
retentionRouter.post("/actions", (req, res) => {
  const parsed = createActionSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: "Payload inválido", details: parsed.error.flatten() });
  }

  const { customer_id, title } = parsed.data;
  const db = getAppDb();
  const timestamp = nowIso();

  const result = db
    .prepare(
      `INSERT INTO retention_actions (customer_id, title, status, notes_json, created_at, updated_at)
       VALUES (?, ?, 'todo', '[]', ?, ?)`
    )
    .run(customer_id, title, timestamp, timestamp);

  const created = db
    .prepare("SELECT * FROM retention_actions WHERE id = ?")
    .get(result.lastInsertRowid) as RetentionActionRow;
  res.status(201).json(serializeAction(created));
});

/** Atualiza status, título e/ou notas em blocos de um card. */
retentionRouter.patch("/actions/:id", (req, res) => {
  const id = Number(req.params.id);
  const parsed = patchActionSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: "Payload inválido", details: parsed.error.flatten() });
  }

  const db = getAppDb();
  const existing = db.prepare("SELECT * FROM retention_actions WHERE id = ?").get(id) as
    | RetentionActionRow
    | undefined;
  if (!existing) {
    return res.status(404).json({ error: "Card não encontrado." });
  }

  const { status, title, notes_json } = parsed.data;
  db.prepare(
    `UPDATE retention_actions
     SET status = COALESCE(?, status),
         title = COALESCE(?, title),
         notes_json = COALESCE(?, notes_json),
         updated_at = ?
     WHERE id = ?`
  ).run(status ?? null, title ?? null, notes_json ? JSON.stringify(notes_json) : null, nowIso(), id);

  const updated = db
    .prepare("SELECT * FROM retention_actions WHERE id = ?")
    .get(id) as RetentionActionRow;
  res.json(serializeAction(updated));
});

/** Remove um card (e não tenta apagar em cascata os comentários — mantidos por histórico). */
retentionRouter.delete("/actions/:id", (req, res) => {
  const id = Number(req.params.id);
  const db = getAppDb();
  const result = db.prepare("DELETE FROM retention_actions WHERE id = ?").run(id);

  if (result.changes === 0) {
    return res.status(404).json({ error: "Card não encontrado." });
  }
  res.status(204).send();
});

// ---------------------------------------------------------------------------
// Chat em tempo real — comentários por card
// ---------------------------------------------------------------------------

const createCommentSchema = z.object({
  author: z.string().min(1),
  message: z.string().min(1),
});

/** Lista comentários de um card, em ordem cronológica. */
retentionRouter.get("/actions/:id/comments", (req, res) => {
  const actionId = Number(req.params.id);
  const db = getAppDb();
  const rows = db
    .prepare("SELECT * FROM retention_comments WHERE action_id = ? ORDER BY created_at ASC")
    .all(actionId);
  res.json(rows);
});

/**
 * Cria um comentário e o transmite em tempo real (Socket.io) para todos os
 * clientes que entraram na sala `retention-action-${id}` via evento
 * `join-action` — é o "chat em tempo real" do card.
 */
retentionRouter.post("/actions/:id/comments", (req, res) => {
  const actionId = Number(req.params.id);
  const parsed = createCommentSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: "Payload inválido", details: parsed.error.flatten() });
  }

  const db = getAppDb();
  const action = db.prepare("SELECT id FROM retention_actions WHERE id = ?").get(actionId);
  if (!action) {
    return res.status(404).json({ error: "Card não encontrado." });
  }

  const { author, message } = parsed.data;
  const timestamp = nowIso();
  const result = db
    .prepare(
      `INSERT INTO retention_comments (action_id, author, message, created_at)
       VALUES (?, ?, ?, ?)`
    )
    .run(actionId, author, message, timestamp);

  const comment = db.prepare("SELECT * FROM retention_comments WHERE id = ?").get(result.lastInsertRowid);

  try {
    getIo().to(`retention-action-${actionId}`).emit("retention-comment", comment);
  } catch (err) {
    // Socket.io não deveria falhar aqui (já está de pé desde o boot do server),
    // mas nunca deixamos um problema de broadcast derrubar a resposta HTTP.
    console.warn("[retention] falha ao emitir retention-comment via Socket.io", err);
  }

  res.status(201).json(comment);
});

// ---------------------------------------------------------------------------
// Funil de retenção
// ---------------------------------------------------------------------------

/**
 * Funil de retenção (reformulação da idea dados "7 — funil de recrutamento"
 * para o domínio do produto): quantos clientes de Alto risco de churn estão em
 * cada estágio — sem ação nenhuma, card criado (`todo`), em andamento
 * (`in_progress`) ou concluído (`done`, que cobre tanto "resolvido" quanto
 * "perdido" — o desfecho fica registrado nas notas do card).
 */
retentionRouter.get("/funnel", (_req, res) => {
  let altoRiscoIds = new Set<string>();
  try {
    const churnRows = readCsv(CHURN_CSV_ENV);
    altoRiscoIds = new Set(
      churnRows.filter((r) => r.risk_segment === "Alto").map((r) => r.customer_id)
    );
  } catch {
    // Scores de churn ainda não gerados — funil fica zerado até o ETL rodar.
  }

  const db = getAppDb();
  const actions = db
    .prepare("SELECT customer_id, status FROM retention_actions")
    .all() as { customer_id: number; status: string }[];

  const statusCount: Record<string, number> = { todo: 0, in_progress: 0, done: 0 };
  const customersComAcao = new Set<string>();

  for (const action of actions) {
    const customerId = String(action.customer_id);
    if (altoRiscoIds.has(customerId)) {
      customersComAcao.add(customerId);
    }
    if (action.status in statusCount) {
      statusCount[action.status] += 1;
    }
  }

  const semAcao = [...altoRiscoIds].filter((id) => !customersComAcao.has(id)).length;

  res.json({
    alto_risco_total: altoRiscoIds.size,
    sem_acao: semAcao,
    todo: statusCount.todo,
    in_progress: statusCount.in_progress,
    done: statusCount.done,
  });
});

// ---------------------------------------------------------------------------
// Recomendações de win-back
// ---------------------------------------------------------------------------

/**
 * Recomendações de produtos para oferta de win-back (idea dev "17 — Sistema de
 * recomendação"). Se o CSV ainda não foi gerado pelo script Python, devolve []
 * em vez de erro 500 — é uma dependência opcional, não uma falha da rota.
 */
retentionRouter.get("/recommendations/:customerId", (req, res) => {
  res.json(readRecommendationsFor(req.params.customerId));
});

// ---------------------------------------------------------------------------
// Win-back assíncrono (fila BullMQ)
// ---------------------------------------------------------------------------

/**
 * Enfileira o envio de um e-mail de win-back para o cliente do card (busca as
 * recomendações do mesmo CSV de `/recommendations/:customerId`). O processamento
 * real acontece em `queue/winbackWorker.ts` — aqui só despachamos o job.
 */
retentionRouter.post("/actions/:id/winback", (req, res) => {
  const id = Number(req.params.id);
  const db = getAppDb();
  const action = db.prepare("SELECT * FROM retention_actions WHERE id = ?").get(id) as
    | { id: number; customer_id: number }
    | undefined;

  if (!action) {
    return res.status(404).json({ error: "Card não encontrado." });
  }

  const recommendedProducts = readRecommendationsFor(String(action.customer_id));
  const queue = getWinbackQueue();

  if (!queue) {
    return res.status(202).json({
      queued: false,
      warning: "Fila indisponível (Redis fora do ar) — e-mail não foi enfileirado. Ver docs/HISTORICO.md.",
    });
  }

  queue
    .add("winback-emails", { customerId: action.customer_id, recommendedProducts })
    .catch((err) => console.warn("[retention] falha ao enfileirar job de winback", err));

  res.status(202).json({ queued: true, customer_id: action.customer_id, recommendations: recommendedProducts.length });
});
