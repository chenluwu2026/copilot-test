"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { ResearchDetail } from "@/lib/api";
import { api } from "@/lib/api";

const sectionKeys = [
  "business_model",
  "industry_space",
  "competitive_landscape",
  "financial_quality",
  "management",
  "growth_drivers",
  "key_risks",
  "current_valuation",
] as const;

const sectionLabels: Record<string, string> = {
  business_model: "商业模式",
  industry_space: "行业空间",
  competitive_landscape: "竞争格局",
  financial_quality: "财务质量",
  management: "管理层",
  growth_drivers: "增长驱动",
  key_risks: "主要风险",
  current_valuation: "当前估值",
};

export function ResearchEditor({ data }: { data: ResearchDetail }) {
  const router = useRouter();
  const latest = data.latest;
  const fa0 = latest.fundamental_analysis;
  const [rating, setRating] = useState(latest.rating);
  const [horizon, setHorizon] = useState(latest.horizon || "6-12个月");
  const [conclusion, setConclusion] = useState(latest.investment_conclusion);
  const [fa, setFa] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const k of sectionKeys) {
      const v = fa0[k];
      init[k] = typeof v === "string" ? v : Array.isArray(v) ? v.join("\n") : "";
    }
    return init;
  });
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  async function save() {
    setLoading(true);
    setStatus("");
    try {
      const fundamental_analysis: Record<string, string | string[]> = { ...fa };
      const cv = fa0.core_variables_6_12m;
      if (cv) {
        fundamental_analysis.core_variables_6_12m = Array.isArray(cv) ? cv : [String(cv)];
      }
      await api.createResearch({
        security_id: data.security.id,
        rating,
        horizon,
        fundamental_analysis,
        investment_conclusion: conclusion,
        scenario_analysis: latest.scenario_analysis,
        valuation_snapshot: latest.valuation_snapshot,
      });
      setStatus("已保存为新版本研究观点");
      router.refresh();
    } catch (e) {
      setStatus(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-6 space-y-4 rounded border border-aims-border p-4">
      <h3 className="font-medium">编辑并定稿（保存为新版本）</h3>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">
          <span className="text-gray-400">评级</span>
          <select
            className="mt-1 w-full rounded border border-aims-border bg-aims-bg px-2 py-1"
            value={rating}
            onChange={(e) => setRating(e.target.value)}
          >
            {["strong_buy", "buy", "hold", "neutral", "reduce", "sell"].map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="text-gray-400">周期</span>
          <input
            className="mt-1 w-full rounded border border-aims-border bg-aims-bg px-2 py-1"
            value={horizon}
            onChange={(e) => setHorizon(e.target.value)}
          />
        </label>
      </div>
      <p className="text-xs text-gray-500">
        十段式空白段请补充要点；可先使用「生成研究草稿」，再人工定稿。加仓类决策需研究闸门通过。
      </p>
      {sectionKeys.map((k) => (
        <label key={k} className="block text-sm">
          <span className="text-gray-400">{sectionLabels[k]}</span>
          <textarea
            className="mt-1 min-h-[60px] w-full rounded border border-aims-border bg-aims-bg px-2 py-1"
            value={fa[k]}
            placeholder={`填写${sectionLabels[k]}…`}
            onChange={(e) => setFa({ ...fa, [k]: e.target.value })}
          />
        </label>
      ))}
      <label className="block text-sm">
        <span className="text-gray-400">投资结论</span>
        <textarea
          className="mt-1 min-h-[80px] w-full rounded border border-aims-border bg-aims-bg px-2 py-1"
          value={conclusion}
          onChange={(e) => setConclusion(e.target.value)}
        />
      </label>
      <button
        type="button"
        onClick={save}
        disabled={loading}
        className="rounded bg-aims-accent px-4 py-2 text-white disabled:opacity-50"
      >
        {loading ? "保存中…" : "保存定稿"}
      </button>
      {status && <p className="text-sm text-gray-400">{status}</p>}
    </div>
  );
}
