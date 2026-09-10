'use strict';
/**
 * Abstração de messaging do RetentIQ.
 *
 * - InMemoryBus: entrega síncrona in-process, para dev/teste e para a demo.
 * - KafkaBus (kafkajs): event streaming durável — domain events
 *   (order.created, customer.churn_risk_detected, forecast.updated),
 *   consumidos por múltiplos read models (CQRS — ver docs/adr/ADR-002).
 * - RabbitBus (amqplib): work queue — jobs assíncronos (report.generate,
 *   model.retrain, email.send). Ver docs/adr/ADR-001 (Kafka vs RabbitMQ).
 *
 * kafkajs/amqplib são importados só quando a classe correspondente é
 * instanciada — não são dependência para rodar a InMemoryBus / a demo.
 */

class InMemoryBus {
  constructor() {
    this._handlers = new Map();
    this.log = [];
  }
  publish(topic, message) {
    const payload = JSON.parse(JSON.stringify(message)); // garante serializável
    this.log.push({ topic, payload });
    for (const h of this._handlers.get(topic) || []) h(payload);
  }
  subscribe(topic, handler) {
    if (!this._handlers.has(topic)) this._handlers.set(topic, []);
    this._handlers.get(topic).push(handler);
  }
}

class KafkaBus {
  constructor({ brokers = ['localhost:9092'], clientId = 'retentiq', groupId = 'retentiq' } = {}) {
    const { Kafka } = require('kafkajs'); // dependência externa
    this._kafka = new Kafka({ clientId, brokers });
    this._producer = this._kafka.producer();
    this._groupId = groupId;
    this._connected = false;
  }
  async _ensure() { if (!this._connected) { await this._producer.connect(); this._connected = true; } }
  async publish(topic, message) {
    await this._ensure();
    await this._producer.send({ topic, messages: [{ value: JSON.stringify(message) }] });
  }
  async subscribe(topic, handler) {
    const consumer = this._kafka.consumer({ groupId: this._groupId });
    await consumer.connect();
    await consumer.subscribe({ topic, fromBeginning: true });
    await consumer.run({ eachMessage: async ({ message }) => handler(JSON.parse(message.value.toString())) });
  }

  /** Consumo não-bloqueante: resolve com o primeiro payload do tópico (ou
   *  null após `timeoutMs`). Usado em testes de integração e jobs batch. */
  async consumeOnce(topic, timeoutMs = 10000) {
    const consumer = this._kafka.consumer({ groupId: `${this._groupId}-once-${Date.now()}` });
    await consumer.connect();
    await consumer.subscribe({ topic, fromBeginning: true });
    return new Promise((resolve) => {
      const timer = setTimeout(async () => { await consumer.disconnect(); resolve(null); }, timeoutMs);
      consumer.run({
        eachMessage: async ({ message }) => {
          clearTimeout(timer);
          const value = JSON.parse(message.value.toString());
          await consumer.disconnect();
          resolve(value);
        },
      });
    });
  }

  /** Roundtrip robusto para testes: assina o tópico, espera o consumer
   *  ENTRAR no grupo, só então publica e aguarda a primeira mensagem.
   *  Evita a corrida "publiquei antes do consumer group existir". */
  async roundtrip(topic, message, timeoutMs = 20000) {
    const consumer = this._kafka.consumer({ groupId: `${this._groupId}-rt-${Date.now()}` });
    await consumer.connect();
    await consumer.subscribe({ topic, fromBeginning: true });

    const joined = new Promise((res) => consumer.on(consumer.events.GROUP_JOIN, res));
    const firstMessage = new Promise((resolve) => {
      consumer.run({
        eachMessage: async ({ message: m }) => resolve(JSON.parse(m.value.toString())),
      });
    });

    await joined;
    await this.publish(topic, message);

    const result = await Promise.race([
      firstMessage,
      new Promise((res) => setTimeout(() => res(null), timeoutMs)),
    ]);
    await consumer.disconnect();
    return result;
  }
}

class RabbitBus {
  constructor(url = 'amqp://guest:guest@localhost:5672') {
    this._amqplib = require('amqplib'); // dependência externa
    this._url = url;
  }
  async publish(queue, message) {
    const conn = await this._amqplib.connect(this._url);
    const ch = await conn.createChannel();
    await ch.assertQueue(queue, { durable: true });
    ch.sendToQueue(queue, Buffer.from(JSON.stringify(message)), { persistent: true });
    await ch.close();
    await conn.close();
  }
  async subscribe(queue, handler) {
    const conn = await this._amqplib.connect(this._url);
    const ch = await conn.createChannel();
    await ch.assertQueue(queue, { durable: true });
    ch.prefetch(1);
    ch.consume(queue, (msg) => {
      handler(JSON.parse(msg.content.toString()));
      ch.ack(msg);
    });
  }

  /** Consumo não-bloqueante via polling (`get`). Resolve com o primeiro
   *  payload da fila (ou null após `timeoutMs`). */
  async consumeOnce(queue, timeoutMs = 5000) {
    const conn = await this._amqplib.connect(this._url);
    const ch = await conn.createChannel();
    await ch.assertQueue(queue, { durable: true });
    const deadline = Date.now() + timeoutMs;
    try {
      while (Date.now() < deadline) {
        const msg = await ch.get(queue, { noAck: true });
        if (msg) return JSON.parse(msg.content.toString());
        await new Promise((r) => setTimeout(r, 150));
      }
      return null;
    } finally {
      await conn.close();
    }
  }
}

module.exports = { InMemoryBus, KafkaBus, RabbitBus };
