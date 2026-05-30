"use client";

import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { NavPoint } from "@/lib/api";

export function NavChart({ data }: { data: NavPoint[] }) {
  const chartData = data.map((d) => ({
    date: d.snapshot_date.slice(5),
    nav: d.nav,
  }));
  if (!chartData.length) {
    return <p className="text-sm text-gray-500">暂无净值数据</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={chartData}>
        <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
        <YAxis stroke="#64748b" fontSize={12} domain={["auto", "auto"]} />
        <Tooltip
          contentStyle={{ background: "#1a2332", border: "1px solid #2d3a4f" }}
        />
        <Line type="monotone" dataKey="nav" stroke="#3b82f6" dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  );
}
