# Política de retenção — exemplo (laboratório de portfólio)

> Exemplo de política aplicável a este projeto. Prazos são **propostos pelo autor**
> para o contexto de estudo, não derivados de obrigação legal de uma empresa.

| Ativo | Retenção | Descarte | Justificativa |
|---|---|---|---|
| `online_retail_II.xlsx` (bruto) | enquanto o projeto estiver ativo | apagar arquivo local | necessário para reprocessar; disponível publicamente na UCI (recuperável) |
| `retentiq.db` (warehouse local) | até a próxima carga (substituído a cada execução) | sobrescrito pelo ETL | derivado e reprodutível |
| `datasets/processed/*.parquet` | até a próxima carga | sobrescrito | derivado |
| `etl_load_audit` | junto com o warehouse (recriado a cada carga completa) | idem | ver limitação abaixo |
| Exports pseudonimizados de KPIs | 90 dias após a geração | apagar arquivo; rotacionar a chave HMAC invalida joins com exports antigos | minimização no tempo |
| Chave `RETENTIQ_PSEUDONYMIZATION_KEY` | rotação a cada 12 meses ou após suspeita de vazamento | substituir no cofre | limita reidentificação por chave antiga |
| Fixtures sintéticas | indefinida (versionadas) | — | não contêm dado pessoal |

## Limitação conhecida

A carga é full refresh: o `DROP TABLE` do DDL apaga o histórico de
`etl_load_audit` a cada execução (fica só a carga atual). Uma trilha de auditoria
de longo prazo exigiria tabela fora do ciclo de recriação — registrado no backlog.

## Verificação

Nenhum job automático de expurgo existe: a política acima é documental. Item de
backlog: script que lista exports mais antigos que 90 dias.
