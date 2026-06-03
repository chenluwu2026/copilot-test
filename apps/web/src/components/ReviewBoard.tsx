"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import type { BatchReviewResult, OpenDecision } from "@/lib/api";
import { api } from "@/lib/api";
import { buildRunGroups, toggleSetMember } from "@/lib/runGroups";
import {
  BatchOperationResultPanel,
  type BatchResultRow,
} from "@/components/BatchOperationResultPanel";

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

function ReviewRow({
  d,
  loading,
  selected,
  onToggle,
  onReview,
  onActivateMemory,
  onPromote,
}: {
  d: OpenDecision;
  loading: string | null;
  selected: boolean;
  onToggle: () => void;
  onReview: () => void;
  onActivateMemory: () => void;
  onPromote: () => void;
}) {
  return (
    <tr className={`border-t border-aims-border ${selected ? "bg-aims-accent/5" : ""}`}>
      <td className="py-2">
        <input type="checkbox" checked={selected} onChange={onToggle} className="mr-2" />
        <Link href={`/decisions/${d.decision_id}`} className="text-aims-accent hover:underline">
          {d.name}
        </Link>
        <span className="ml-1 text-xs text-gray-500">{d.symbol}</span>
      </td>
      <td>{d.action}</td>
      <td>{d.days_since_execution ?? "—"}</td>
      <td className={urgencyClass[d.urgency ?? "unknown"]}>{urgencyLabel[d.urgency ?? "unknown"]}</td>
      <td
        className={
          (d.return_since_decision_pct ?? 0) >= 0 ? "text-aims-positive" : "text-aims-negative"
        }
      >
        {d.return_since_decision_pct != null ? `${d.return_since_decision_pct}%` : "—"}
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
        <Link href={`/decisions/${d.decision_id}#decision-ledger`} className="text-aims-accent">
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
        <button type="button" onClick={onReview} disabled={!!loading} className="text-aims-accent">
          {loading === `review-${d.decision_id}` ? "复盘…" : "复盘"}
        </button>
        {d.pending_memory_id && (
          <button
            type="button"
            onClick={onActivateMemory}
            disabled={!!loading}
            className="text-xs text-yellow-400"
          >
            激活记忆
          </button>
        )}
        {d.has_outcome && !d.pending_memory_id && (
          <button
            type="button"
            onClick={onPromote}
            disabled={!!loading}
            className="text-xs text-gray-400"
          >
            沉淀并激活
          </button>
        )}
      </td>
    </tr>
  );
}

function rowsFromReviewBatch(res: BatchReviewResult, items: OpenDecision[]): BatchResultRow[] {
  const byId = new Map(items.map((d) => [d.decision_id, d]));
  return res.results.map((r) => {
    const d = byId.get(r.decision_id);
    return {
      id: r.decision_id,
      ok: r.ok,
      label: d ? `${d.name} (${d.symbol})` : r.symbol || r.decision_id.slice(0, 8),
      detail: r.ok
        ? `${r.return_since_decision_pct ?? "—"}%${r.ledger_has_postmortem ? " · 已回写账本" : ""}`
        : r.error,
      href: `/decisions/${r.decision_id}#decision-ledger`,
    };
  });
}

