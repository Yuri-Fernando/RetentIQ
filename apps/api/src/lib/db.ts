import Database from "better-sqlite3";
import path from "node:path";
import fs from "node:fs";

const DB_PATH = path.resolve(
  __dirname,
  "../../",
  process.env.WAREHOUSE_DB_PATH ?? "../../data-platform/warehouse/retentiq.db"
);

let db: Database.Database | null = null;

/**
 * Abre (lazy) a conexão com o Data Warehouse SQLite gerado pelo pipeline Python.
 * Se o arquivo ainda não existir, lança um erro explicativo em vez de falhar
 * silenciosamente — o usuário precisa rodar o ETL primeiro (ver README raiz).
 */
export function getDb(): Database.Database {
  if (db) return db;

  if (!fs.existsSync(DB_PATH)) {
    throw new Error(
      `Data Warehouse não encontrado em ${DB_PATH}. ` +
        "Rode primeiro: python data-platform/ingestion/extract_transform_load.py"
    );
  }

  db = new Database(DB_PATH, { readonly: true, fileMustExist: true });
  return db;
}
