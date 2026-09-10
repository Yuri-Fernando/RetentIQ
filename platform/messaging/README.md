# platform/messaging/

Camada event-driven do RetentIQ.

| Backbone | Uso | Adapter |
|---|---|---|
| **Kafka** (event streaming) | domain events: `order.created`, `customer.churn_risk_detected`, `forecast.updated` — consumidos por múltiplos read models (CQRS) | `KafkaBus` (kafkajs) |
| **RabbitMQ** (work queue) | jobs: `retention.outreach`, `report.generate`, `model.retrain` — semântica de fila com ack/retry/DLQ | `RabbitBus` (amqplib) |
| **InMemoryBus** | dev/teste + `demo.js` | — (sem dependências) |

`schemas/` — JSON Schema por tópico. Ver `docs/adr/ADR-001-kafka-vs-rabbitmq.md`
e `docs/adr/ADR-002-cqrs-read-models.md`.

```bash
node platform/messaging/demo.js
node platform/messaging/tests/bus.test.js
```

> **Status:** ✅ `InMemoryBus` + demo + 4 testes (Node puro). 🚧
> `KafkaBus`/`RabbitBus` implementados; `kafkajs`/`amqplib` não instalados
> no ambiente e sem broker — próximos passos.
