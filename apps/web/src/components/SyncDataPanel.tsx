"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export function SyncDataPanel() {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  async function pollJob(jobId: string) {
    for (let i = 0; i < 60; i++) {
      await new Promise((r) => setTimeout(r, 3000));
      const j = await api.syncJob(jobId);
      if (j.status !== "running") {
        setMsg(`作业 ${j.status}: ${JSON.stringify(j.result || j.error_message).slice(0, 180)}`);
        router.refresh();
        return;
      }
      setMsg(`后台同步中… (${i + 1}/60)`);
    }
    setMsg("同步时间较长，请稍后在「最近同步作业」查看");
    router.refresh();
  }

  async function run(
    kind: "quotes" | "filings" | "financials" | "news" | "all" | "all_async"
  ) {
    setLoading(kind);
    setMsg("");
    try {
      let res: Record<string, unknown>;
      if (kind === "quotes") res = await api.syncQuotes();
      else if (kind === "filings") res = await api.syncFilings();
      else if (kind === "financials") res = await api.syncFinancials();
      else if (kind === "news") res = await api.syncNews();
      else if (kind === "all_async") {
        res = await api.syncAllAsync();
        const jobId = res.job_id as string;
        if (jobId) await pollJob(jobId);
        return;
      } else res = await api.syncAll();
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
          onClick={() => run("news")}
          disabled={!!loading}
          className="rounded border border-aims-border px-3 py-2 text-sm disabled:opacity-50"
        >
          {loading === "news" ? "同步中…" : "同步资讯"}
        </button>
        <button
          onClick={() => run("all")}
          disabled={!!loading}
          className="rounded bg-aims-trade px-3 py-2 text-sm text-white disabled:opacity-50"
        >
          {loading === "all" ? "同步中…" : "一键全量"}
        </button>
        <button
          onClick={() => run("all_async")}
          disabled={!!loading}
          className="rounded border border-aims-trade px-3 py-2 text-sm text-aims-trade disabled:opacity-50"
        >
          {loading === "all_async" ? "后台同步…" : "后台全量"}
        </button>
      </div>
      {msg && <p className="text-xs text-gray-400 break-all">{msg}</p>}
    </div>
  );
}
