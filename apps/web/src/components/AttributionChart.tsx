"use client";

import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AttributionReport } from "@/lib/api";

export function AttributionChart({ data }: { data: AttributionReport }) {
  const chartData = data.sector_attribution.map((s) => ({
    name: s.sector,
    pnl: s.unrealized_pnl,
  }));
  if (!chartData.length) return <p className="text-sm text-gray-500">暂无归因数据</p>;
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData}>
        <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
        <YAxis stroke="#64748b" fontSize={11} />
        <Tooltip contentStyle={{ background: "#1a2332", border: "1px solid #2d3a4f" }} />
        <Bar dataKey="pnl" fill="#3b82f6" />
      </BarChart>
    </ResponsiveContainer>
  );
}
