"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export function EventResearchActions({
  eventId,
  symbols,
}: {
  eventId: string;
  symbols: string[];
}) {
  const router = useRouter();
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  async function refreshResearch() {
    setLoading(true);
    setMsg("");
    try {
      const res = await api.refreshEventResearch(eventId);
      setMsg(
        res.refreshed_symbols.length
          ? `已刷新研究：${res.refreshed_symbols.join(", ")}`
          : "无标的被刷新（可能为人工定稿或未过期）"
      );
      router.refresh();
    } catch (e) {
      setMsg(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2">
      <button
        type="button"
        disabled={loading}
        onClick={refreshResearch}
        className="rounded border border-aims-accent px-2 py-1 text-xs text-aims-accent disabled:opacity-50"
      >
        {loading ? "刷新中…" : "刷新相关研究"}
      </button>
      {symbols[0] && (
        <a
          href={`/research/${encodeURIComponent(symbols[0])}`}
          className="text-xs text-gray-400 hover:text-aims-accent"
        >
          研究页 →
        </a>
      )}
      {msg && <span className="text-xs text-gray-500">{msg}</span>}
    </div>
  );
}
