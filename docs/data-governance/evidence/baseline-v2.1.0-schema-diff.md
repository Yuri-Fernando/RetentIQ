# Baseline v2.1.0 — warehouse gerado pelo ETL antigo x modelo físico v2.2.0

| severidade | id | detalhe | aprovado |
|---|---|---|---|
| breaking | `fk_removed:fact_sales(country_id)->dim_country(country_id)` | fact_sales: FK (country_id)->dim_country(country_id) removida | — |
| breaking | `fk_removed:fact_sales(customer_id)->dim_customer(customer_id)` | fact_sales: FK (customer_id)->dim_customer(customer_id) removida | — |
| breaking | `fk_removed:fact_sales(date_id)->dim_date(date_id)` | fact_sales: FK (date_id)->dim_date(date_id) removida | — |
| breaking | `fk_removed:fact_sales(stock_code)->dim_product(stock_code)` | fact_sales: FK (stock_code)->dim_product(stock_code) removida | — |
| breaking | `pk_changed:dim_country` | dim_country: PK ['country_id'] -> [] | — |
| breaking | `pk_changed:dim_customer` | dim_customer: PK ['customer_id'] -> [] | — |
| breaking | `pk_changed:dim_date` | dim_date: PK ['date_id'] -> [] | — |
| breaking | `pk_changed:dim_product` | dim_product: PK ['stock_code'] -> [] | — |
| breaking | `pk_changed:fact_sales` | fact_sales: PK ['sale_id'] -> [] | — |
| breaking | `pk_changed:fact_sales_cancelled` | fact_sales_cancelled: PK ['cancel_id'] -> [] | — |
| breaking | `table_removed:etl_load_audit` | tabela etl_load_audit não existe no banco | — |
| breaking | `unique_removed:dim_country(country)` | dim_country: UNIQUE ('country',) removida | — |
| breaking | `view_removed:vw_customer_kpis` | view vw_customer_kpis ausente (consumidores da view quebram) | — |
| review | `nullability_relaxed:dim_country.country` | dim_country.country: NOT NULL -> NULL | — |
| review | `nullability_relaxed:dim_country.country_id` | dim_country.country_id: NOT NULL -> NULL | — |
| review | `nullability_relaxed:dim_customer.customer_id` | dim_customer.customer_id: NOT NULL -> NULL | — |
| review | `nullability_relaxed:dim_customer.primary_country` | dim_customer.primary_country: NOT NULL -> NULL | — |
| review | `nullability_relaxed:dim_date.date` | dim_date.date: NOT NULL -> NULL | — |
| review | `nullability_relaxed:dim_date.date_id` | dim_date.date_id: NOT NULL -> NULL | — |
| review | `nullability_relaxed:dim_date.day` | dim_date.day: NOT NULL -> NULL | — |
| review | `nullability_relaxed:dim_date.is_weekend` | dim_date.is_weekend: NOT NULL -> NULL | — |
| review | `nullability_relaxed:dim_date.month` | dim_date.month: NOT NULL -> NULL | — |
| review | `nullability_relaxed:dim_date.weekday` | dim_date.weekday: NOT NULL -> NULL | — |
| review | `nullability_relaxed:dim_date.year` | dim_date.year: NOT NULL -> NULL | — |
| review | `nullability_relaxed:dim_product.description` | dim_product.description: NOT NULL -> NULL | — |
| review | `nullability_relaxed:dim_product.stock_code` | dim_product.stock_code: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales.country_id` | fact_sales.country_id: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales.customer_id` | fact_sales.customer_id: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales.date_id` | fact_sales.date_id: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales.invoice` | fact_sales.invoice: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales.invoice_date` | fact_sales.invoice_date: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales.price` | fact_sales.price: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales.quantity` | fact_sales.quantity: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales.revenue` | fact_sales.revenue: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales.sale_id` | fact_sales.sale_id: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales.stock_code` | fact_sales.stock_code: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales_cancelled.cancel_id` | fact_sales_cancelled.cancel_id: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales_cancelled.customer_id` | fact_sales_cancelled.customer_id: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales_cancelled.date_id` | fact_sales_cancelled.date_id: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales_cancelled.invoice` | fact_sales_cancelled.invoice: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales_cancelled.invoice_date` | fact_sales_cancelled.invoice_date: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales_cancelled.price` | fact_sales_cancelled.price: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales_cancelled.quantity` | fact_sales_cancelled.quantity: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales_cancelled.revenue` | fact_sales_cancelled.revenue: NOT NULL -> NULL | — |
| review | `nullability_relaxed:fact_sales_cancelled.stock_code` | fact_sales_cancelled.stock_code: NOT NULL -> NULL | — |
