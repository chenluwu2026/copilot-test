"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type WeightCompareRow = {
  label: string;
  current: number;
  target: number;
};

export function PortfolioWeightCompareChart({
  targets,
  maxBars = 12,
}: {
  targets: {
    symbol?: string | null;
    security_id: string;
    current_weight_pct: number;
    target_weight_pct: number;
  }[];
  maxBars?: number;
}) {
  const rows: WeightCompareRow[] = targets
    .slice(0, maxBars)
    .map((t) => ({
      label: t.symbol || t.security_id.slice(0, 8),
      current: Number(t.current_weight_pct) || 0,
      target: Number(t.target_weight_pct) || 0,
    }))
    .filter((r) => Math.abs(r.current - r.target) > 0.01 || r.target > 0);

  if (!rows.length) {
    return <p className="text-sm text-gray-500">暂无权重对比数据</p>;
  }

  return (
    <div className="mt-2">
      <p className="mb-2 text-xs text-gray-500">当前权重 vs 目标权重（%）</p>
      <ResponsiveContainer width="100%" height={Math.max(220, rows.length * 36)}>
        <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d3a4f" />
          <XAxis type="number" stroke="#64748b" fontSize={11} domain={[0, "auto"]} />
          <YAxis type="category" dataKey="label" stroke="#64748b" fontSize={11} width={72} />
          <Tooltip
            contentStyle={{ background: "#1a2332", border: "1px solid #2d3a4f" }}
            formatter={(v: number) => [`${v.toFixed(2)}%`, ""]}
          />
          <Legend />
          <Bar dataKey="current" name="当前" fill="#64748b" radius={[0, 2, 2, 0]} />
          <Bar dataKey="target" name="目标" fill="#3b82f6" radius={[0, 2, 2, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
