-- RetentIQ — consultas analíticas típicas usadas no benchmark
-- (data-platform/governance/benchmark_queries.py). Cada bloco começa com
-- "-- name: <id>". Parâmetro %(customer_id)s é escolhido em tempo de execução
-- (o ID não é registrado no relatório).

-- name: q1_receita_por_mes
SELECT d.year, d.month, SUM(f.revenue) AS receita
FROM fact_sales f
JOIN dim_date d ON d.date_id = f.date_id
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- name: q2_top_clientes
SELECT customer_id, SUM(revenue) AS receita
FROM fact_sales
GROUP BY customer_id
ORDER BY receita DESC
LIMIT 20;

-- name: q3_top_produtos
SELECT p.stock_code, p.description, SUM(f.revenue) AS receita
FROM fact_sales f
JOIN dim_product p ON p.stock_code = f.stock_code
GROUP BY p.stock_code, p.description
ORDER BY receita DESC
LIMIT 20;

-- name: q4_tendencia_cancelamentos
SELECT date_id / 100 AS ano_mes, COUNT(*) AS linhas, SUM(revenue) AS estorno
FROM fact_sales_cancelled
GROUP BY date_id / 100
ORDER BY ano_mes;

-- name: q5_kpi_de_um_cliente
SELECT * FROM vw_customer_kpis WHERE customer_id = %(customer_id)s;

-- name: q6_receita_de_um_mes
SELECT SUM(revenue) AS receita
FROM fact_sales
WHERE date_id BETWEEN 20111101 AND 20111130;
