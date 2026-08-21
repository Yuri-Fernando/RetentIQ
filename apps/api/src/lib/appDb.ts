import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";

/**
 * Banco de estado da aplicação — GRAVÁVEL, separado do Data Warehouse read-only
 * de `lib/db.ts` (aquele é gerado pelo pipeline Python e nunca deve ser escrito
 * pela API). Aqui vivem os dados que a própria API cria: os cards do Kanban de
 * "Ações de Retenção" (idea dev "8 — Kanban estilo Trello") e os comentários do
 * chat em tempo real de cada card.
 *
 * Arquivo: apps/api/data/app_state.db (fora do warehouse, git-ignored — ver
 * .gitignore raiz; a pasta `apps/api/data/` é versionada só com um .gitkeep).
 */
const APP_DB_PATH = path.resolve(__dirname, "../../data/app_state.db");

let db: Database.Database | null = null;

function ensureSchema(database: Database.Database) {
  database.exec(`
    CREATE TABLE IF NOT EXISTS retention_actions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_id INTEGER NOT NULL,
      title TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'todo', -- todo | in_progress | done
      notes_json TEXT NOT NULL DEFAULT '[]', -- array de blocos [{type:'text'|'heading'|'checklist', content, checked?}]
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    -- "action_id" referencia retention_actions(id) por convenção, mas
    -- deliberadamente SEM constraint de FOREIGN KEY: a rota DELETE
    -- /api/retention/actions/:id não apaga comentários em cascata (mantidos
    -- por histórico, ver routes/retention.ts), o que deixaria comentários
    -- órfãos apontando para um card já removido — uma FK de verdade bloquearia
    -- exatamente esse DELETE com "FOREIGN KEY constraint failed" (bug real
    -- encontrado e corrigido nesta sessão, ver docs/HISTORICO.md).
    CREATE TABLE IF NOT EXISTS retention_comments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      action_id INTEGER NOT NULL,
      author TEXT NOT NULL,
      message TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
  `);
}

/**
 * Abre (lazy) a conexão gravável com o banco de estado da aplicação. Cria a
 * pasta `apps/api/data/` e o arquivo do banco automaticamente se ainda não
 * existirem, e garante o schema via CREATE TABLE IF NOT EXISTS.
 */
export function getAppDb(): Database.Database {
  if (db) return db;

  const dir = path.dirname(APP_DB_PATH);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  db = new Database(APP_DB_PATH);
  db.pragma("journal_mode = WAL");
  ensureSchema(db);
  return db;
}
