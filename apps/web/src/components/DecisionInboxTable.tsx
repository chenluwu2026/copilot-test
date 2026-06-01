"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Decision } from "@/lib/api";
import { api } from "@/lib/api";

export function DecisionInboxTable({
  items,
  showReject = true,
}: {
  items: Decision[];
  showReject?: boolean;
}) {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);

  async function setStatus(id: string, status: string) {
    setLoading(`${status}-${id}`);
    try {
      await api.updateDecisionStatus(id, status);
      router.refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(null);
    }
  }

  if (!items.length) {
    return <p className="text-sm text-gray-500">收件箱为空</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="text-gray-400">
        <tr>
          <th>标的</th>
          <th>动作</th>
          <th>仓位</th>
          <th>状态</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {items.map((d) => (
          <tr key={d.id} className="border-t border-aims-border">
            <td className="py-2">{d.name}</td>
            <td>{d.action}</td>
            <td>
              {d.current_weight_pct}% → {d.target_weight_pct}%
            </td>
            <td>{d.status}</td>
            <td className="space-x-2 whitespace-nowrap">
              <Link href={`/decisions/${d.id}`} className="text-aims-accent">
                详情
              </Link>
              {d.status === "draft" && (
                <>
                  <button
                    type="button"
                    onClick={() => setStatus(d.id, "approved")}
                    disabled={!!loading}
                    className="text-aims-positive"
                  >
                    批准
                  </button>
                  {showReject && (
                    <button
                      type="button"
                      onClick={() => setStatus(d.id, "cancelled")}
                      disabled={!!loading}
                      className="text-gray-400"
                    >
                      拒绝
                    </button>
                  )}
                </>
              )}
              {d.status === "approved" && (
                <button
                  type="button"
                  onClick={() => api.executeDecision(d.id).then(() => router.refresh())}
                  disabled={!!loading}
                  className="text-aims-accent"
                >
                  执行
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
