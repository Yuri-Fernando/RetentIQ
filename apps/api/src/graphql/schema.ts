import { createSchema } from "graphql-yoga";

import { getOverview, getRevenueByCountry } from "../services/metricsService";
import { getChurnSummary } from "../services/churnService";

/**
 * API GraphQL (idea dev "16 — API GraphQL"): oferece, como alternativa de
 * leitura aos endpoints REST já existentes, os mesmos dados de
 * `GET /api/metrics/overview`, `GET /api/metrics/revenue-by-country` e
 * `GET /api/churn/summary`. Os resolvers reaproveitam as mesmas funções de
 * `services/metricsService.ts` e `services/churnService.ts` usadas pelas
 * rotas REST — nenhuma lógica de consulta é duplicada.
 *
 * Montado em `/graphql` no server.ts, atrás de `requireAuth` (mesmo padrão de
 * autenticação das demais rotas).
 */
const typeDefs = /* GraphQL */ `
  type Overview {
    total_customers: Int!
    total_orders: Int!
    total_revenue: Float
    avg_line_revenue: Float
    total_cancelled: Int!
  }

  type RevenueByCountry {
    country: String!
    revenue: Float
    orders: Int!
  }

  type ChurnSummary {
    total_customers: Int!
    by_segment: ChurnBySegment!
  }

  type ChurnBySegment {
    Alto: Int!
    Medio: Int!
    Baixo: Int!
  }

  type Query {
    overview: Overview!
    revenueByCountry: [RevenueByCountry!]!
    churnSummary: ChurnSummary!
  }
`;

const resolvers = {
  Query: {
    overview: () => getOverview(),
    revenueByCountry: () => getRevenueByCountry(),
    churnSummary: () => {
      const summary = getChurnSummary();
      return {
        total_customers: summary.total_customers,
        // GraphQL não aceita "Médio" como nome de campo (sem acento no schema);
        // o valor em português continua disponível via REST em /api/churn/summary.
        by_segment: {
          Alto: summary.by_segment.Alto ?? 0,
          Medio: summary.by_segment["Médio"] ?? 0,
          Baixo: summary.by_segment.Baixo ?? 0,
        },
      };
    },
  },
};

export const schema = createSchema({ typeDefs, resolvers });
