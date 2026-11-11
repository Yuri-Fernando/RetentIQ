"""
Gera o DICIONÁRIO DE DADOS (docs/data-governance/data-dictionary.csv) a partir de:

  * metadados TÉCNICOS extraídos do catálogo do banco (reverse_engineer.py):
    tipo, nulidade, default, PK, FK, UNIQUE — nunca digitados à mão;
  * tipo PostgreSQL correspondente (modelo versionado retentiq_postgres.schema.json);
  * metadados SEMÂNTICOS versionados em docs/data-governance/metadata/columns.yaml.

Sem --sqlite, constrói um warehouse temporário com a fixture sintética (mesmo
schema físico do ETL), o que torna a geração determinística e executável no CI
sem o dataset real.

Valida cobertura (exit 1 se falhar):
  * toda coluna física tem metadado e vice-versa;
  * classificação válida, descrição/origem/papéis preenchidos;
  * termo de glossário existe em business-glossary.md;
  * regra de qualidade existe em quality-rules.yaml.

Uso:
    python data-platform/governance/export_dictionary.py            # regenera o CSV
    python data-platform/governance/export_dictionary.py --check    # falha se o CSV versionado estiver defasado
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-platform"))

from governance.reverse_engineer import introspect_sqlite  # noqa: E402

GOV = ROOT / "docs" / "data-governance"
METADATA = GOV / "metadata" / "columns.yaml"
PG_MODEL = GOV / "model" / "retentiq_postgres.schema.json"
GLOSSARY = GOV / "business-glossary.md"
QUALITY_RULES = GOV / "quality-rules.yaml"
OUT_CSV = GOV / "data-dictionary.csv"

HEADER = [
    "schema", "table", "column", "object_type", "type_sqlite", "type_postgres", "nullable",
    "default", "is_pk", "fk_reference", "unique", "description", "classification", "source",
    "transformation", "owner_role", "steward_role", "quality_rule", "glossary_term",
]


def build_fixture_model() -> dict:
    """Cria warehouse temporário com a fixture e devolve o modelo do catálogo."""
    sys.path.insert(0, str(ROOT / "data-platform" / "ingestion"))
    from extract_transform_load import build_warehouse  # noqa: E402
    from governance.fixtures import synthetic_raw  # noqa: E402

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "fixture.db"
        build_warehouse(synthetic_raw(), db, "synthetic_fixture(seed=42)", None, None)
        return introspect_sqlite(db)


def glossary_terms(path: Path = GLOSSARY) -> set[str]:
    # termos são cabeçalhos de nível 3: "### Termo"
    return {m.group(1).strip() for m in re.finditer(r"^###\s+(.+)$", path.read_text(encoding="utf-8"), re.M)}


def quality_rule_ids(path: Path = QUALITY_RULES) -> set[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {r["id"] for r in data["rules"]}


def build_rows(model: dict, meta: dict, pg_model: dict | None) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    rows: list[dict] = []
    allowed_cls = set(meta["classifications"])
    roles = set(meta["roles"])
    terms = glossary_terms()
    rules = quality_rule_ids()
    mt = meta["tables"]

    physical: dict[str, tuple[str, list[dict], dict]] = {}
    for tname, t in model["tables"].items():
        physical[tname] = ("table", t["columns"], t)
    for vname, v in model["views"].items():
        physical[vname] = ("view", [{"name": c, "type": "", "nullable": True, "default": None}
                                    for c in v["columns"]], {})

    for name in sorted(set(physical) - set(mt)):
        errors.append(f"objeto físico sem metadado: {name}")
    for name in sorted(set(mt) - set(physical)):
        errors.append(f"metadado sem objeto físico: {name}")

    for name in sorted(set(physical) & set(mt)):
        kind, cols, t = physical[name]
        tmeta = mt[name]
        for r in ("owner_role", "steward_role"):
            if tmeta.get(r) not in roles:
                errors.append(f"{name}: {r} inválido ({tmeta.get(r)})")
        cmeta = tmeta.get("columns", {})
        phys_cols = [c["name"] for c in cols]
        for c in sorted(set(phys_cols) - set(cmeta)):
            errors.append(f"coluna física sem metadado: {name}.{c}")
        for c in sorted(set(cmeta) - set(phys_cols)):
            errors.append(f"metadado sem coluna física: {name}.{c}")
        pg_cols = {}
        if pg_model:
            pg_obj = pg_model["tables"].get(name)
            if pg_obj:
                pg_cols = {c["name"]: c["type"] for c in pg_obj["columns"]}
        fks = {fk["columns"][0]: f"{fk['ref_table']}.{fk['ref_columns'][0]}"
               for fk in t.get("foreign_keys", []) if len(fk["columns"]) == 1}
        uniques = {u["columns"][0] for u in t.get("unique", []) if len(u["columns"]) == 1}
        pk = t.get("primary_key", [])
        for col in cols:
            m = cmeta.get(col["name"])
            if m is None:
                continue
            fq = f"{name}.{col['name']}"
            for field in ("description", "classification", "source", "transformation", "quality_rule", "glossary"):
                if not str(m.get(field) or "").strip():
                    errors.append(f"{fq}: campo '{field}' vazio")
            if m.get("classification") not in allowed_cls:
                errors.append(f"{fq}: classificação inválida {m.get('classification')}")
            if m.get("glossary") and m["glossary"] not in terms:
                errors.append(f"{fq}: termo de glossário inexistente '{m['glossary']}'")
            if m.get("quality_rule") and m["quality_rule"] not in rules:
                errors.append(f"{fq}: regra de qualidade inexistente '{m['quality_rule']}'")
            rows.append({
                "schema": "main",
                "table": name,
                "column": col["name"],
                "object_type": kind,
                "type_sqlite": col["type"],
                "type_postgres": pg_cols.get(col["name"], ""),
                "nullable": "" if kind == "view" else ("YES" if col["nullable"] else "NO"),
                "default": "" if col.get("default") is None else str(col["default"]),
                "is_pk": "YES" if col["name"] in pk else "NO",
                "fk_reference": fks.get(col["name"], ""),
                "unique": "YES" if col["name"] in uniques else "NO",
                "description": m.get("description", ""),
                "classification": m.get("classification", ""),
                "source": m.get("source", ""),
                "transformation": m.get("transformation", ""),
                "owner_role": meta["roles"].get(tmeta.get("owner_role"), ""),
                "steward_role": meta["roles"].get(tmeta.get("steward_role"), ""),
                "quality_rule": m.get("quality_rule", ""),
                "glossary_term": m.get("glossary", ""),
            })
    return rows, errors


def render_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=HEADER, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Gera/valida o dicionário de dados")
    p.add_argument("--sqlite", type=Path, help="warehouse existente (padrão: fixture temporária)")
    p.add_argument("--out", type=Path, default=OUT_CSV)
    p.add_argument("--check", action="store_true", help="não grava; falha se o CSV estiver defasado")
    args = p.parse_args(argv)

    model = introspect_sqlite(args.sqlite) if args.sqlite else build_fixture_model()
    meta = yaml.safe_load(METADATA.read_text(encoding="utf-8"))
    pg_model = json.loads(PG_MODEL.read_text(encoding="utf-8")) if PG_MODEL.exists() else None
    rows, errors = build_rows(model, meta, pg_model)
    if errors:
        print("[dictionary] ERROS de cobertura/consistência:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    content = render_csv(rows)
    if args.check:
        current = args.out.read_text(encoding="utf-8") if args.out.exists() else ""
        if current != content:
            print(f"[dictionary] {args.out} está DEFASADO — rode export_dictionary.py e versione.", file=sys.stderr)
            return 1
        print(f"[dictionary] OK — {len(rows)} colunas, 100% cobertas e atualizadas.", file=sys.stderr)
        return 0
    args.out.write_text(content, encoding="utf-8", newline="\n")
    print(f"[dictionary] {len(rows)} colunas gravadas em {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
