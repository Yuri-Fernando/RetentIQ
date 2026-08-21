"use client";

interface ChurnSummary {
  total_customers: number;
  by_segment: { Alto: number; Médio: number; Baixo: number };
}

const SEGMENT_COLOR: Record<string, string> = {
  Alto: "bg-risk-alto",
  Médio: "bg-risk-medio",
  Baixo: "bg-risk-baixo",
};

export function ChurnPanel({ summary }: { summary: ChurnSummary }) {
  const segments = Object.entries(summary.by_segment) as [string, number][];

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-4">
      <p className="mb-3 text-sm font-medium text-gray-300">Risco de churn por segmento</p>
      <div className="space-y-2">
        {segments.map(([segment, count]) => {
          const pct = summary.total_customers > 0 ? (count / summary.total_customers) * 100 : 0;
          return (
            <div key={segment}>
              <div className="mb-1 flex justify-between text-xs text-gray-400">
                <span>{segment}</span>
                <span>
                  {count} clientes ({pct.toFixed(1)}%)
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-black/30">
                <div
                  className={`h-full ${SEGMENT_COLOR[segment] ?? "bg-gray-500"}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
