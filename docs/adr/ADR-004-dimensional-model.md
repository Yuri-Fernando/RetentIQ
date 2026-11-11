# ADR-004 — Manter esquema estrela para consumo analítico

- **Status:** Aceito
- **Data:** 2026-11-10
- **Contexto do processo:** laboratório de portfólio (decisão do autor; não houve
  comitê de arquitetura real)
- **Relacionados:** [normalization-analysis.md](../data-governance/normalization-analysis.md),
  [logical-model.md](../data-governance/logical-model.md), [ADR-002](ADR-002-cqrs-read-models.md)

## Contexto

A origem (Online Retail II) é uma extração plana, uma linha por item de nota. Um
OLTP equivalente em 3FN teria `pedido`, `item_pedido`, `produto` e `cliente`. O
RetentIQ consome esses dados para **leitura analítica** (receita por período, RFM,
churn, recomendação), com carga **full refresh** e nenhum update linha a linha
entre cargas.

## Decisão

Manter o warehouse como **esquema estrela**: `fact_sales` e `fact_sales_cancelled`
no grão "linha de nota", dimensões `dim_customer`, `dim_product`, `dim_country`,
`dim_date`, `invoice` como dimensão degenerada e a view `vw_customer_kpis` como
camada de consumo declarada. (Verificado no código: a API atual agrega direto em
`fact_sales` em `apps/api/src/routes/metrics.ts` e `services/metricsService.ts`, sem
usar a view — duplicação de lógica registrada como dívida DT-05.)

A partir da v2.2.0, a estrela é **fisicamente íntegra** no SQLite também (PK, FK,
CHECK, UNIQUE, view), e não só no DDL PostgreSQL.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Warehouse em 3FN (espelho do OLTP inferido) | +1 join (pedido) em toda consulta; anomalias que a 3FN evita não ocorrem num warehouse recriado a cada carga |
| Floco de neve (ex.: `dim_product → dim_category`) | a origem não tem hierarquia de produto/geografia; seria inventar entidade |
| Tabela larga única (one big table) | duplicaria descrição de produto e dados de calendário em 793 mil linhas; perde a dimensão como ponto único de verdade |
| View materializada de KPIs | o volume atual (≈ 5,9 mil clientes) não justifica o custo de atualização; a view simples foi medida no benchmark (q5: 9-20 ms no PostgreSQL local) |

## Consequências

- (+) consultas analíticas com no máximo um join por dimensão; medidas aditivas
  claras (`quantity`, `revenue`);
- (+) dimensões como ponto único de verdade para descrição/calendário;
- (−) redundância intencional (`invoice_date` + `date_id`, `primary_country` +
  `country_id`) — mitigada por regras de qualidade de coerência;
- (−) sem histórico de atributos (SCD tipo 1 por recarga). SCD tipo 2 está no
  backlog, sem data;
- (−) cancelamentos ficam em fato separado sem FK — venda líquida exige união dos
  dois fatos (regra no glossário).
