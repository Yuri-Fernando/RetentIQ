# Ticket de mudança — exemplo (DCR-2026-014)

> **Artefato de laboratório.** Demonstração de processo, **não** é um ticket real
> de Jira Service Management/ServiceNow nem registro de atuação profissional em
> equipe. Sem capturas de tela de ferramentas.

| Campo | Valor |
|---|---|
| Tipo | Mudança normal (alteração de coluna) |
| Título | Adicionar `primary_country_id` (FK) em `dim_customer` — resolve DT-01 |
| Solicitante (simulado) | Analista de BI |
| Prioridade | Baixa |
| Janela proposta | fora do horário de carga |
| Itens de configuração | `schema_sqlite.sql`, `schema_postgres.sql`, `extract_transform_load.py`, `metadata/columns.yaml`, API (`apps/api/src/routes/metrics.ts` — só se passar a usar o id) |

## Descrição
Hoje `dim_customer.primary_country` é texto livre, sem integridade com
`dim_country`. Relatórios por país do cliente fazem join por texto.

## Estratégia: expand / contract
1. **Expand (v2.3.0):** adicionar `primary_country_id INTEGER REFERENCES dim_country(country_id)` anulável; ETL preenche; `primary_country` mantida.
2. **Migrar consumidores:** API e dashboards passam a usar o id.
3. **Contract (≥ v2.4.0):** remover `primary_country` só depois de `git grep` sem consumidores.

## Análise de risco
| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| País do cliente inexistente em `dim_country` | baixa (países do cliente vêm das mesmas vendas) | carga falha por FK | regra de qualidade + teste com fixture |
| Consumidor externo lendo `primary_country` | média | quebra de relatório | coluna antiga mantida por 1 versão |
| Diff de schema acusa coluna nova | certa | nenhum (compatível) | snapshot regenerado no PR |

## Plano de teste
- `pytest data-platform/tests` (novo teste de FK)
- ETL completo no dado real + `quality/checks.py`
- `schema_diff.py`: só `column_added` (compatible) + `fk_added` (review)

## Rollback
Reverter o commit e recarregar (warehouse reprodutível).

## Status
Proposto — **não implementado** (backlog).
