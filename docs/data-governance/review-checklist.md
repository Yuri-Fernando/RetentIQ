# Checklist de revisão de DDL — RetentIQ

Usar em todo PR que altere `schema_*.sql`, `migrations/` ou `metadata/columns.yaml`.

## Modelo e integridade
- [ ] Grão da tabela declarado e inalterado (ou mudança justificada na CR)
- [ ] PK definida; natural × substituta justificada
- [ ] FKs para todas as dimensões referenciadas — ou ausência documentada (ex.: `fact_sales_cancelled`)
- [ ] Nulidade coerente com o modelo lógico; NOT NULL novo tem default ou backfill
- [ ] UNIQUE nas chaves naturais
- [ ] CHECK para domínios (sinais, faixas, prefixos) com nome `ck_<tabela>_<regra>`

## Tipos
- [ ] Valores financeiros em `NUMERIC(p,s)` no PostgreSQL; precisão justificada pelo maior valor real
- [ ] Datas com/sem fuso conforme a origem; nada de data em texto livre
- [ ] Tipos mapeados entre SQLite e PostgreSQL ([physical-model.md](physical-model.md#2-mapeamento-de-tipos))

## Performance
- [ ] Índice para cada FK usada em filtro/join frequente
- [ ] Índice novo medido (antes/depois) — [benchmark](performance-benchmark.md); custo de espaço/escrita registrado
- [ ] Cardinalidade esperada considerada (índice em coluna de 2 valores raramente ajuda)

## Operação e compatibilidade
- [ ] Mudança é aditiva **ou** segue expand/contract
- [ ] Nenhuma coluna lida pela API/ML renomeada (`git grep` nos consumidores)
- [ ] Lock: constraints com `NOT VALID` + `VALIDATE`; `lock_timeout` definido; índices grandes com `CREATE INDEX CONCURRENTLY`
- [ ] Script `up` idempotente; script `down` testado e restaura o snapshot anterior
- [ ] Segregação por tenant: n/a neste warehouse (single-tenant); obrigatória no FleetCam

## Governança e segurança
- [ ] `metadata/columns.yaml` atualizado (descrição, classificação, origem, regra)
- [ ] `export_dictionary.py` rodado; snapshot `model/*.schema.json` regenerado
- [ ] Coluna com dado pessoal classificada; acesso revisado em `roles_postgres.sql`
- [ ] Nenhum dado real/credencial em fixtures, migrações ou exemplos
- [ ] CHANGELOG atualizado
