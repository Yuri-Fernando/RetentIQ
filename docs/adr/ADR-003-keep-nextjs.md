# ADR-003 — Manter Next.js no frontend (não migrar para Angular)

**Status:** Aceito · **Data:** 2026-09

## Contexto

O portfólio tem um projeto (Argus) que demonstra Angular + microfrontends.
Poderia-se padronizar tudo em Angular.

## Decisão

RetentIQ **mantém Next.js**. O objetivo do RetentIQ é demonstrar um
**produto SaaS distribuído event-driven** (Next.js + Node + ML + Kafka +
RabbitMQ + Postgres + Redis + WebSocket), não repetir a stack de front do
Argus. Diversidade de stack entre projetos do portfólio é intencional: cada
um prova um recorte diferente.

## Consequências

- (+) O portfólio cobre Angular (Argus) **e** Next.js (RetentIQ) sem
  retrabalho artificial.
- (−) Dois ecossistemas de front no portfólio (aceito — é amplitude, não
  inconsistência).
