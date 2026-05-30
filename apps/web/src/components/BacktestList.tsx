"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { BacktestRow } from "@/lib/api";
import { api } from "@/lib/api";

export function BacktestList({ items }: { items: BacktestRow[] }) {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);

  async function promote(id: string) {
    setLoading(id);
    try {
      await api.promoteReviewMemory(id);
      router.refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(null);
    }
  }

  if (!items.length) return null;

  return (
    <ul className="mt-3 space-y-1 text-sm">
      {items.slice(0, 8).map((b) => (
        <li key={b.decision_id} className="flex flex-wrap items-center justify-between gap-2">
          <Link href={`/decisions/${b.decision_id}`} className="text-aims-accent">
            {b.symbol} {b.action}
            {b.price_source === "bars" && (
              <span className="ml-1 text-xs text-green-500">K线</span>
            )}
          </Link>
          <span className="flex items-center gap-2">
            <span className={b.return_pct >= 0 ? "text-aims-positive" : "text-aims-negative"}>
              {b.return_pct}%
            </span>
            <button
              type="button"
              onClick={() => promote(b.decision_id)}
              disabled={loading === b.decision_id}
              className="text-xs text-gray-400 hover:text-aims-accent"
            >
              记忆
            </button>
          </span>
        </li>
      ))}
    </ul>
  );
}
