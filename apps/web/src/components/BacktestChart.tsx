"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BacktestRow } from "@/lib/api";

export function BacktestChart({ items }: { items: BacktestRow[] }) {
  if (!items.length) {
    return <p className="text-sm text-gray-500">运行复盘后显示决策收益分布</p>;
  }
  const chartData = items.map((b) => ({
    name: b.symbol || b.decision_id.slice(0, 6),
    return_pct: b.return_pct,
  }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData}>
        <XAxis dataKey="name" stroke="#64748b" fontSize={10} angle={-25} textAnchor="end" height={50} />
        <YAxis stroke="#64748b" fontSize={11} unit="%" />
        <Tooltip
          contentStyle={{ background: "#1a2332", border: "1px solid #2d3a4f" }}
          formatter={(v: number) => [`${v}%`, "收益"]}
        />
        <Bar dataKey="return_pct">
          {chartData.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.return_pct >= 0 ? "#22c55e" : "#ef4444"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
