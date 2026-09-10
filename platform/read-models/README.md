# platform/read-models/ (CQRS — ADR-002)

Projeções de leitura materializadas a partir de domain events, usando o
**SQLite embutido do Node** (`node:sqlite`, sem dependência externa — requer
Node ≥ 22.5).

`ChurnReadModel` consome `order.created` e `customer.churn_risk_detected` e
materializa:

- `customer_360(customer_id, revenue, orders, last_score, high_risk, last_seen)`
- `kpis(key, value)` — `total_revenue`, `at_risk_customers`, `avg_score`

**Propriedade central:** reconstruível por replay do log —
`rebuildFromEvents()` produz o mesmo estado que o consumo incremental
(testado em `tests/churn_read_model.test.js`).

```js
const { ChurnReadModel } = require('./churn_read_model');
const rm = new ChurnReadModel('cqrs.db');
rm.subscribeTo(bus);                        // consumo incremental
const rm2 = new ChurnReadModel().rebuildFromEvents(eventLog);  // replay
```

```bash
node platform/read-models/tests/churn_read_model.test.js
```
