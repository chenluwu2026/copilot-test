"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import type { Decision } from "@/lib/api";
import { api } from "@/lib/api";
import { DecisionInboxTable } from "@/components/DecisionInboxTable";

type Group = {
  key: string;
  runId: string | null;
  label: string;
  items: Decision[];
};

function buildGroups(items: Decision[]): Group[] {
  const map = new Map<string, Decision[]>();
  for (const d of items) {
    const key = d.run_id || "__none__";
    const list = map.get(key) || [];
    list.push(d);
    map.set(key, list);
  }
  const groups: Group[] = [];
  for (const [key, list] of Array.from(map.entries())) {
    const runId = key === "__none__" ? null : key;
    groups.push({
      key,
      runId,
      label: runId ? `批次 ${runId}` : "其他（无 run_id）",
      items: list,
    });
  }
  groups.sort((a, b) => {
    if (a.runId && !b.runId) return -1;
    if (!a.runId && b.runId) return 1;
    if (a.runId && b.runId) return b.runId.localeCompare(a.runId);
    return 0;
  });
  return groups;
}

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

  const groups = useMemo(() => buildGroups(items), [items]);

  async function batchAction(group: Group, action: "approve" | "cancel" | "execute") {
    const label =
      action === "approve" ? "批准" : action === "cancel" ? "拒绝" : "执行";
    const ok = confirm(`对本组 ${group.items.length} 条决策全部「${label}」？`);
    if (!ok) return;
    setLoading(`${action}-${group.key}`);
    try {
      const res = await api.batchDecisionActions({
        decision_ids: group.items.map((d) => d.id),
        action,
      });
      alert(`完成：成功 ${res.succeeded}，失败 ${res.failed}`);
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

  const allDraft = items.every((d) => d.status === "draft");
  const allApproved = items.every((d) => d.status === "approved");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
        <span>按 run_id 分组 · 共 {groups.length} 组</span>
        {allDraft && items.length > 1 && (
          <button
            type="button"
            disabled={!!loading}
            className="rounded border border-aims-accent/50 px-2 py-1 text-aims-accent"
            onClick={async () => {
              setLoading("approve-all");
              await batchAction({ key: "all", runId: null, label: "", items }, "approve");
            }}
          >
            {loading === "approve-all" ? "处理中…" : `全部批准（${items.length}）`}
          </button>
        )}
        {allApproved && items.length > 1 && (
          <button
            type="button"
            disabled={!!loading}
            className="rounded border border-aims-accent/50 px-2 py-1 text-aims-accent"
            onClick={async () => {
              setLoading("execute-all");
              await batchAction({ key: "all", runId: null, label: "", items }, "execute");
            }}
          >
            {loading === "execute-all" ? "处理中…" : `全部执行（${items.length}）`}
          </button>
        )}
      </div>

      {groups.map((g) => {
        const isCollapsed = collapsed[g.key] ?? false;
        const canBatchApprove = showReject && g.items.every((d) => d.status === "draft");
        const canBatchExecute = g.items.every((d) => d.status === "approved");

        return (
          <section
            key={g.key}
            className="rounded-lg border border-aims-border/80 bg-aims-bg/30"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-aims-border/60 px-3 py-2">
              <button
                type="button"
                className="text-left text-sm font-medium text-gray-300"
                onClick={() => setCollapsed((c) => ({ ...c, [g.key]: !isCollapsed }))}
              >
                {isCollapsed ? "▸" : "▾"} {g.label}
                <span className="ml-2 text-xs text-gray-500">({g.items.length} 条)</span>
              </button>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                {g.runId && (
                  <Link
                    href={`/fm/runs/${encodeURIComponent(g.runId)}`}
                    className="text-aims-accent underline"
                  >
                    批次详情
                  </Link>
                )}
                {canBatchApprove && g.items.length > 0 && (
                  <button
                    type="button"
                    disabled={!!loading}
                    className="text-aims-positive"
                    onClick={() => batchAction(g, "approve")}
                  >
                    本组批准
                  </button>
                )}
                {canBatchExecute && g.items.length > 0 && (
                  <button
                    type="button"
                    disabled={!!loading}
                    className="text-aims-accent"
                    onClick={() => batchAction(g, "execute")}
                  >
                    本组执行
                  </button>
                )}
              </div>
            </div>
            {!isCollapsed && (
              <div className="p-2">
                <DecisionInboxTable items={g.items} showReject={showReject} groupByRun={false} />
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
