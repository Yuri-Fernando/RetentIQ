'use strict';
/**
 * Demo executável do fluxo event-driven do RetentIQ, sem broker:
 *
 *   order.created ──▶ read model de receita (write side -> read side, CQRS)
 *                 └─▶ re-score de churn ──▶ customer.churn_risk_detected
 *                                        ├─▶ automação de retenção (job RabbitMQ)
 *                                        └─▶ dashboard em tempo real (WebSocket)
 *
 *   node platform/messaging/demo.js
 */
const { InMemoryBus } = require('./bus');

function buildDemo() {
  const events = new InMemoryBus();   // Kafka em prod
  const jobs = new InMemoryBus();     // RabbitMQ em prod
  const state = { revenueByCustomer: {}, retentionJobs: [], dashboardPushes: [] };

  events.subscribe('order.created', (e) => {
    state.revenueByCustomer[e.customer_id] =
      (state.revenueByCustomer[e.customer_id] || 0) + e.amount; // read model
    // re-score de churn (simplificado)
    const score = e.amount < 50 ? 0.82 : 0.30;
    if (score >= 0.7) {
      events.publish('customer.churn_risk_detected', {
        event_id: 'evt-' + e.order_id, occurred_at: new Date().toISOString(),
        customer_id: e.customer_id, score, top_factors: ['low_order_value'],
      });
    }
  });

  events.subscribe('customer.churn_risk_detected', (e) => {
    jobs.publish('retention.outreach', { customer_id: e.customer_id, score: e.score });
    state.dashboardPushes.push({ type: 'churn_risk', customer_id: e.customer_id });
  });

  jobs.subscribe('retention.outreach', (j) => state.retentionJobs.push(j.customer_id));

  return { events, state };
}

if (require.main === module) {
  const { events, state } = buildDemo();
  events.publish('order.created', {
    event_id: 'e1', occurred_at: new Date().toISOString(),
    order_id: 'o1', customer_id: 'CUST-9', amount: 19.9, items: 1,
  });
  console.log('read model receita:', state.revenueByCustomer);
  console.log('jobs de retenção   :', state.retentionJobs);
  console.log('pushes p/ dashboard:', state.dashboardPushes);
}

module.exports = { buildDemo };
