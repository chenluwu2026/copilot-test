"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { PendingMemoryDecision } from "@/lib/api";
import { api } from "@/lib/api";

export function ReviewPendingMemoryPanel({ items }: { items: PendingMemoryDecision[] }) {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);

  async function promote(decisionId: string, activate: boolean) {
    const key = `${decisionId}-${activate}`;
    setLoading(key);
    try {
      await api.promoteReviewMemory(decisionId, { activate });
      router.refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(null);
    }
  }

  if (!items.length) {
    return (
      <p className="text-sm text-gray-500">暂无待沉淀/激活的记忆。完成复盘后可在此一键激活。</p>
    );
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="text-gray-400">
        <tr>
          <th>标的</th>
          <th>复盘收益</th>
          <th>摘要</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {items.map((d) => (
          <tr key={d.decision_id} className="border-t border-aims-border">
            <td className="py-2">
              {d.name}
              <span className="ml-1 text-xs text-gray-500">{d.symbol}</span>
            </td>
            <td
              className={
                d.return_pct >= 0 ? "text-aims-positive" : "text-aims-negative"
              }
            >
              {d.return_pct}%
            </td>
            <td className="max-w-xs truncate text-gray-400">{d.outcome_summary}</td>
            <td className="space-x-2 whitespace-nowrap">
              <button
                type="button"
                onClick={() => promote(d.decision_id, false)}
                disabled={!!loading}
                className="text-aims-accent"
              >
                {loading === `${d.decision_id}-false` ? "…" : "沉淀记忆"}
              </button>
              <button
                type="button"
                onClick={() => promote(d.decision_id, true)}
                disabled={!!loading}
                className="rounded bg-aims-accent px-2 py-0.5 text-xs text-white"
              >
                {loading === `${d.decision_id}-true` ? "…" : "沉淀并激活"}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
