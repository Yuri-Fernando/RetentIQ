'use strict';
/** Testes do read model CQRS — Node assert puro + node:sqlite embutido.
 *  Rodar: node platform/read-models/tests/churn_read_model.test.js
 *  Requer Node >= 22.5 (node:sqlite).
 */
const assert = require('node:assert');
const { ChurnReadModel } = require('../churn_read_model');
const { InMemoryBus } = require('../../messaging/bus');

const EVENTS = [
  ['order.created', { customer_id: 'C1', amount: 100, occurred_at: '2026-09-10T00:00:00Z' }],
  ['customer.churn_risk_detected', { customer_id: 'C1', score: 0.82, occurred_at: '2026-09-10T00:01:00Z' }],
  ['order.created', { customer_id: 'C2', amount: 40, occurred_at: '2026-09-10T00:02:00Z' }],
  ['order.created', { customer_id: 'C1', amount: 60, occurred_at: '2026-09-10T00:03:00Z' }],
  ['customer.churn_risk_detected', { customer_id: 'C1', score: 0.40, occurred_at: '2026-09-10T00:04:00Z' }],
];

// 1. projeção incremental
{
  const rm = new ChurnReadModel();
  for (const [t, p] of EVENTS) {
    (t === 'order.created' ? rm.onOrderCreated(p) : rm.onChurnRiskDetected(p));
  }
  const c1 = rm.customer('C1');
  assert.strictEqual(c1.revenue, 160);
  assert.strictEqual(c1.orders, 2);
  assert.strictEqual(c1.last_score, 0.4);
  assert.strictEqual(c1.high_risk, 0); // último score baixou o risco
  const k = rm.kpis();
  assert.strictEqual(k.total_revenue, 200);
  assert.strictEqual(k.at_risk_customers, 0);
}

// 2. replay == incremental (propriedade central de event-sourcing)
{
  const incremental = new ChurnReadModel();
  for (const [t, p] of EVENTS) {
    (t === 'order.created' ? incremental.onOrderCreated(p) : incremental.onChurnRiskDetected(p));
  }
  const replayed = new ChurnReadModel().rebuildFromEvents(EVENTS);
  assert.deepStrictEqual(replayed.dump(), incremental.dump());
}

// 3. wiring com o bus real (InMemoryBus)
{
  const bus = new InMemoryBus();
  const rm = new ChurnReadModel();
  rm.subscribeTo(bus);
  bus.publish('order.created', { customer_id: 'CX', amount: 250, occurred_at: '2026-09-10T00:00:00Z' });
  bus.publish('customer.churn_risk_detected', { customer_id: 'CX', score: 0.9, occurred_at: '2026-09-10T00:00:00Z' });
  assert.strictEqual(rm.customer('CX').revenue, 250);
  assert.strictEqual(rm.kpis().at_risk_customers, 1);
}

console.log('ok — 3 testes do read model CQRS passaram');
