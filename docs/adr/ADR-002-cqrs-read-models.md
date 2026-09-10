# ADR-002 — CQRS: read models materializados a partir de eventos

**Status:** Aceito · **Data:** 2026-09

## Contexto

O dashboard precisa de agregações (receita por cliente, KPIs de churn,
planejamento de demanda) com leitura rápida. Calcular isso on-the-fly a
partir das tabelas transacionais a cada request não escala e acopla a
leitura à modelagem de escrita.

## Decisão

**CQRS**: o lado de escrita (pedidos, clientes) publica domain events em
Kafka; **read models** dedicados (tabelas desnormalizadas / views
materializadas) são atualizados por consumidores desses eventos e servem o
dashboard e a API de consulta. O read model pode ser reconstruído por
replay do tópico.

Escopo: só para as três agregações caras (receita, churn, demanda). CRUD
simples continua leitura direta — CQRS não é aplicado em tudo.

## Consequências

- (+) Leitura rápida e desacoplada; read models reconstruíveis; novas views
  = novo consumidor, sem tocar no lado de escrita.
- (−) Consistência eventual entre escrita e read model (janela < 2s); a UI
  mostra "atualizando" quando aplicável.
