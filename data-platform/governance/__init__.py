"""
RetentIQ — governança e modelagem de dados.

Ferramentas determinísticas (stdlib + pandas/PyYAML) usadas por testes e CI:

- fixtures.py           fixture sintética no formato do Online Retail II (sem dados reais)
- reverse_engineer.py   engenharia reversa de schema (SQLite PRAGMA / PostgreSQL catálogo)
- schema_diff.py        diff determinístico modelo versionado x banco (exit != 0 se incompatível)
- export_dictionary.py  dicionário de dados gerado do banco + metadados semânticos versionados
- privacy.py            pseudonimização (HMAC-SHA256) e generalização k-anônima para exports
- benchmark_queries.py  EXPLAIN (ANALYZE, BUFFERS) em PostgreSQL local, antes/depois de índice
"""
