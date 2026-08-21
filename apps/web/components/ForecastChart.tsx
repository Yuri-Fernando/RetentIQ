"use client";

import { Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface Point {
  date: string;
  revenue_actual?: string;
  revenue_predicted_holdout?: string;
  revenue_forecast_future?: string;
}

export function ForecastChart({ data }: { data: Point[] }) {
  return (
    <div className="h-72 rounded-xl border border-white/10 bg-white/5 p-4">
      <p className="mb-2 text-sm font-medium text-gray-300">
        Previsão de demanda (receita) — próximos 30 dias
      </p>
      <ResponsiveContainer width="100%" height="90%">
        <LineChart data={data}>
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#9ca3af" }} minTickGap={40} />
          <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} />
          <Tooltip contentStyle={{ background: "#111827", border: "1px solid #ffffff20", fontSize: 12 }} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Line type="monotone" dataKey="revenue_actual" name="Realizado" stroke="#6366f1" dot={false} />
          <Line
            type="monotone"
            dataKey="revenue_forecast_future"
            name="Previsão"
            stroke="#f59e0b"
            strokeDasharray="4 4"
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
