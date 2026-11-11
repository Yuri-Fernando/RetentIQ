# Schema diff — modelo versionado × banco real

Ferramenta: [`data-platform/governance/schema_diff.py`](../../data-platform/governance/schema_diff.py).
Compara o snapshot versionado em [`model/`](model/) com o schema extraído de um
banco (SQLite, PostgreSQL ou JSON já extraído).

## Classificação

| Severidade | Mudanças | Efeito no CI |
|---|---|---|
| `breaking` | tabela/coluna/view removida, tipo alterado, NULL→NOT NULL, PK alterada, FK/UNIQUE removida, coluna NOT NULL nova sem default | **exit 1**, a menos que o ID esteja no arquivo de aprovações |
| `review` | FK/UNIQUE nova, NOT NULL→NULL, índice removido | reportado |
| `compatible` | tabela/coluna anulável/índice/view nova | reportado |

Aprovação = lista de IDs (`approved: [...]` em YAML/JSON), revisada no PR. Modela
o "aprovado na homologação" do [change-control.md](change-control.md).

## Onde roda

| Contexto | Comparação |
|---|---|
| `pytest` / CI job `data-platform` | modelo SQLite versionado × warehouse gerado pela fixture (deve ser vazio) |
| CI job `data-model-postgres` | modelo PostgreSQL versionado × DDL aplicado em `postgres:16` (deve ser vazio) |
| Manual | warehouse local do usuário × modelo |

```bash
python data-platform/governance/schema_diff.py \
  --expected docs/data-governance/model/retentiq_sqlite.schema.json \
  --sqlite data-platform/warehouse/retentiq.db --out-md diff.md --out-json diff.json
```

## Resultados registrados

| Data | Comparação | Resultado | Evidência |
|---|---|---|---|
| 2026-11-10 | warehouse v2.1.0 local × modelo v2.2.0 | 13 breaking + 34 review (exit 1) | [baseline-v2.1.0-schema-diff.md](evidence/baseline-v2.1.0-schema-diff.md) |
| 2026-11-10 | modelo SQLite × modelo PostgreSQL | 17 diferenças, todas de tipo (esperadas por dialeto) | [sqlite-vs-postgres-diff.md](evidence/sqlite-vs-postgres-diff.md) |
| 2026-11-10 | warehouse do dado real reconstruído pelo ETL v2.2.0 × modelo | 0 diferenças | testes + carga real |

## Como agir diante de drift

1. **Não corrigir o banco à mão.** Ler o diff e descobrir a origem (deploy fora do
   processo? ETL antigo? alteração manual?).
2. Se a mudança é desejada → abrir CR, atualizar o DDL versionado, regenerar o
   snapshot (`reverse_engineer.py --out-json`) e o dicionário, aprovar no PR.
3. Se não é desejada → restaurar pelo DDL versionado (no warehouse: recarga
   completa; em OLTP: migração reversa) e registrar incidente
   ([sample-incident-ticket.md](sample-incident-ticket.md)).
