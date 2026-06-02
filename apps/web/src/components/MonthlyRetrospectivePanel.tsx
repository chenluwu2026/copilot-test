"use client";

import { useState } from "react";
import type { MonthlyRetrospective } from "@/lib/api";
import { api } from "@/lib/api";

export function MonthlyRetrospectivePanel({ portfolioId }: { portfolioId: string }) {
  const [data, setData] = useState<MonthlyRetrospective | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const r = await api.monthlyRetrospective(portfolioId);
      setData(r);
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={load}
        disabled={loading}
        className="rounded bg-aims-trade px-3 py-1 text-sm text-white disabled:opacity-50"
      >
        {loading ? "生成中…" : "生成月度复盘 Markdown"}
      </button>
      {data && (
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded border border-aims-border bg-black/20 p-3 text-xs">
          {data.summary_md}
        </pre>
      )}
    </div>
  );
}
