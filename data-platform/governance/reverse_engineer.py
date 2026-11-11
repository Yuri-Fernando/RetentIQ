"""
Engenharia reversa do schema do warehouse a partir do CATÁLOGO do banco
(nunca por regex sobre o DDL):

  * SQLite     -> PRAGMA table_xinfo / foreign_key_list / index_list / index_info
  * PostgreSQL -> information_schema.columns + pg_catalog (pg_constraint, pg_index)

Produz um modelo canônico (dict JSON-serializável e ordenado) usado por:
  * schema_diff.py        (modelo versionado x banco real)
  * export_dictionary.py  (dicionário de dados)
  * to_dbml()/to_mermaid() (diagramas importáveis por ferramentas CASE/dbdiagram/dbdocs)

Uso:
    python data-platform/governance/reverse_engineer.py --sqlite data-platform/warehouse/retentiq.db \
        --out-json model.json --out-dbml model.dbml --out-mermaid model.mmd
    python data-platform/governance/reverse_engineer.py --postgres "postgresql://u:p@localhost:5432/db" ...
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

INTERNAL_TABLES_SQLITE = {"sqlite_sequence", "sqlite_stat1", "sqlite_stat4"}


def _canon_type(t: str) -> str:
    t = (t or "").strip().lower()
    aliases = {
        "int4": "integer", "int8": "bigint", "int": "integer", "bool": "boolean",
        "character varying": "varchar", "timestamp without time zone": "timestamp",
        "timestamp with time zone": "timestamptz", "double precision": "double",
    }
    return aliases.get(t, t)


# --------------------------------------------------------------------------- SQLite
def introspect_sqlite(db_path: str | Path) -> dict:
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        model: dict = {"dialect": "sqlite", "tables": {}, "views": {}}
        rows = conn.execute(
            "SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"
        ).fetchall()
        for name, kind, sql in rows:
            if name in INTERNAL_TABLES_SQLITE or name.startswith("sqlite_"):
                continue
            if kind == "view":
                model["views"][name] = {
                    "columns": [r[1] for r in conn.execute(f"PRAGMA table_info('{name}')")],
                }
                continue
            cols = []
            pk_cols = []
            for cid, cname, ctype, notnull, default, pk, hidden in conn.execute(
                f"PRAGMA table_xinfo('{name}')"
            ):
                if hidden:
                    continue
                cols.append({
                    "name": cname,
                    "type": _canon_type(ctype),
                    # PK INTEGER em SQLite é rowid: nunca nula mesmo sem NOT NULL explícito
                    "nullable": not (notnull or pk),
                    "default": default,
                })
                if pk:
                    pk_cols.append((pk, cname))
            fks = []
            for _id, _seq, ref_table, from_col, to_col, *_ in conn.execute(
                f"PRAGMA foreign_key_list('{name}')"
            ):
                fks.append({"columns": [from_col], "ref_table": ref_table, "ref_columns": [to_col]})
            uniques, indexes = [], []
            for _seq, iname, unique, origin, partial in conn.execute(f"PRAGMA index_list('{name}')"):
                icols = [r[2] for r in conn.execute(f"PRAGMA index_info('{iname}')")]
                if origin == "u":
                    uniques.append({"columns": icols})
                elif origin == "c":
                    indexes.append({"name": iname, "columns": icols, "unique": bool(unique),
                                    "partial": bool(partial)})
            checks = _sqlite_checks(sql or "")
            model["tables"][name] = {
                "columns": cols,
                "primary_key": [c for _, c in sorted(pk_cols)],
                "foreign_keys": sorted(fks, key=lambda f: f["columns"]),
                "unique": sorted(uniques, key=lambda u: u["columns"]),
                "indexes": sorted(indexes, key=lambda i: i["name"]),
                "checks": checks,
            }
        return model
    finally:
        conn.close()


def _sqlite_checks(create_sql: str) -> int:
    """SQLite não expõe CHECK no catálogo; contamos ocorrências de CHECK no DDL
    armazenado em sqlite_master (informativo — não usado como fonte de PK/FK)."""
    return create_sql.upper().count("CHECK (") + create_sql.upper().count("CHECK(")


# ----------------------------------------------------------------------- PostgreSQL
def introspect_postgres(dsn: str, schema: str = "public") -> dict:
    import psycopg2  # dependência opcional (só para o modo PostgreSQL)

    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        model: dict = {"dialect": "postgresql", "tables": {}, "views": {}}
        cur.execute(
            """SELECT table_name, table_type FROM information_schema.tables
               WHERE table_schema = %s ORDER BY table_name""", (schema,))
        for tname, ttype in cur.fetchall():
            cur.execute(
                """SELECT column_name, data_type, is_nullable, column_default,
                          numeric_precision, numeric_scale
                   FROM information_schema.columns
                   WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position""",
                (schema, tname))
            cols = []
            for cname, dtype, nullable, default, prec, scale in cur.fetchall():
                t = _canon_type(dtype)
                if t == "numeric" and prec is not None:
                    t = f"numeric({prec},{scale})"
                cols.append({"name": cname, "type": t, "nullable": nullable == "YES",
                             "default": default})
            if ttype == "VIEW":
                model["views"][tname] = {"columns": [c["name"] for c in cols]}
                continue
            model["tables"][tname] = {
                "columns": cols, "primary_key": [], "foreign_keys": [], "unique": [],
                "indexes": [], "checks": 0,
            }
        # constraints via pg_catalog (ordem das colunas preservada por conkey)
        cur.execute(
            """
            SELECT rel.relname, con.contype, con.conname,
                   ARRAY(SELECT att.attname FROM unnest(con.conkey) WITH ORDINALITY k(n, o)
                         JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = k.n
                         ORDER BY k.o) AS cols,
                   frel.relname AS ref_table,
                   ARRAY(SELECT att.attname FROM unnest(con.confkey) WITH ORDINALITY k(n, o)
                         JOIN pg_attribute att ON att.attrelid = con.confrelid AND att.attnum = k.n
                         ORDER BY k.o) AS ref_cols
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace ns ON ns.oid = rel.relnamespace
            LEFT JOIN pg_class frel ON frel.oid = con.confrelid
            WHERE ns.nspname = %s
            ORDER BY rel.relname, con.conname
            """, (schema,))
        for rel, ctype, cname, cols, ref_table, ref_cols in cur.fetchall():
            t = model["tables"].get(rel)
            if t is None:
                continue
            if ctype == "p":
                t["primary_key"] = list(cols)
            elif ctype == "f":
                t["foreign_keys"].append({"columns": list(cols), "ref_table": ref_table,
                                          "ref_columns": list(ref_cols)})
            elif ctype == "u":
                t["unique"].append({"columns": list(cols)})
            elif ctype == "c":
                t["checks"] += 1
        cur.execute(
            """
            SELECT t.relname, i.relname, ix.indisunique, ix.indpred IS NOT NULL,
                   ARRAY(SELECT a.attname FROM unnest(ix.indkey) WITH ORDINALITY k(n, o)
                         JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.n
                         ORDER BY k.o)
            FROM pg_index ix
            JOIN pg_class t ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_namespace ns ON ns.oid = t.relnamespace
            LEFT JOIN pg_constraint c ON c.conindid = ix.indexrelid
            WHERE ns.nspname = %s AND c.oid IS NULL
            ORDER BY t.relname, i.relname
            """, (schema,))
        for rel, iname, unique, partial, cols in cur.fetchall():
            if rel in model["tables"]:
                model["tables"][rel]["indexes"].append(
                    {"name": iname, "columns": list(cols), "unique": bool(unique), "partial": bool(partial)})
        for t in model["tables"].values():
            t["foreign_keys"].sort(key=lambda f: f["columns"])
            t["unique"].sort(key=lambda u: u["columns"])
        return model
    finally:
        conn.close()


# --------------------------------------------------------------------------- saídas
def to_dbml(model: dict, project: str = "retentiq") -> str:
    out = [f"// Gerado por data-platform/governance/reverse_engineer.py a partir do catálogo ({model['dialect']}).",
           "// Não editar à mão: regenerar a partir do banco.",
           f"Project {project} {{ database_type: '{'PostgreSQL' if model['dialect'] == 'postgresql' else 'SQLite'}' }}", ""]
    refs = []
    for tname, t in model["tables"].items():
        out.append(f"Table {tname} {{")
        pk = t["primary_key"]
        for c in t["columns"]:
            attrs = []
            if len(pk) == 1 and c["name"] == pk[0]:
                attrs.append("pk")
            if not c["nullable"] and not (len(pk) == 1 and c["name"] == pk[0]):
                attrs.append("not null")
            if any(u["columns"] == [c["name"]] for u in t["unique"]):
                attrs.append("unique")
            ctype = c["type"].replace(" ", "_") or "text"
            out.append(f"  {c['name']} {ctype}" + (f" [{', '.join(attrs)}]" if attrs else ""))
        idx_lines = []
        if len(pk) > 1:
            idx_lines.append(f"    ({', '.join(pk)}) [pk]")
        for i in t["indexes"]:
            cols = i["columns"][0] if len(i["columns"]) == 1 else f"({', '.join(i['columns'])})"
            opts = [f"name: '{i['name']}'"] + (["unique"] if i["unique"] else [])
            idx_lines.append(f"    {cols} [{', '.join(opts)}]")
        if idx_lines:
            out.append("  indexes {")
            out.extend(idx_lines)
            out.append("  }")
        out.append("}")
        out.append("")
        for fk in t["foreign_keys"]:
            if len(fk["columns"]) == 1:
                refs.append(f"Ref: {tname}.{fk['columns'][0]} > {fk['ref_table']}.{fk['ref_columns'][0]}")
            else:
                refs.append(f"Ref: {tname}.({', '.join(fk['columns'])}) > "
                            f"{fk['ref_table']}.({', '.join(fk['ref_columns'])})")
    out.extend(sorted(refs))
    return "\n".join(out) + "\n"


def to_mermaid(model: dict) -> str:
    out = ["erDiagram"]
    for tname, t in model["tables"].items():
        fk_cols = {c for fk in t["foreign_keys"] for c in fk["columns"]}
        out.append(f"    {tname} {{")
        for c in t["columns"]:
            keys = []
            if c["name"] in t["primary_key"]:
                keys.append("PK")
            if c["name"] in fk_cols:
                keys.append("FK")
            ctype = c["type"].split("(")[0].replace(" ", "_") or "text"
            out.append(f"        {ctype} {c['name']}" + (f" {','.join(keys)}" if keys else ""))
        out.append("    }")
    for tname, t in model["tables"].items():
        for fk in t["foreign_keys"]:
            out.append(f"    {fk['ref_table']} ||--o{{ {tname} : \"{', '.join(fk['columns'])}\"")
    return "\n".join(out) + "\n"


def dump_json(model: dict) -> str:
    return json.dumps(model, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Engenharia reversa do schema (catálogo do banco)")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--sqlite", type=Path)
    src.add_argument("--postgres", help="DSN libpq, ex.: postgresql://user:pass@localhost:5432/db")
    p.add_argument("--out-json", type=Path)
    p.add_argument("--out-dbml", type=Path)
    p.add_argument("--out-mermaid", type=Path)
    args = p.parse_args(argv)

    model = introspect_sqlite(args.sqlite) if args.sqlite else introspect_postgres(args.postgres)
    if args.out_json:
        args.out_json.write_text(dump_json(model), encoding="utf-8")
    if args.out_dbml:
        args.out_dbml.write_text(to_dbml(model), encoding="utf-8")
    if args.out_mermaid:
        args.out_mermaid.write_text(to_mermaid(model), encoding="utf-8")
    if not (args.out_json or args.out_dbml or args.out_mermaid):
        sys.stdout.write(dump_json(model))
    print(f"[reverse] {model['dialect']}: {len(model['tables'])} tabelas, {len(model['views'])} views",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
