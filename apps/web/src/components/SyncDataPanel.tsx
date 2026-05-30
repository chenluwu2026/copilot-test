"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export function SyncDataPanel() {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  async function run(kind: "quotes" | "filings" | "financials" | "all") {
    setLoading(kind);
    setMsg("");
    try {
      let res: Record<string, unknown>;
      if (kind === "quotes") res = await api.syncQuotes();
      else if (kind === "filings") res = await api.syncFilings();
      else if (kind === "financials") res = await api.syncFinancials();
      else res = await api.syncAll();
      setMsg(JSON.stringify(res, null, 0).slice(0, 200));
      router.refresh();
    } catch (e) {
      setMsg(String(e));
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="space-y-2 rounded border border-aims-border bg-aims-card p-4">
      <p className="text-sm font-medium">数据同步（AkShare）</p>
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => run("quotes")}
          disabled={!!loading}
          className="rounded bg-aims-accent px-3 py-2 text-sm text-white disabled:opacity-50"
        >
          {loading === "quotes" ? "同步中…" : "同步行情"}
        </button>
        <button
          onClick={() => run("filings")}
          disabled={!!loading}
          className="rounded border border-aims-border px-3 py-2 text-sm disabled:opacity-50"
        >
          {loading === "filings" ? "同步中…" : "同步公告"}
        </button>
        <button
          onClick={() => run("financials")}
          disabled={!!loading}
          className="rounded border border-aims-border px-3 py-2 text-sm disabled:opacity-50"
        >
          {loading === "financials" ? "同步中…" : "同步财报"}
        </button>
        <button
          onClick={() => run("all")}
          disabled={!!loading}
          className="rounded bg-aims-trade px-3 py-2 text-sm text-white disabled:opacity-50"
        >
          {loading === "all" ? "同步中…" : "一键全量"}
        </button>
      </div>
      {msg && <p className="text-xs text-gray-400 break-all">{msg}</p>}
    </div>
  );
}
