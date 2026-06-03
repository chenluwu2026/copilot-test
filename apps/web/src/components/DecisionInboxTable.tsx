"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Decision } from "@/lib/api";
import { api } from "@/lib/api";

function sourceBadge(agent?: string) {
  if (!agent) return null;
  const label =
    agent === "decision_pipeline"
      ? "流水线"
      : agent === "cio_agent"
        ? "CIO"
        : agent === "fm_daily"
          ? "一日编排"
          : agent;
  const color =
    agent === "decision_pipeline" || agent === "fm_daily"
      ? "border-aims-research/40 text-aims-research"
      : "border-gray-600 text-gray-400";
  return (
    <span className={`ml-1 rounded border px-1 py-0.5 text-[10px] ${color}`}>{label}</span>
  );
}

function gradeBadge(grade?: string) {
  if (!grade) return null;
  const colors: Record<string, string> = {
    A: "text-aims-positive border-aims-positive/40",
    B: "text-yellow-400 border-yellow-600/40",
    C: "text-red-400 border-red-600/40",
  };
  return (
    <span
      className={`ml-2 rounded border px-1.5 py-0.5 text-xs ${colors[grade] || "text-gray-400 border-gray-600"}`}
      title="证据完整度"
    >
      证据 {grade}
    </span>
  );
}

export function DecisionInboxTable({
  items,
  showReject = true,
  groupByRun: _groupByRun = true,
  selectedIds,
  onToggleSelect,
}: {
  items: Decision[];
  showReject?: boolean;
  /** 由 DecisionInboxGrouped 内嵌时传 false */
  groupByRun?: boolean;
  selectedIds?: Set<string>;
  onToggleSelect?: (id: string) => void;
}) {
  const selectable = !!selectedIds && !!onToggleSelect;
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);

  const sorted = [...items].sort((a, b) => {
    const order = { C: 0, B: 1, A: 2 };
    const ga = a.evidence_grade || "B";
    const gb = b.evidence_grade || "B";
    return (order[ga as keyof typeof order] ?? 1) - (order[gb as keyof typeof order] ?? 1);
  });

  async function setStatus(id: string, status: string) {
    const item = items.find((x) => x.id === id);
    if (
      status === "approved" &&
      item?.evidence_grade === "C" &&
      (!item.references || item.references.length < 1)
    ) {
      alert("证据不足（等级 C 且无参考信息），请补充参考后再批准。");
      return;
    }
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

  async function execute(id: string, action: string) {
    setLoading(`exec-${id}`);
    try {
      const res = await api.executeDecision(id);
      if (res.message) {
        alert(res.message);
      }
      router.refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(null);
    }
  }

  function executeLabel(action: string, current: number, target: number) {
    const noChange =
      action === "hold" ||
      action === "watch" ||
      action === "ban" ||
      Math.abs(target - current) < 0.01;
    return noChange ? "确认" : "执行";
  }

  if (!sorted.length) {
    return <p className="text-sm text-gray-500">收件箱为空</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="text-gray-400">
        <tr>
          {selectable && <th className="w-8"></th>}
          <th>标的 / 来源</th>
          <th>动作</th>
          <th>仓位</th>
          <th>证据</th>
          <th>状态</th>
          <th>账本</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((d) => (
          <tr
            key={d.id}
            className={`border-t border-aims-border ${
              selectable && selectedIds?.has(d.id) ? "bg-aims-accent/5" : ""
            }`}
          >
            {selectable && (
              <td className="py-2">
                <input
                  type="checkbox"
                  checked={selectedIds!.has(d.id)}
                  onChange={() => onToggleSelect!(d.id)}
                />
              </td>
            )}
            <td className="py-2">
              {d.name}
              {sourceBadge(d.created_by_agent)}
              {gradeBadge(d.evidence_grade)}
            </td>
            <td>{d.action}</td>
            <td>
              {d.current_weight_pct}% → {d.target_weight_pct}%
            </td>
            <td className="text-xs text-gray-400">
              {d.evidence_score != null ? `${d.evidence_score} 分` : "—"}
            </td>
            <td>{d.status}</td>
            <td className="text-xs text-gray-400">
              {d.ledger_status ?? "—"}
              {d.run_id && (
                <div>
                  <Link
                    href={`/fm/runs/${encodeURIComponent(d.run_id)}`}
                    className="text-aims-accent"
                  >
                    {d.run_id.slice(0, 18)}…
                  </Link>
                </div>
              )}
            </td>
            <td className="space-x-2 whitespace-nowrap">
              <Link href={`/decisions/${d.id}#decision-ledger`} className="text-aims-accent">
                账本
              </Link>
              <Link href={`/decisions/${d.id}`} className="text-gray-400">
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
                  onClick={() => execute(d.id, d.action)}
                  disabled={!!loading}
                  className="text-aims-accent"
                  title={
                    d.action === "hold" || d.current_weight_pct === d.target_weight_pct
                      ? "维持仓位，确认后标记为已处理"
                      : undefined
                  }
                >
                  {executeLabel(d.action, d.current_weight_pct, d.target_weight_pct)}
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
