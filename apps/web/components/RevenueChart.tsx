"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Point {
  date: string;
  revenue: number;
  orders: number;
}

export function RevenueChart({ data }: { data: Point[] }) {
  return (
    <div className="h-72 rounded-xl border border-white/10 bg-white/5 p-4">
      <p className="mb-2 text-sm font-medium text-gray-300">Receita diária</p>
      <ResponsiveContainer width="100%" height="90%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.6} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#9ca3af" }} minTickGap={30} />
          <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #ffffff20", fontSize: 12 }}
          />
          <Area type="monotone" dataKey="revenue" stroke="#6366f1" fill="url(#revenueGradient)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
