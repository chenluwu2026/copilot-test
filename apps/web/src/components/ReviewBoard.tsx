"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { OpenDecision } from "@/lib/api";
import { api } from "@/lib/api";

const urgencyLabel: Record<string, string> = {
  overdue: "已逾期",
  due: "到期待复盘",
  ok: "未到期",
  unknown: "—",
};

const urgencyClass: Record<string, string> = {
  overdue: "text-aims-negative",
  due: "text-yellow-400",
  ok: "text-gray-500",
  unknown: "text-gray-500",
};

export function ReviewBoard({ items }: { items: OpenDecision[] }) {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);

  async function review(id: string) {
    setLoading(`review-${id}`);
    try {
      const res = await api.runReview(id);
      if (res.memory_id) {
        const ok = confirm(
          "复盘完成，已生成待确认记忆。是否立即激活？激活后将在下次 CIO 调仓时注入。"
        );
        if (ok) {
          await api.activateMemory(res.memory_id);
        }
      }
      router.refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(null);
    }
  }

  async function activateMemoryId(memoryId: string) {
    setLoading(`mem-${memoryId}`);
    try {
      await api.activateMemory(memoryId);
      router.refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(null);
    }
  }

  async function promote(decisionId: string, activate: boolean) {
    setLoading(`promote-${decisionId}-${activate}`);
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
    return <p className="text-sm text-gray-500">暂无待复盘决策</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="text-gray-400">
        <tr>
          <th>标的</th>
          <th>动作</th>
          <th>执行天数</th>
          <th>状态</th>
          <th>决策后收益</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {items.map((d) => (
          <tr key={d.decision_id} className="border-t border-aims-border">
            <td className="py-2">
              <Link href={`/decisions/${d.decision_id}`} className="text-aims-accent hover:underline">
                {d.name}
              </Link>
              <span className="ml-1 text-xs text-gray-500">{d.symbol}</span>
            </td>
            <td>{d.action}</td>
            <td>{d.days_since_execution ?? "—"}</td>
            <td className={urgencyClass[d.urgency ?? "unknown"]}>
              {urgencyLabel[d.urgency ?? "unknown"]}
            </td>
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
            <td className="space-x-2 whitespace-nowrap">
              <button
                type="button"
                onClick={() => review(d.decision_id)}
                disabled={!!loading}
                className="text-aims-accent"
              >
                {loading === `review-${d.decision_id}` ? "复盘…" : "复盘"}
              </button>
              {d.pending_memory_id && (
                <button
                  type="button"
                  onClick={() => activateMemoryId(d.pending_memory_id!)}
                  disabled={!!loading}
                  className="text-xs text-yellow-400"
                >
                  激活记忆
                </button>
              )}
              {d.has_outcome && !d.pending_memory_id && (
                <button
                  type="button"
                  onClick={() => promote(d.decision_id, true)}
                  disabled={!!loading}
                  className="text-xs text-gray-400"
                >
                  沉淀并激活
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
