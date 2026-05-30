"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { OpenDecision } from "@/lib/api";
import { api } from "@/lib/api";

export function ReviewBoard({ items }: { items: OpenDecision[] }) {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);

  async function review(id: string) {
    setLoading(id);
    try {
      const res = await api.runReview(id);
      if (res.memory_id) {
        alert(`复盘完成。已生成待确认记忆，可在下方记忆库激活。`);
      }
      router.refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(null);
    }
  }

  if (!items.length) {
    return <p className="text-sm text-gray-500">暂无待复盘决策</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="text-gray-400">
        <tr>
          <th>标的</th>
          <th>动作</th>
          <th>决策后收益</th>
          <th>数据源</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {items.map((d) => (
          <tr key={d.decision_id} className="border-t border-aims-border">
            <td className="py-2">{d.name}</td>
            <td>{d.action}</td>
            <td
              className={
                (d.return_since_decision_pct ?? 0) >= 0
                  ? "text-aims-positive"
                  : "text-aims-negative"
              }
            >
              {d.return_since_decision_pct != null
                ? `${d.return_since_decision_pct}%`
                : "—"}
            </td>
            <td className="text-xs text-gray-500">{d.price_source ?? "—"}</td>
            <td>
              <button
                onClick={() => review(d.decision_id)}
                disabled={!!loading}
                className="text-aims-accent"
              >
                {loading === d.decision_id ? "复盘…" : "复盘"}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
