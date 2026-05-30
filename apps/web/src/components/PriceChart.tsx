"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Bar = { bar_date: string; close: number };

export function PriceChart({ data }: { data: Bar[] }) {
  const chart = data.map((d) => ({
    date: d.bar_date.slice(5),
    close: d.close,
  }));
  if (!chart.length) {
    return <p className="text-sm text-gray-500">暂无 K 线，请先在数据中心同步行情</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={chart}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2d3a4f" />
        <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
        <YAxis stroke="#64748b" fontSize={11} domain={["auto", "auto"]} />
        <Tooltip contentStyle={{ background: "#1a2332", border: "1px solid #2d3a4f" }} />
        <Line type="monotone" dataKey="close" stroke="#22c55e" dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  );
}
