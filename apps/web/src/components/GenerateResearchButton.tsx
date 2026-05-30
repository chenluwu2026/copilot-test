"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export function GenerateResearchButton({
  securityId,
  symbol,
}: {
  securityId: string;
  symbol: string;
}) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function generate() {
    setLoading(true);
    try {
      await api.generateResearchDraft(securityId);
      router.refresh();
      router.push(`/research/${encodeURIComponent(symbol)}`);
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={generate}
      disabled={loading}
      className="rounded bg-aims-research px-3 py-1 text-sm text-white disabled:opacity-50"
    >
      {loading ? "生成中…" : "生成研究草稿"}
    </button>
  );
}
