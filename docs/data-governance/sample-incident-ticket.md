# Ticket de incidente — exemplo (INC-2026-031)

> **Artefato de laboratório.** O cenário técnico é reproduzido por teste
> automatizado (`test_detects_fk_orphans_when_constraints_bypassed`); o ticket é
> demonstração de processo, não registro real de ferramenta de ITSM.

| Campo | Valor |
|---|---|
| Título | Violação de integridade referencial em `fact_sales` |
| Severidade | SEV-3 (dado analítico incorreto; sem indisponibilidade) |
| Detecção | job de qualidade: `fk.fact_sales_customer_id` e `schema.fk_sem_violacao` **FALHARAM** |
| Ciclo (NIST SP 800-61) | detecção → contenção → erradicação → recuperação → lições |

## Linha do tempo (simulada)
| Hora | Evento |
|---|---|
| T0 | checks retornam exit 1: 1 venda com `customer_id` inexistente em `dim_customer` |
| T0+5 min | **contenção:** dashboard marcado como "dados em revisão"; carga seguinte suspensa |
| T0+20 min | **análise:** `PRAGMA foreign_key_check` aponta a linha; `etl_load_audit` mostra que a última carga oficial fechou a reconciliação → a alteração veio **depois** da carga |
| T0+30 min | causa: script manual executado com `PRAGMA foreign_keys = OFF` alterou o fato direto no arquivo |
| T0+40 min | **erradicação/recuperação:** recarga completa a partir da origem (hash SHA-256 conferido) → checks verdes; `schema_diff.py` sem drift |

## Causa raiz
Escrita fora do pipeline, com verificação de FK desligada. O SQLite só aplica FK
quando a conexão liga `PRAGMA foreign_keys`.

## Ações corretivas
| Ação | Status |
|---|---|
| Checks de FK independentes do PRAGMA (LEFT JOIN) e `foreign_key_check` | implementado |
| API abre o warehouse em modo somente leitura | já existia |
| Documentar que o warehouse só é alterado pelo ETL | implementado (este repositório) |
| Mover leitura de usuários para PostgreSQL com papéis sem DML | planejado |

## Lições
Integridade declarada no schema não basta quando o SGBD permite desligá-la; o
check independente detectou o problema.