export function ReviewBoard({
  items,
  portfolioId,
  initialRunId,
}: {
  items: OpenDecision[];
  portfolioId: string;
  initialRunId?: string;
}) {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [runFilter, setRunFilter] = useState(initialRunId || "");
  const [batchPanel, setBatchPanel] = useState<{
    title: string;
    res: BatchReviewResult;
  } | null>(null);

  const filteredItems = useMemo(
    () => (runFilter ? items.filter((d) => d.run_id === runFilter) : items),
    [items, runFilter]
  );

  const runOptions = useMemo(() => {
    const ids = new Set<string>();
    for (const d of items) {
      if (d.run_id) ids.add(d.run_id);
    }
    return Array.from(ids).sort().reverse();
  }, [items]);

  const groups = useMemo(
    () => buildRunGroups(filteredItems, (d) => d.run_id),
    [filteredItems]
  );

  const dueCount = useMemo(
    () =>
      filteredItems.filter(
        (d) => d.urgency === "due" || d.urgency === "overdue" || d.review_due
      ).length,
    [filteredItems]
  );

  function applyRunFilter(runId: string) {
    setRunFilter(runId);
    if (runId) router.push(`/review?run_id=${encodeURIComponent(runId)}`);
    else router.push("/review");
  }

  async function finishBatchReview(res: BatchReviewResult, label: string) {
    setBatchPanel({ title: `批量复盘 · ${label}`, res });
    const failedIds = new Set(res.results.filter((r) => !r.ok).map((r) => r.decision_id));
    setSelected(failedIds);
    if (res.memory_ids.length) {
      const activate = confirm(
        `批量复盘完成（成功 ${res.succeeded}，失败 ${res.failed}）。\n生成 ${res.memory_ids.length} 条待确认记忆，是否全部激活？`
      );
      if (activate) {
        for (const mid of res.memory_ids) {
          try {
            await api.activateMemory(mid);
          } catch {
            /* skip */
          }
        }
      }
    }
    router.refresh();
  }

  async function review(id: string) {
    setLoading(`review-${id}`);
    try {
      const res = await api.runReview(id);
      if (res.review_quality) {
        const failed = res.review_quality.checklist.filter((c) => !c.ok);
        if (failed.length) {
          const msg = [
            `复盘质量 ${res.review_quality.quality_pct}%`,
            ...failed.map((c) => `· ${c.item}: ${c.detail}`),
          ].join("\n");
          alert(msg);
        }
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
        if (ok) await api.activateMemory(res.memory_id);
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

  async function batchReviewByIds(decisionIds: string[], label: string) {
    if (!decisionIds.length) return;
    const ok = confirm(`将对已选 ${decisionIds.length} 条决策运行复盘（${label}，最多 20 条）并回写账本。继续？`);
    if (!ok) return;
    setLoading(`batch-ids-${label}`);
    try {
      const res = await api.runReviewBatch({
        portfolio_id: portfolioId,
        decision_ids: decisionIds.slice(0, 20),
        limit: 20,
      });
      await finishBatchReview(res, label);
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(null);
    }
  }

  async function batchReview(urgency: "due" | "all") {
    const n = urgency === "due" ? dueCount : filteredItems.length;
    if (n === 0) {
      alert(urgency === "due" ? "暂无到期/逾期待复盘项" : "暂无待复盘决策");
      return;
    }
    const ok = confirm(
      urgency === "due"
        ? `将对 ${n} 条到期/逾期待复盘决策依次运行复盘（最多 20 条），并回写账本。继续？`
        : `将对当前筛选的 ${n} 条待复盘决策依次运行复盘（最多 20 条）。继续？`
    );
    if (!ok) return;
    setLoading(`batch-${urgency}`);
    try {
      const ids =
        urgency === "due"
          ? filteredItems
              .filter(
                (d) =>
                  d.urgency === "due" || d.urgency === "overdue" || d.review_due
              )
              .map((d) => d.decision_id)
          : filteredItems.map((d) => d.decision_id);
      const res = await api.runReviewBatch({
        portfolio_id: portfolioId,
        decision_ids: ids.slice(0, 20),
        limit: 20,
      });
      const label =
        urgency === "due"
          ? runFilter
            ? `到期 · ${runFilter}`
            : "到期"
          : runFilter
            ? `批次 ${runFilter}`
            : "全部";
      await finishBatchReview(res, label);
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(null);
    }
  }

  function selectGroup(groupItems: OpenDecision[], checked: boolean) {
    setSelected((prev) => {
      const next = new Set(prev);
      for (const d of groupItems) {
        if (checked) next.add(d.decision_id);
        else next.delete(d.decision_id);
      }
      return next;
    });
  }

  if (!items.length) {
    return <p className="text-sm text-gray-500">暂无待复盘决策</p>;
  }

  const selectedIds = Array.from(selected);

  return (
    <div className="space-y-4">
      {batchPanel && (
        <BatchOperationResultPanel
          title={batchPanel.title}
          succeeded={batchPanel.res.succeeded}
          failed={batchPanel.res.failed}
          rows={rowsFromReviewBatch(batchPanel.res, items)}
          onDismiss={() => setBatchPanel(null)}
        />
      )}

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <label className="flex items-center gap-2 text-xs text-gray-500">
          批次筛选
          <select
            value={runFilter}
            onChange={(e) => applyRunFilter(e.target.value)}
            className="rounded border border-aims-border bg-aims-bg px-2 py-1 text-sm text-gray-300"
          >
            <option value="">全部（{items.length}）</option>
            {runOptions.map((rid) => (
              <option key={rid} value={rid}>
                {rid}（{items.filter((d) => d.run_id === rid).length}）
              </option>
            ))}
          </select>
        </label>
        {runFilter && (
          <Link
            href={`/fm/runs/${encodeURIComponent(runFilter)}`}
            className="text-xs text-aims-accent underline"
          >
            批次详情 →
          </Link>
        )}
      </div>

      {filteredItems.length === 0 ? (
        <p className="text-sm text-gray-500">该批次下暂无待复盘决策</p>
      ) : null}

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
          {loading === "batch-all" ? "处理中…" : `批量复盘（当前 ${filteredItems.length}）`}
        </button>
        {selectedIds.length > 0 && (
          <button
            type="button"
            disabled={!!loading}
            onClick={() => batchReviewByIds(selectedIds, "已勾选")}
            className="rounded border border-aims-research/50 px-3 py-1.5 text-aims-research"
          >
            {loading?.startsWith("batch-ids") ? "复盘…" : `复盘已选（${selectedIds.length}）`}
          </button>
        )}
        <span className="text-xs text-gray-500">
          按 run_id 分组 · 共 {groups.length} 组 · 单次最多 20 条
          {runFilter ? ` · 已筛批次` : ""}
        </span>
      </div>

      {filteredItems.length > 0 &&
        groups.map((g) => {
        const isCollapsed = collapsed[g.key] ?? false;
        const groupIds = g.items.map((d) => d.decision_id);
        const allSelected = groupIds.length > 0 && groupIds.every((id) => selected.has(id));
        const someSelected = groupIds.some((id) => selected.has(id));

        return (
          <section
            key={g.key}
            className="rounded-lg border border-aims-border/80 bg-aims-bg/30"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-aims-border/60 px-3 py-2">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = someSelected && !allSelected;
                  }}
                  onChange={() => selectGroup(g.items, !allSelected)}
                />
                <button
                  type="button"
                  className="text-left text-sm font-medium text-gray-300"
                  onClick={() => setCollapsed((c) => ({ ...c, [g.key]: !isCollapsed }))}
                >
                  {isCollapsed ? "▸" : "▾"} {g.label}
                  <span className="ml-2 text-xs text-gray-500">({g.items.length} 条)</span>
                </button>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                {g.runId && (
                  <Link
                    href={`/fm/runs/${encodeURIComponent(g.runId)}`}
                    className="text-aims-accent underline"
                  >
                    批次详情
                  </Link>
                )}
                <button
                  type="button"
                  disabled={!!loading}
                  className="text-aims-accent"
                  onClick={() => batchReviewByIds(groupIds, g.label)}
                >
                  本组复盘
                </button>
              </div>
            </div>
            {!isCollapsed && (
              <div className="overflow-x-auto p-2">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="text-gray-400">
                    <tr>
                      <th>标的</th>
                      <th>动作</th>
                      <th>天数</th>
                      <th>状态</th>
                      <th>收益</th>
                      <th>账本</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {g.items.map((d) => (
                      <ReviewRow
                        key={d.decision_id}
                        d={d}
                        loading={loading}
                        selected={selected.has(d.decision_id)}
                        onToggle={() =>
                          setSelected((s) => toggleSetMember(s, d.decision_id))
                        }
                        onReview={() => review(d.decision_id)}
                        onActivateMemory={() => {
                          if (d.pending_memory_id) {
                            setLoading(`mem-${d.pending_memory_id}`);
                            api
                              .activateMemory(d.pending_memory_id)
                              .then(() => router.refresh())
                              .catch((e) => alert(String(e)))
                              .finally(() => setLoading(null));
                          }
                        }}
                        onPromote={() => {
                          setLoading(`promote-${d.decision_id}`);
                          api
                            .promoteReviewMemory(d.decision_id, { activate: true })
                            .then(() => router.refresh())
                            .catch((e) => alert(String(e)))
                            .finally(() => setLoading(null));
                        }}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
