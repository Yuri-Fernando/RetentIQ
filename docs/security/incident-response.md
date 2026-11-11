# Resposta a incidentes de dados — runbook (RetentIQ)

> Estruturado nas fases do NIST SP 800-61 (preparação → detecção/análise →
> contenção/erradicação/recuperação → pós-incidente). Laboratório: os comandos são
> reais; equipes e prazos são exemplos.

## Preparação (o que já existe)

| Recurso | Uso no incidente |
|---|---|
| `quality/checks.py` (exit 1 em falha crítica) + relatório JSON | detecção |
| `schema_diff.py` | detecção de alteração estrutural |
| `etl_load_audit` (hash SHA-256, contagens) | análise: a carga oficial estava íntegra? |
| DDL versionado + ETL reprodutível | recuperação por recarga completa |
| `CR-*.down.sql` testados | rollback de estrutura |

## Playbook A — dado incorreto/adulterado no warehouse

1. **Detectar:** check crítico falha (ex.: `reconciliacao.receita_total`).
2. **Conter:** marcar dashboards como "em revisão"; suspender exports.
3. **Analisar:**
   ```bash
   python data-platform/quality/checks.py --db <warehouse> --report incident.json
   python data-platform/governance/schema_diff.py --expected docs/data-governance/model/retentiq_sqlite.schema.json --sqlite <warehouse>
   sqlite3 <warehouse> "PRAGMA foreign_key_check; SELECT * FROM etl_load_audit;"
   ```
   Se a auditoria fecha e o warehouse não → alteração **após** a carga.
4. **Erradicar/recuperar:** conferir o hash do arquivo de origem e recarregar:
   `python data-platform/ingestion/extract_transform_load.py`.
5. **Pós-incidente:** ticket ([exemplo](../data-governance/sample-incident-ticket.md)), causa raiz, nova regra/teste se a detecção demorou.

## Playbook B — vazamento de dado pessoal (warehouse ou export)

1. **Conter:** revogar o acesso ao local exposto; rotacionar
   `RETENTIQ_PSEUDONYMIZATION_KEY` se um export com tokens vazou junto com a chave.
2. **Avaliar:** quais colunas (dicionário → `classification`), quantos titulares,
   se havia chave HMAC exposta (tokens reversíveis por força bruta no domínio de IDs).
3. **Comunicar:** pela LGPD (art. 48) a comunicação à ANPD e aos titulares é
   devida quando o incidente pode acarretar risco ou dano relevante — decisão do
   controlador com apoio jurídico (fora do escopo técnico deste repositório).
4. **Registrar** tudo (linha do tempo, evidências, decisões).

## Playbook C — segredo commitado

1. Rotacionar o segredo **imediatamente** (remover do Git não basta: o histórico e forks guardam).
2. Remover do código, mover para variável de ambiente/cofre.
3. Reescrita de histórico só com autorização do dono do repositório.
4. Confirmar com `trivy fs --scanners secret .` (mesmo scanner do CI).

## Severidade (exemplo)

| SEV | Critério |
|---|---|
| 1 | vazamento de dado pessoal ou segredo |
| 2 | KPI financeiro errado publicado |
| 3 | violação de integridade detectada antes de publicação |
| 4 | aviso de qualidade (warning) |
