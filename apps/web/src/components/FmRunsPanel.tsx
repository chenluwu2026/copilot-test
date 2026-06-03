"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type FmRunSummary } from "@/lib/api";

export function FmRunsPanel({ portfolioId }: { portfolioId: string }) {
  const [runs, setRuns] = useState<FmRunSummary[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const data = await api.fmRuns(portfolioId);
        if (!cancelled) setRuns(data);
      } catch (e) {
        if (!cancelled) setError(String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [portfolioId]);

  if (loading) return <p className="text-sm text-gray-500">加载批次记录…</p>;
  if (error) return <p className="text-sm text-aims-negative">{error}</p>;
  if (!runs.length) {
    return (
      <p className="text-sm text-gray-500">
        暂无一日流水线批次。请在{" "}
        <Link href="/" className="text-aims-accent underline">
          指挥中心
        </Link>{" "}
        运行「一日流水线」。
      </p>
    );
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="text-gray-400">
        <tr>
          <th className="pb-2">run_id</th>
          <th>时间</th>
          <th>账本</th>
          <th>建单</th>
          <th>拒单率</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {runs.map((r) => (
          <tr key={r.run_id} className="border-t border-aims-border">
            <td className="py-2 font-mono text-xs">{r.run_id}</td>
            <td className="text-gray-400">{r.created_at?.replace("T", " ").slice(0, 19) ?? "—"}</td>
            <td>{r.ledger_count}</td>
            <td>{r.decision_count}</td>
            <td className={r.rejection_rate_pct >= 40 ? "text-aims-negative" : ""}>
              {r.rejection_rate_pct}%
            </td>
            <td>
              <Link href={`/fm/runs/${encodeURIComponent(r.run_id)}`} className="text-aims-accent">
                详情 →
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
