"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { Decision } from "@/lib/api";
import { Card } from "@/components/Card";
import { DecisionInboxGrouped } from "@/components/DecisionInboxGrouped";
import { idsToSet, loadInboxSelection, type InboxTab } from "@/lib/inboxSelection";

export function DecisionInboxClient({
  tab,
  drafts,
  approved,
}: {
  tab: InboxTab;
  drafts: Decision[];
  approved: Decision[];
}) {
  const [mounted, setMounted] = useState(false);
  const [selectionCounts, setSelectionCounts] = useState({ draft: 0, approved: 0 });

  useEffect(() => {
    setMounted(true);
    const s = loadInboxSelection();
    setSelectionCounts({ draft: s.draft.length, approved: s.approved.length });
  }, []);

  function onSelectionChange(t: InboxTab, ids: string[]) {
    setSelectionCounts((c) => ({ ...c, [t]: ids.length }));
  }

  const items = tab === "approved" ? approved : drafts;
  const initialSelected = mounted ? idsToSet(loadInboxSelection()[tab]) : new Set<string>();

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">决策收件箱</h1>
        <Link href="/decisions" className="text-sm text-aims-accent">
          全部决策 →
        </Link>
      </div>
      <p className="text-sm text-gray-400">
        CIO 调仓产出为 draft，需批准后才可模拟成交。勾选在 Tab 间保留（本会话）。
      </p>

      <div className="flex flex-wrap gap-2 text-sm">
        <Link
          href="/decisions/inbox"
          className={tab === "draft" ? "text-aims-accent" : "text-gray-400"}
        >
          待批准 ({drafts.length})
          {selectionCounts.draft > 0 && tab !== "draft" && (
            <span className="ml-1 text-xs text-aims-research">· 已选 {selectionCounts.draft}</span>
          )}
        </Link>
        <Link
          href="/decisions/inbox?tab=approved"
          className={tab === "approved" ? "text-aims-accent" : "text-gray-400"}
        >
          待执行 ({approved.length})
          {selectionCounts.approved > 0 && tab !== "approved" && (
            <span className="ml-1 text-xs text-aims-research">
              · 已选 {selectionCounts.approved}
            </span>
          )}
        </Link>
      </div>

      <Card title={tab === "approved" ? "已批准 · 待成交" : "草案 · 待批准"}>
        <DecisionInboxGrouped
          key={`${tab}-${mounted}`}
          items={items}
          showReject={tab !== "approved"}
          selectionTab={tab}
          initialSelected={initialSelected}
          onSelectionChange={onSelectionChange}
        />
      </Card>
    </div>
  );
}
