# Caso técnico — modelagem e administração de dados no RetentIQ

## Problema

O RetentIQ transforma 1.067.371 linhas do dataset público *Online Retail II* (UCI)
em um warehouse para análise de receita e retenção. Até a v2.1.0, o DDL
PostgreSQL dizia ser "equivalente" ao warehouse SQLite criado pelo ETL. Ao
comparar os catálogos, encontrei **13 diferenças incompatíveis**: o SQLite não
tinha nenhuma PK, FK ou UNIQUE, a view de KPIs não existia e 34 colunas aceitavam
NULL. Além disso, o job de qualidade do CI **pulava** os checks porque o banco não
é versionado, e o ETL imprimia "[OK]" mesmo quando um check falhava.

## Requisito

Ter um modelo de dados documentado nos três níveis, **fisicamente íntegro**,
com metadados que não fiquem defasados, mudanças controladas e qualidade
verificada a cada push, sem quebrar a API, o ETL e os modelos de ML.

## O que foi feito

| Etapa | Resultado medido |
|---|---|
| Modelo conceitual → lógico → físico | entidades e cardinalidades a partir do dado real; grão declarado; chaves natural × substituta justificadas (a origem tem 23.756 grupos `invoice+produto+preço` repetidos, por isso `sale_id` é substituta) |
| Schema físico SQLite explícito | PK/FK/CHECK/UNIQUE/view aplicados pelo ETL com `PRAGMA foreign_keys=ON`; carga real de 793.609 vendas e 18.688 cancelamentos **sem nenhuma violação** |
| Normalização | DFs medidas no arquivo bruto (1.232 de 4.950 produtos com mais de uma descrição = anomalia de atualização real); estrela justificada em ADR |
| Dicionário + glossário | 50 colunas, 100% cobertas, **geradas do catálogo**; teste falha se surgir coluna sem metadado |
| Engenharia reversa + diff | extração via PRAGMA/pg_catalog; diff classificado (compatível/revisão/incompatível) com exit 1 no CI |
| Ferramenta CASE | `@dbml/cli` 3.14.1: import de DDL (achei um bug do parser com `IF NOT EXISTS`), forward engineering aplicado em PostgreSQL 16 com diff vazio, `db2dbml` no banco vivo |
| Controle de mudança | CR-001 (CHECKs `NOT VALID` + `VALIDATE`) com up/down idempotentes testados em PostgreSQL |
| Qualidade | 7 → 30 regras com severidade; reconciliação origem → warehouse fecha exatamente: 1.067.371 = 243.007 + 11.996 + 71 + 793.609 + 18.688 |
| Privacidade e acesso | classificação por coluna; papéis de menor privilégio testados; export com HMAC-SHA256 e k-anonimato |
| Performance | EXPLAIN (ANALYZE, BUFFERS) no dado real: índices cobrindo aceleram consultas seletivas 1,7–2,2× e não ajudam agregações completas; não adotados (custo de +60 MB) |
| Segurança | pip-audit achou CVE no pyarrow (corrigido); Trivy achou containers rodando como root (corrigido) |

## Decisões principais

1. **Manter a estrela** (ADR-004): o warehouse é recriado a cada carga, então as
   anomalias que a 3FN evita não ocorrem; ganha-se um join a menos por consulta.
2. **Sem FK nos cancelamentos**: 129 clientes e 37 produtos reais só aparecem em
   estornos. Preferi preservar o estorno (venda líquida correta) a descartá-lo por
   uma FK, e monitorar com regra de aviso.
3. **Não renomear colunas lidas pela API** (ex.: `primary_country`): dívida
   registrada com plano expand/contract.
4. **Não adotar índices** que só melhoraram consultas de 20–40 ms.

## Achados que eu não esperava

- A API **não usa** a view `vw_customer_kpis`: agrega direto no fato (lógica de KPI
  duplicada — dívida DT-05).
- A comparação de dialetos mostrou que SQLite e PostgreSQL diferem **só em tipos**
  depois da correção (17 colunas: `REAL`↔`NUMERIC` etc.).

## Como validar

`python -m pytest experimentation/tests data-platform/tests` (106 testes Python,
50 deles novos, incluindo 6 contra PostgreSQL de laboratório) e o CI (`data-platform`, `data-model-postgres`,
`security`). Evidências brutas em [`evidence/`](evidence/).

## O que posso e não posso afirmar

| Posso afirmar | Não posso afirmar |
|---|---|
| Modelei um warehouse em três níveis e documentei grão, chaves e medidas | Que tenho 3 anos de experiência profissional em administração de dados — este é um projeto de portfólio |
| Implementei e testei PK/FK/CHECK, DDL/DML, migração com rollback em PostgreSQL | Que homologuei modelos em empresa ou participei de comitê/CAB real |
| Fiz engenharia reversa por catálogo e usei uma ferramenta CASE open source (`@dbml/cli`) | Que usei SAP PowerDesigner, ERwin ou ER/Studio |
| Gerei dicionário, glossário, catálogo e linhagem versionados | Que operei catálogos corporativos (Collibra, Purview, DataHub) |
| Medi planos de execução com EXPLAIN ANALYZE no dado real | Que tenho benchmark representativo de produção |
| Apliquei controles técnicos de privacidade alinhados à LGPD | Que o projeto "está em conformidade com a LGPD" (não há parecer jurídico) |
| Escrevi tickets de mudança/incidente como demonstração de processo | Que atuei com ServiceNow/Jira Service Management ou em squad Scrum real |
