"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
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

export function ReviewBoard({
  items,
  portfolioId,
}: {
  items: OpenDecision[];
  portfolioId: string;
}) {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);

  const dueCount = useMemo(
    () =>
      items.filter(
        (d) => d.urgency === "due" || d.urgency === "overdue" || d.review_due
      ).length,
    [items]
  );

  async function review(id: string) {
    setLoading(`review-${id}`);
    try {
      const res = await api.runReview(id);
      if (res.review_quality) {
        const failed = res.review_quality.checklist.filter((c) => !c.ok);
        const msg = [
          `复盘质量 ${res.review_quality.quality_pct}%`,
          ...failed.map((c) => `· ${c.item}: ${c.detail}`),
        ].join("\n");
        if (failed.length) alert(msg);
      }
      const ledgerNote = res.ledger_has_postmortem
        ? "\n\n已回写决策账本（postmortem）。"
        : res.ledger_status
          ? `\n\n账本状态：${res.ledger_status}`
          : "";
      if (res.memory_id) {
        const ok = confirm(
          `复盘完成，已生成待确认记忆。${ledgerNote}\n\n是否立即激活？激活后将在下次 CIO 调仓时注入。`
        );
        if (ok) {
          await api.activateMemory(res.memory_id);
        }
      } else if (ledgerNote) {
        alert(`复盘完成。${ledgerNote.trim()}`);
      }
      router.refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(null);
    }
  }

  async function batchReview(urgency: "due" | "all") {
    const n = urgency === "due" ? dueCount : items.length;
    if (n === 0) {
      alert(urgency === "due" ? "暂无到期/逾期待复盘项" : "暂无待复盘决策");
      return;
    }
    const ok = confirm(
      urgency === "due"
        ? `将对 ${n} 条到期/逾期待复盘决策依次运行复盘（最多 20 条），并回写账本。继续？`
        : `将对全部 ${n} 条待复盘决策依次运行复盘（最多 20 条）。继续？`
    );
    if (!ok) return;
    setLoading(`batch-${urgency}`);
    try {
      const res = await api.runReviewBatch({
        portfolio_id: portfolioId,
        urgency,
        limit: 20,
      });
      let msg = `批量复盘完成：成功 ${res.succeeded}，失败 ${res.failed}`;
      if (res.memory_ids.length) {
        msg += `\n生成 ${res.memory_ids.length} 条待确认记忆。`;
        const activate = confirm(`${msg}\n\n是否全部激活这些记忆？`);
        if (activate) {
          for (const mid of res.memory_ids) {
            try {
              await api.activateMemory(mid);
            } catch {
              /* skip */
            }
          }
        }
      } else {
        alert(msg);
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
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <button
          type="button"
          disabled={!!loading || dueCount === 0}
          onClick={() => batchReview("due")}
          className="rounded bg-aims-accent px-3 py-1.5 text-white disabled:opacity-50"
        >
          {loading === "batch-due" ? "批量复盘…" : `批量复盘（到期 ${dueCount}）`}
        </button>
        <button
          type="button"
          disabled={!!loading}
          onClick={() => batchReview("all")}
          className="rounded border border-aims-border px-3 py-1.5 text-gray-300 disabled:opacity-50"
        >
          {loading === "batch-all" ? "处理中…" : `批量复盘（全部 ${items.length}）`}
        </button>
        <span className="text-xs text-gray-500">单次最多 20 条 · 自动回写 Ledger</span>
      </div>

      <table className="w-full text-left text-sm">
        <thead className="text-gray-400">
          <tr>
            <th>标的</th>
            <th>动作</th>
            <th>执行天数</th>
            <th>状态</th>
            <th>决策后收益</th>
            <th>账本</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((d) => (
            <tr key={d.decision_id} className="border-t border-aims-border">
              <td className="py-2">
                <Link
                  href={`/decisions/${d.decision_id}`}
                  className="text-aims-accent hover:underline"
                >
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
              <td className="text-xs text-gray-400">
                {d.ledger_status ? (
                  <span>
                    {d.ledger_status}
                    {d.has_postmortem ? " · 已复盘" : ""}
                  </span>
                ) : (
                  "—"
                )}
                <br />
                <Link
                  href={`/decisions/${d.decision_id}#decision-ledger`}
                  className="text-aims-accent"
                >
                  账本 →
                </Link>
                {d.run_id && (
                  <>
                    {" "}
                    <Link
                      href={`/fm/runs/${encodeURIComponent(d.run_id)}`}
                      className="text-gray-500 hover:text-aims-accent"
                    >
                      批次
                    </Link>
                  </>
                )}
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
    </div>
  );
}
