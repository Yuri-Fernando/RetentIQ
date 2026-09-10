'use strict';
/** Testes da camada de messaging — Node assert puro, sem dependências.
 *  Rodar: node platform/messaging/tests/bus.test.js
 */
const assert = require('node:assert');
const { InMemoryBus } = require('../bus');
const { buildDemo } = require('../demo');

// 1. InMemoryBus entrega ao assinante
{
  const bus = new InMemoryBus();
  const got = [];
  bus.subscribe('t', (m) => got.push(m));
  bus.publish('t', { a: 1 });
  assert.deepStrictEqual(got, [{ a: 1 }]);
  assert.deepStrictEqual(bus.log, [{ topic: 't', payload: { a: 1 } }]);
}

// 2. múltiplos assinantes no mesmo tópico (fan-out — semântica Kafka)
{
  const bus = new InMemoryBus();
  let n = 0;
  bus.subscribe('x', () => (n += 1));
  bus.subscribe('x', () => (n += 10));
  bus.publish('x', {});
  assert.strictEqual(n, 11);
}

// 3. fluxo da demo: order.created -> churn risk -> job de retenção + push no dashboard
{
  const { events, state } = buildDemo();
  events.publish('order.created', {
    event_id: 'e', occurred_at: new Date().toISOString(),
    order_id: 'o', customer_id: 'C1', amount: 10, items: 1,
  });
  assert.strictEqual(state.revenueByCustomer['C1'], 10);
  assert.deepStrictEqual(state.retentionJobs, ['C1']);
  assert.strictEqual(state.dashboardPushes[0].type, 'churn_risk');
}

// 4. pedido de valor alto não gera evento de risco
{
  const { events, state } = buildDemo();
  events.publish('order.created', {
    event_id: 'e2', occurred_at: new Date().toISOString(),
    order_id: 'o2', customer_id: 'C2', amount: 500, items: 3,
  });
  assert.strictEqual(state.retentionJobs.length, 0);
}

console.log('ok — 4 testes de messaging passaram');
