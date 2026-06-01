"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { DashboardActions } from "@/lib/api";
import { api } from "@/lib/api";

type Todo = NonNullable<DashboardActions["event_review_todos"]>[number];

export function DashboardEventReview({
  todos,
  portfolioId,
}: {
  todos: Todo[];
  portfolioId: string;
}) {
  const router = useRouter();
  const [loadingId, setLoadingId] = useState<string | null>(null);

  if (!todos.length) return null;

  async function onRefreshResearch(eventId: string) {
    setLoadingId(eventId);
    try {
      await api.refreshEventResearch(eventId);
      router.refresh();
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <section className="rounded-lg border border-yellow-600/40 bg-yellow-900/10 p-4">
      <h2 className="text-sm font-medium text-yellow-400">事件复审（24h）</h2>
      <ul className="mt-2 space-y-2 text-sm">
        {todos.map((t) => (
          <li key={t.event_id} className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <span className="text-aims-accent">{t.symbols.join(", ")}</span>
              <span className="ml-2 text-xs text-gray-500">{t.impact_direction}</span>
              <p className="text-xs text-gray-400">{t.summary}</p>
            </div>
            <div className="flex shrink-0 gap-2">
              <button
                type="button"
                disabled={loadingId === t.event_id}
                onClick={() => onRefreshResearch(t.event_id)}
                className="text-xs text-aims-accent"
              >
                刷新研究
              </button>
              <Link href={`/events?highlight=${t.event_id}`} className="text-xs text-gray-400">
                详情
              </Link>
              <button
                type="button"
                className="text-xs text-aims-trade"
                onClick={() => {
                  api
                    .runRebalance(portfolioId)
                    .then(() => router.push("/decisions/inbox"))
                    .catch((e) => alert(String(e)));
                }}
              >
                调仓草案
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
