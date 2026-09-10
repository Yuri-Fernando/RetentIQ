'use strict';
/**
 * Read model CQRS do RetentIQ (ADR-002).
 *
 * O lado de escrita publica domain events (`order.created`,
 * `customer.churn_risk_detected`); este consumidor os projeta em tabelas
 * desnormalizadas prontas para o dashboard, usando o SQLite embutido do
 * Node (`node:sqlite`, sem dependência externa):
 *
 *   - customer_360(customer_id, revenue, orders, last_score, high_risk, last_seen)
 *   - kpis(key, value)  — total_revenue, at_risk_customers, avg_score
 *
 * Propriedade central de CQRS/event-sourcing: o read model é reconstruível
 * por replay do log — `rebuildFromEvents()` produz exatamente o mesmo
 * estado que o consumo incremental.
 */
const { DatabaseSync } = require('node:sqlite');

const SCHEMA = `
CREATE TABLE IF NOT EXISTS customer_360 (
  customer_id TEXT PRIMARY KEY,
  revenue     REAL DEFAULT 0,
  orders      INTEGER DEFAULT 0,
  last_score  REAL,
  high_risk   INTEGER DEFAULT 0,
  last_seen   TEXT
);
CREATE TABLE IF NOT EXISTS kpis (key TEXT PRIMARY KEY, value REAL);
`;

class ChurnReadModel {
  constructor(path = ':memory:') {
    this.db = new DatabaseSync(path);
    this.db.exec(SCHEMA);
  }

  // --- projeções (um handler por tipo de evento) ------------------------

  onOrderCreated(e) {
    this.db.prepare(`
      INSERT INTO customer_360 (customer_id, revenue, orders, last_seen)
      VALUES (:cid, :amount, 1, :ts)
      ON CONFLICT(customer_id) DO UPDATE SET
        revenue = customer_360.revenue + :amount,
        orders  = customer_360.orders + 1,
        last_seen = :ts
    `).run({ cid: e.customer_id, amount: e.amount, ts: e.occurred_at });
    this._recomputeKpis();
  }

  onChurnRiskDetected(e) {
    const high = e.score >= 0.7 ? 1 : 0;
    this.db.prepare(`
      INSERT INTO customer_360 (customer_id, last_score, high_risk, last_seen)
      VALUES (:cid, :score, :high, :ts)
      ON CONFLICT(customer_id) DO UPDATE SET
        last_score = :score, high_risk = :high, last_seen = :ts
    `).run({ cid: e.customer_id, score: e.score, high, ts: e.occurred_at });
    this._recomputeKpis();
  }

  _recomputeKpis() {
    const r = this.db.prepare(`
      SELECT COALESCE(SUM(revenue),0) rev,
             COALESCE(SUM(high_risk),0) hr,
             COALESCE(AVG(last_score),0) avg_s
      FROM customer_360
    `).get();
    const put = this.db.prepare(
      'INSERT INTO kpis (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value',
    );
    put.run('total_revenue', Number(r.rev.toFixed(2)));
    put.run('at_risk_customers', r.hr);
    put.run('avg_score', Number(r.avg_s.toFixed(4)));
  }

  // --- API de leitura (o dashboard consome isto) -----------------------

  customer(id) {
    return this.db.prepare('SELECT * FROM customer_360 WHERE customer_id = ?').get(id) || null;
  }

  kpis() {
    return Object.fromEntries(this.db.prepare('SELECT key, value FROM kpis').all().map((r) => [r.key, r.value]));
  }

  dump() {
    return {
      customer_360: this.db.prepare('SELECT * FROM customer_360 ORDER BY customer_id').all(),
      kpis: this.kpis(),
    };
  }

  // --- wiring + replay ------------------------------------------------

  subscribeTo(bus) {
    bus.subscribe('order.created', (e) => this.onOrderCreated(e));
    bus.subscribe('customer.churn_risk_detected', (e) => this.onChurnRiskDetected(e));
  }

  /** Replay: `[[topic, payload], ...]` na ordem do log. */
  rebuildFromEvents(events) {
    for (const [topic, payload] of events) {
      if (topic === 'order.created') this.onOrderCreated(payload);
      else if (topic === 'customer.churn_risk_detected') this.onChurnRiskDetected(payload);
    }
    return this;
  }
}

module.exports = { ChurnReadModel };
