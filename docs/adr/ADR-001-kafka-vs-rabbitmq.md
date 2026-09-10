# ADR-001 — Kafka para event streaming, RabbitMQ para work queue

**Status:** Aceito · **Data:** 2026-09

## Contexto

RetentIQ evolui de um pipeline batch + API para uma arquitetura
**event-driven**: eventos de negócio (pedido criado, risco de churn
detectado, previsão atualizada) precisam alimentar vários consumidores
(read models, automação de retenção, dashboard em tempo real), e há também
tarefas assíncronas (gerar relatório, retreinar modelo, enviar e-mail).

## Decisão

- **Kafka** — os **domain events**. Log retido, replay, múltiplos consumer
  groups independentes, ordenação por partição (chave = `customer_id`).
- **RabbitMQ** — os **jobs**. Roteamento, ack por mensagem, prefetch, DLQ,
  prioridade. Uma tarefa é feita por um worker, uma vez, com retry.

Regra: fato que interessa a mais de um consumidor ou que precisa de replay
→ Kafka. Tarefa a executar → RabbitMQ.

## Alternativas

- **Só Kafka** — emular work-queue é possível, mas ack por mensagem, DLQ e
  prioridade ficam manuais.
- **Só RabbitMQ** — sem log retido/replay; integração analítica e
  multi-consumidor viram gambiarra.
- **Redis Streams** (já usado em partes) — ótimo para volume moderado e
  baixa operação, mas sem as garantias de retenção/particionamento do Kafka
  para o event backbone.

## Consequências

- (+) Cada padrão com a ferramenta certa; decisão defensável.
- (−) Dois brokers para operar (mitigado: RabbitMQ só para um punhado de
  filas de job).
