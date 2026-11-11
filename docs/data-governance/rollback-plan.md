# Plano de rollback — mudanças de modelo do RetentIQ

| Situação | Ação | Tempo/risco | Testado? |
|---|---|---|---|
| CR-001 aplicada e rejeitando carga legítima | `CR-001_fact_sales_checks.down.sql` (só remove constraints; não toca em dados) | segundos; lock curto | ✅ `test_cr001_forward_rollback_and_idempotency` |
| Schema SQLite v2.2.0 quebrou algum consumidor | voltar o código à v2.1.0 (`git revert`) e rodar o ETL de novo — o warehouse é recriado do zero | duração de uma carga (8 min 53 s medidos no dado real) | não (não houve necessidade) |
| Carga com dado ruim publicada | rodar o ETL com o arquivo de origem anterior; conferir `etl_load_audit.source_sha256` | duração de uma carga | parcial: reconciliação testada |
| Drift manual detectado em ambiente | recriar a partir do DDL versionado (warehouse) | duração de uma carga | ✅ `test_drift_restoration_by_rebuilding_from_versioned_ddl` |

## Princípios

1. Todo `up.sql` tem um `down.sql` testado **antes** do merge.
2. Rollback de estrutura não apaga dado. Mudanças destrutivas (DROP COLUMN) só na
   fase *contract* de expand/contract, depois que nenhum consumidor lê a coluna.
3. Warehouse analítico é **reprodutível** a partir da origem: o rollback mais
   seguro é recarregar, não editar linhas.
4. Depois do rollback: rodar `quality/checks.py` e `schema_diff.py`, registrar no
   ticket ([sample-incident-ticket.md](sample-incident-ticket.md)).
