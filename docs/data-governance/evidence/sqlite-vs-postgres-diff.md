# Diff entre dialetos — modelo SQLite x modelo PostgreSQL

| severidade | id | detalhe | aprovado |
|---|---|---|---|
| breaking | `type_changed:dim_date.date` | dim_date.date: tipo timestamp -> date | — |
| breaking | `type_changed:dim_date.is_weekend` | dim_date.is_weekend: tipo integer -> boolean | — |
| breaking | `type_changed:etl_load_audit.dropped_duplicates` | etl_load_audit.dropped_duplicates: tipo integer -> bigint | — |
| breaking | `type_changed:etl_load_audit.dropped_invalid_sales` | etl_load_audit.dropped_invalid_sales: tipo integer -> bigint | — |
| breaking | `type_changed:etl_load_audit.dropped_missing_customer` | etl_load_audit.dropped_missing_customer: tipo integer -> bigint | — |
| breaking | `type_changed:etl_load_audit.fact_cancelled_rows` | etl_load_audit.fact_cancelled_rows: tipo integer -> bigint | — |
| breaking | `type_changed:etl_load_audit.fact_sales_revenue` | etl_load_audit.fact_sales_revenue: tipo real -> numeric(16,4) | — |
| breaking | `type_changed:etl_load_audit.fact_sales_rows` | etl_load_audit.fact_sales_rows: tipo integer -> bigint | — |
| breaking | `type_changed:etl_load_audit.load_id` | etl_load_audit.load_id: tipo integer -> bigint | — |
| breaking | `type_changed:etl_load_audit.loaded_at_utc` | etl_load_audit.loaded_at_utc: tipo text -> timestamptz | — |
| breaking | `type_changed:etl_load_audit.source_rows` | etl_load_audit.source_rows: tipo integer -> bigint | — |
| breaking | `type_changed:fact_sales.price` | fact_sales.price: tipo real -> numeric(12,4) | — |
| breaking | `type_changed:fact_sales.revenue` | fact_sales.revenue: tipo real -> numeric(14,4) | — |
| breaking | `type_changed:fact_sales.sale_id` | fact_sales.sale_id: tipo integer -> bigint | — |
| breaking | `type_changed:fact_sales_cancelled.cancel_id` | fact_sales_cancelled.cancel_id: tipo integer -> bigint | — |
| breaking | `type_changed:fact_sales_cancelled.price` | fact_sales_cancelled.price: tipo real -> numeric(12,4) | — |
| breaking | `type_changed:fact_sales_cancelled.revenue` | fact_sales_cancelled.revenue: tipo real -> numeric(14,4) | — |
