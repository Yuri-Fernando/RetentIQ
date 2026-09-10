'use strict';
/**
 * Testes de integração do messaging contra brokers reais (Kafka + RabbitMQ).
 *
 *   docker compose -f infra/docker/broker-compose.yml up -d
 *   RUN_INTEGRATION=1 node platform/messaging/tests/integration.test.js
 *
 * Pula (exit 0) se `RUN_INTEGRATION` != "1" ou se o broker não responder.
 * Requer `kafkajs` e `amqplib` (ver platform/package.json).
 */
const assert = require('node:assert');
const net = require('node:net');

function portOpen(host, port, timeout = 1500) {
  return new Promise((resolve) => {
    const s = net.createConnection({ host, port });
    const done = (v) => { s.destroy(); resolve(v); };
    s.setTimeout(timeout);
    s.on('connect', () => done(true));
    s.on('timeout', () => done(false));
    s.on('error', () => done(false));
  });
}

(async () => {
  if (process.env.RUN_INTEGRATION !== '1') {
    console.log('skip — RUN_INTEGRATION != 1');
    return;
  }

  const { KafkaBus, RabbitBus } = require('../bus');
  let ran = 0;

  if (await portOpen('localhost', 9092)) {
    const topic = `retentiq.itest.${Date.now()}`;
    const kb = new KafkaBus({ brokers: ['localhost:9092'], clientId: 'itest', groupId: `itest-${Date.now()}` });
    const got = await kb.roundtrip(topic, { hello: 'kafka', id: 1 }, 25000);
    assert.ok(got && got.id === 1, `mensagem Kafka não recebida (got=${JSON.stringify(got)})`);
    console.log('ok — Kafka publish/consume roundtrip');
    ran++;
  } else {
    console.log('skip — Kafka indisponível em localhost:9092');
  }

  if (await portOpen('localhost', 5672)) {
    const queue = `retentiq.itest.${Date.now()}`;
    const rb = new RabbitBus('amqp://guest:guest@localhost:5672');
    await rb.publish(queue, { job: 'report.generate', id: 2 });
    const got = await rb.consumeOnce(queue, 5000);
    assert.ok(got && got.id === 2, `mensagem RabbitMQ não recebida (got=${JSON.stringify(got)})`);
    console.log('ok — RabbitMQ publish/consume roundtrip');
    ran++;
  } else {
    console.log('skip — RabbitMQ indisponível em localhost:5672');
  }

  console.log(`integração: ${ran} roundtrip(s) OK`);
  process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
