# Event-Driven Architecture — RetentIQ

```text
                    Write side (pedidos, clientes, catálogo)
                                   │  publica domain events
                                   ▼
                          Kafka (event backbone)
        ┌──────────────────────────┼───────────────────────────┐
        ▼                          ▼                           ▼
  read model receita       read model churn            read model demanda
  (CQRS — ADR-002)          + re-score                  (forecast.updated)
        │                          │                           │
        └────────────┬─────────────┴───────────────┬───────────┘
                     ▼                             ▼
             API de consulta / GraphQL     dashboard tempo real (WebSocket)
                     │
        customer.churn_risk_detected
                     ▼
              RabbitMQ (work queue)
        retention.outreach · report.generate · model.retrain
                     ▼
                Async workers
```

**Tópicos Kafka:** `order.created`, `customer.churn_risk_detected`,
`forecast.updated` (schemas em `platform/messaging/schemas/`).
**Filas RabbitMQ:** `retention.outreach`, `report.generate`, `model.retrain`.

**Garantias:** ordenação por `customer_id` (partição); idempotência do
consumidor por `event_id`; at-least-once + consumidores idempotentes; DLQ
após N tentativas.
