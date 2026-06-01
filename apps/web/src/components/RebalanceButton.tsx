"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export function RebalanceButton({ portfolioId }: { portfolioId: string }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  async function run() {
    setLoading(true);
    setMsg("");
    try {
      const res = await api.runRebalance(portfolioId);
      setMsg(`已生成 ${res.decision_ids.length} 条决策草稿`);
      router.push("/decisions/inbox");
      router.refresh();
    } catch (e) {
      setMsg(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <button
        onClick={run}
        disabled={loading}
        className="rounded bg-aims-trade px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {loading ? "Agent 运行中…" : "生成 AI 调仓建议"}
      </button>
      {msg && <p className="mt-1 text-xs text-gray-400">{msg}</p>}
    </div>
  );
}
