"""
Diff determinístico entre o MODELO FÍSICO VERSIONADO (JSON em
docs/data-governance/model/) e o schema REAL de um banco (engenharia reversa).

Classificação de cada mudança:
  * breaking   -> quebra consumidores ou integridade (remoção de tabela/coluna,
                  mudança de tipo, coluna passa a NOT NULL, remoção de PK/FK,
                  coluna NOT NULL nova sem default)
  * review     -> não quebra leitura, mas exige revisão (nova FK, coluna passa a
                  aceitar NULL, índice removido, view removida)
  * compatible -> aditiva (tabela/coluna anulável nova, índice novo, view nova)

Mudanças "breaking" só passam se o seu ID estiver em um arquivo de aprovações
(YAML/JSON com a chave `approved: [ids]`), o que modela o fluxo de homologação
descrito em docs/data-governance/change-control.md.

Exit code: 0 = sem drift incompatível não aprovado · 1 = drift incompatível · 2 = erro de uso

Uso:
    python data-platform/governance/schema_diff.py \
        --expected docs/data-governance/model/retentiq_sqlite.schema.json \
        --sqlite data-platform/warehouse/retentiq.db --out-md diff.md --out-json diff.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance.reverse_engineer import introspect_postgres, introspect_sqlite  # noqa: E402


@dataclass(frozen=True)
class Change:
    id: str
    kind: str
    severity: str
    detail: str


def _cols(t: dict) -> dict[str, dict]:
    return {c["name"]: c for c in t["columns"]}


def _fk_key(fk: dict) -> str:
    return f"({','.join(fk['columns'])})->{fk['ref_table']}({','.join(fk['ref_columns'])})"


def diff_models(expected: dict, actual: dict) -> list[Change]:
    changes: list[Change] = []

    def add(cid: str, kind: str, severity: str, detail: str) -> None:
        changes.append(Change(cid, kind, severity, detail))

    et, at = expected["tables"], actual["tables"]
    for name in sorted(set(et) - set(at)):
        add(f"table_removed:{name}", "table_removed", "breaking", f"tabela {name} não existe no banco")
    for name in sorted(set(at) - set(et)):
        add(f"table_added:{name}", "table_added", "compatible", f"tabela {name} existe no banco mas não no modelo")

    for name in sorted(set(et) & set(at)):
        e, a = et[name], at[name]
        ec, ac = _cols(e), _cols(a)
        for col in sorted(set(ec) - set(ac)):
            add(f"column_removed:{name}.{col}", "column_removed", "breaking", f"coluna {name}.{col} removida")
        for col in sorted(set(ac) - set(ec)):
            c = ac[col]
            sev = "breaking" if (not c["nullable"] and c.get("default") is None) else "compatible"
            add(f"column_added:{name}.{col}", "column_added", sev,
                f"coluna {name}.{col} ({c['type']}, {'NULL' if c['nullable'] else 'NOT NULL'}) não está no modelo")
        for col in sorted(set(ec) & set(ac)):
            if ec[col]["type"] != ac[col]["type"]:
                add(f"type_changed:{name}.{col}", "type_changed", "breaking",
                    f"{name}.{col}: tipo {ec[col]['type']} -> {ac[col]['type']}")
            if ec[col]["nullable"] != ac[col]["nullable"]:
                if ec[col]["nullable"]:
                    add(f"nullability_tightened:{name}.{col}", "nullability_changed", "breaking",
                        f"{name}.{col}: NULL -> NOT NULL")
                else:
                    add(f"nullability_relaxed:{name}.{col}", "nullability_changed", "review",
                        f"{name}.{col}: NOT NULL -> NULL")
        if e["primary_key"] != a["primary_key"]:
            add(f"pk_changed:{name}", "pk_changed", "breaking",
                f"{name}: PK {e['primary_key']} -> {a['primary_key']}")
        efk = {_fk_key(f) for f in e["foreign_keys"]}
        afk = {_fk_key(f) for f in a["foreign_keys"]}
        for k in sorted(efk - afk):
            add(f"fk_removed:{name}{k}", "fk_removed", "breaking", f"{name}: FK {k} removida")
        for k in sorted(afk - efk):
            add(f"fk_added:{name}{k}", "fk_added", "review", f"{name}: FK {k} nova (pode rejeitar cargas)")
        eu = {tuple(u["columns"]) for u in e["unique"]}
        au = {tuple(u["columns"]) for u in a["unique"]}
        for u in sorted(eu - au):
            add(f"unique_removed:{name}({','.join(u)})", "unique_removed", "breaking", f"{name}: UNIQUE {u} removida")
        for u in sorted(au - eu):
            add(f"unique_added:{name}({','.join(u)})", "unique_added", "review", f"{name}: UNIQUE {u} nova")
        ei = {i["name"] for i in e["indexes"]}
        ai = {i["name"] for i in a["indexes"]}
        for i in sorted(ei - ai):
            add(f"index_removed:{name}.{i}", "index_removed", "review", f"{name}: índice {i} removido (performance)")
        for i in sorted(ai - ei):
            add(f"index_added:{name}.{i}", "index_added", "compatible", f"{name}: índice {i} novo")

    ev, av = set(expected.get("views", {})), set(actual.get("views", {}))
    for v in sorted(ev - av):
        add(f"view_removed:{v}", "view_removed", "breaking", f"view {v} ausente (consumidores da view quebram)")
    for v in sorted(av - ev):
        add(f"view_added:{v}", "view_added", "compatible", f"view {v} nova")
    for v in sorted(ev & av):
        if expected["views"][v]["columns"] != actual["views"][v]["columns"]:
            add(f"view_columns_changed:{v}", "view_columns_changed", "breaking",
                f"view {v}: colunas {expected['views'][v]['columns']} -> {actual['views'][v]['columns']}")
    return changes


def load_approvals(path: Path | None) -> set[str]:
    if not path or not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        import yaml

        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)
    return set(data.get("approved") or [])


def to_markdown(changes: list[Change], approved: set[str], title: str) -> str:
    lines = [f"# {title}", ""]
    if not changes:
        lines.append("Nenhuma diferença entre o modelo versionado e o banco. ✅")
        return "\n".join(lines) + "\n"
    lines += ["| severidade | id | detalhe | aprovado |", "|---|---|---|---|"]
    order = {"breaking": 0, "review": 1, "compatible": 2}
    for c in sorted(changes, key=lambda c: (order[c.severity], c.id)):
        lines.append(f"| {c.severity} | `{c.id}` | {c.detail} | {'sim' if c.id in approved else '—'} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Diff modelo versionado x banco real")
    p.add_argument("--expected", type=Path, required=True)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--sqlite", type=Path)
    src.add_argument("--postgres")
    src.add_argument("--actual-json", type=Path, help="modelo já extraído (JSON)")
    p.add_argument("--approvals", type=Path)
    p.add_argument("--out-md", type=Path)
    p.add_argument("--out-json", type=Path)
    p.add_argument("--title", default="Schema diff — modelo versionado x banco")
    args = p.parse_args(argv)

    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    if args.sqlite:
        actual = introspect_sqlite(args.sqlite)
    elif args.postgres:
        actual = introspect_postgres(args.postgres)
    else:
        actual = json.loads(args.actual_json.read_text(encoding="utf-8"))

    changes = diff_models(expected, actual)
    approved = load_approvals(args.approvals)
    blocking = [c for c in changes if c.severity == "breaking" and c.id not in approved]

    md = to_markdown(changes, approved, args.title)
    if args.out_md:
        args.out_md.write_text(md, encoding="utf-8")
    if args.out_json:
        args.out_json.write_text(json.dumps({
            "changes": [asdict(c) for c in changes],
            "blocking": [c.id for c in blocking],
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.stdout.write(md)
    if blocking:
        print(f"[schema-diff] {len(blocking)} mudança(s) incompatível(is) NÃO aprovada(s).", file=sys.stderr)
        return 1
    print(f"[schema-diff] OK ({len(changes)} diferença(s), nenhuma incompatível não aprovada).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
