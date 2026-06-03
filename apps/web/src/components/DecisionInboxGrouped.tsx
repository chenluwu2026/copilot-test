"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import type { Decision } from "@/lib/api";
import { api } from "@/lib/api";
import { buildRunGroups, toggleSetMember } from "@/lib/runGroups";
import { DecisionInboxTable } from "@/components/DecisionInboxTable";

export function DecisionInboxGrouped({
  items,
  showReject = true,
}: {
  items: Decision[];
  showReject?: boolean;
}) {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const groups = useMemo(() => buildRunGroups(items, (d) => d.run_id), [items]);

  async function batchAction(
    decisionIds: string[],
    action: "approve" | "cancel" | "execute",
    label: string
  ) {
    if (!decisionIds.length) return;
    const actionLabel =
      action === "approve" ? "批准" : action === "cancel" ? "拒绝" : "执行";
    const ok = confirm(`对 ${decisionIds.length} 条决策「${actionLabel}」（${label}）？`);
    if (!ok) return;
    setLoading(`${action}-${label}`);
    try {
      const res = await api.batchDecisionActions({ decision_ids: decisionIds, action });
      alert(`完成：成功 ${res.succeeded}，失败 ${res.failed}`);
      setSelected(new Set());
      router.refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(null);
    }
  }

  function selectGroup(groupItems: Decision[], checked: boolean) {
    setSelected((prev) => {
      const next = new Set(prev);
      for (const d of groupItems) {
        if (checked) next.add(d.id);
        else next.delete(d.id);
      }
      return next;
    });
  }

  if (!items.length) {
    return <p className="text-sm text-gray-500">收件箱为空</p>;
  }

  const allDraft = items.every((d) => d.status === "draft");
  const allApproved = items.every((d) => d.status === "approved");
  const selectedIds = Array.from(selected);
  const selectedItems = items.filter((d) => selected.has(d.id));
  const selectedAllDraft =
    selectedItems.length > 0 && selectedItems.every((d) => d.status === "draft");
  const selectedAllApproved =
    selectedItems.length > 0 && selectedItems.every((d) => d.status === "approved");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
        <span>按 run_id 分组 · 共 {groups.length} 组</span>
        {selectedIds.length > 0 && (
          <>
            <span className="text-aims-research">已选 {selectedIds.length} 条</span>
            {selectedAllDraft && showReject && (
              <>
                <button
                  type="button"
                  disabled={!!loading}
                  className="text-aims-positive"
                  onClick={() => batchAction(selectedIds, "approve", "已勾选")}
                >
                  批准已选
                </button>
                <button
                  type="button"
                  disabled={!!loading}
                  className="text-gray-400"
                  onClick={() => batchAction(selectedIds, "cancel", "已勾选")}
                >
                  拒绝已选
                </button>
              </>
            )}
            {selectedAllApproved && (
              <button
                type="button"
                disabled={!!loading}
                className="text-aims-accent"
                onClick={() => batchAction(selectedIds, "execute", "已勾选")}
              >
                执行已选
              </button>
            )}
            <button
              type="button"
              className="text-gray-500"
              onClick={() => setSelected(new Set())}
            >
              清除选择
            </button>
          </>
        )}
        {selectedIds.length === 0 && allDraft && items.length > 1 && (
          <button
            type="button"
            disabled={!!loading}
            className="rounded border border-aims-accent/50 px-2 py-1 text-aims-accent"
            onClick={() => batchAction(items.map((d) => d.id), "approve", "全部")}
          >
            {loading?.includes("approve") ? "处理中…" : `全部批准（${items.length}）`}
          </button>
        )}
        {selectedIds.length === 0 && allApproved && items.length > 1 && (
          <button
            type="button"
            disabled={!!loading}
            className="rounded border border-aims-accent/50 px-2 py-1 text-aims-accent"
            onClick={() => batchAction(items.map((d) => d.id), "execute", "全部")}
          >
            {loading?.includes("execute") ? "处理中…" : `全部执行（${items.length}）`}
          </button>
        )}
      </div>

      {groups.map((g) => {
        const isCollapsed = collapsed[g.key] ?? false;
        const groupIds = g.items.map((d) => d.id);
        const allSelected = groupIds.length > 0 && groupIds.every((id) => selected.has(id));
        const someSelected = groupIds.some((id) => selected.has(id));
        const canBatchApprove = showReject && g.items.every((d) => d.status === "draft");
        const canBatchExecute = g.items.every((d) => d.status === "approved");

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
                {canBatchApprove && (
                  <button
                    type="button"
                    disabled={!!loading}
                    className="text-aims-positive"
                    onClick={() => batchAction(groupIds, "approve", g.label)}
                  >
                    本组批准
                  </button>
                )}
                {canBatchExecute && (
                  <button
                    type="button"
                    disabled={!!loading}
                    className="text-aims-accent"
                    onClick={() => batchAction(groupIds, "execute", g.label)}
                  >
                    本组执行
                  </button>
                )}
              </div>
            </div>
            {!isCollapsed && (
              <div className="p-2">
                <DecisionInboxTable
                  items={g.items}
                  showReject={showReject}
                  groupByRun={false}
                  selectedIds={selected}
                  onToggleSelect={(id) => setSelected((s) => toggleSetMember(s, id))}
                />
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
