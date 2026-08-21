"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { io } from "socket.io-client";
import Link from "next/link";
import { API_URL, apiFetch, clearToken } from "../../lib/api";
import { KpiCard } from "../../components/KpiCard";
import { RevenueChart } from "../../components/RevenueChart";
import { ChurnPanel } from "../../components/ChurnPanel";
import { ForecastChart } from "../../components/ForecastChart";

const fetcher = <T,>(path: string) => apiFetch<T>(path);
const currency = (n: number) =>
  n?.toLocaleString("pt-BR", { style: "currency", currency: "GBP" }) ?? "-";

interface OverviewMetrics {
  total_customers: number;
  total_orders: number;
  total_revenue: number;
  avg_line_revenue: number;
  total_cancelled: number;
}

interface RevenuePoint {
  date: string;
  revenue: number;
  orders: number;
}

interface ChurnSummary {
  total_customers: number;
  by_segment: { Alto: number; Médio: number; Baixo: number };
}

interface ForecastPoint {
  date: string;
  revenue_actual?: string;
  revenue_predicted_holdout?: string;
  revenue_forecast_future?: string;
}

interface TopProduct {
  stock_code: string;
  description: string;
  revenue: number;
  units: number;
}

export default function DashboardPage() {
  const { data: overview } = useSWR<OverviewMetrics>("/api/metrics/overview", fetcher);
  const { data: timeseries } = useSWR<RevenuePoint[]>("/api/metrics/revenue-timeseries", fetcher);
  const { data: churnSummary } = useSWR<ChurnSummary>("/api/churn/summary", fetcher);
  const { data: forecast } = useSWR<ForecastPoint[]>("/api/forecast/demand", fetcher);
  const { data: topProducts } = useSWR<TopProduct[]>("/api/metrics/top-products", fetcher);

  const [alert, setAlert] = useState<string | null>(null);

  useEffect(() => {
    // idea "14 — Sistema de notificações" (dev): recebe alertas em tempo real
    // quando o backend detecta clientes de Alto risco de churn.
    const socket = io(API_URL);
    socket.on("churn-alert", (payload: { high_risk_customers: number }) => {
      setAlert(`⚠ ${payload.high_risk_customers} clientes em Alto risco de churn.`);
    });
    return () => {
      socket.disconnect();
    };
  }, []);

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">RetentIQ Dashboard</h1>
          <p className="text-sm text-gray-400">
            Receita, churn e previsão de demanda — dataset Online Retail II.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/dashboard/retention"
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-gray-300 hover:bg-white/10"
          >
            Ações de Retenção →
          </Link>
          <button
            onClick={() => {
              clearToken();
              window.location.href = "/";
            }}
            className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-gray-300 hover:bg-white/5"
          >
            Sair
          </button>
        </div>
      </div>

      {alert && (
        <div className="mb-6 rounded-lg border border-risk-alto/40 bg-risk-alto/10 px-4 py-2 text-sm text-red-300">
          {alert}
        </div>
      )}

      <section className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard label="Clientes" value={overview ? String(overview.total_customers) : "..."} />
        <KpiCard label="Pedidos" value={overview ? String(overview.total_orders) : "..."} />
        <KpiCard
          label="Receita total"
          value={overview ? currency(overview.total_revenue) : "..."}
        />
        <KpiCard
          label="Pedidos cancelados"
          value={overview ? String(overview.total_cancelled) : "..."}
        />
      </section>

      <section className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {timeseries && <RevenueChart data={timeseries} />}
        </div>
        <div>{churnSummary && <ChurnPanel summary={churnSummary} />}</div>
      </section>

      <section className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">{forecast && <ForecastChart data={forecast} />}</div>
        <div className="rounded-xl border border-white/10 bg-white/5 p-4">
          <p className="mb-2 text-sm font-medium text-gray-300">Top produtos por receita</p>
          <div className="max-h-56 space-y-1 overflow-y-auto text-xs">
            {topProducts?.slice(0, 10).map((p) => (
              <div key={p.stock_code} className="flex justify-between border-b border-white/5 py-1">
                <span className="truncate pr-2 text-gray-300">{p.description}</span>
                <span className="shrink-0 text-gray-400">{currency(p.revenue)}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
