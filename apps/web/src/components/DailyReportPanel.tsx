"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export function DailyReportPanel({
  portfolioId,
  initialMd,
}: {
  portfolioId: string;
  initialMd: string;
}) {
  const [md, setMd] = useState(initialMd);
  const [loading, setLoading] = useState(false);

  async function regenerate() {
    setLoading(true);
    try {
      const r = await api.dailyReport(portfolioId);
      setMd(r.summary_md);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={regenerate}
        disabled={loading}
        className="mb-2 text-xs text-aims-accent disabled:opacity-50"
      >
        {loading ? "生成中…" : "重新生成今日日报"}
      </button>
      <pre className="max-h-64 overflow-auto whitespace-pre-wrap text-xs text-gray-300">
        {md || "暂无日报，点击上方生成。"}
      </pre>
    </div>
  );
}
