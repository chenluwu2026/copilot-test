"use client";

import Link from "next/link";
import { useState } from "react";
import { PortfolioWeightCompareChart } from "@/components/PortfolioWeightCompareChart";
import { api, type FmDailyRunResponse } from "@/lib/api";

export function FundManagerConsole({
  portfolioId,
  initialDrafts,
  initialApproved,
}: {
  portfolioId: string;
  initialDrafts: number;
  initialApproved: number;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<FmDailyRunResponse | null>(null);
  const [autoApprove, setAutoApprove] = useState(false);
  const [autoSimulate, setAutoSimulate] = useState(false);

  async function runDaily() {
    setLoading(true);
    setError("");
    try {
      const out = await api.fmDailyRun({
        portfolio_id: portfolioId,
        max_turnover_pct: 30,
        auto_approve: autoApprove,
        auto_execute_simulated: autoSimulate,
        simulated_fill_ratio: 0.7,
      });
      setResult(out);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const pipeline = result?.pipeline;

  return (
    <section className="rounded-lg border border-aims-accent/40 bg-aims-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-aims-accent">基金经理控制台</h2>
        <div className="flex gap-3 text-xs text-gray-400">
          <span>待批准 {initialDrafts}</span>
          <span>待执行 {initialApproved}</span>
        </div>
      </div>
      <p className="mt-1 text-xs text-gray-500">
        一键：数据检查 → 股票池候选 → 目标权重 → 风控 → 建单（可选自动审批/模拟执行）
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={autoApprove} onChange={(e) => setAutoApprove(e.target.checked)} />
          自动审批
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={autoSimulate} onChange={(e) => setAutoSimulate(e.target.checked)} />
          自动模拟执行
        </label>
        <button
          type="button"
          onClick={runDaily}
          disabled={loading}
          className="rounded bg-aims-accent px-4 py-2 text-white disabled:opacity-50"
        >
          {loading ? "运行中…" : "运行一日流水线"}
        </button>
        <Link href="/decisions/inbox" className="text-aims-research underline">
          前往收件箱 →
        </Link>
        <Link href="/fm/runs" className="text-aims-accent underline">
          批次账本 →
        </Link>
      </div>
      {error && <p className="mt-2 text-sm text-aims-negative">{error}</p>}
      {result && (
        <div className="mt-3 space-y-2 text-sm">
          <p className="text-gray-300">
            run_id: <code className="text-xs">{result.run_id}</code> · 候选 {result.candidate_count} · 建单{" "}
            {result.counts.created_decisions} · 未过 {result.counts.rejected} · fallback{" "}
            {result.counts.fallback_applied}
          </p>
          <p className="text-xs text-gray-500">
            数据覆盖 {result.data_readiness.coverage_pct}% · 陈旧/缺失{" "}
            {result.data_readiness.stale_or_missing_symbols}
          </p>
          {pipeline?.targets?.length ? (
            <PortfolioWeightCompareChart targets={pipeline.targets} maxBars={10} />
          ) : null}
          {result.run_id && (
            <p className="text-xs">
              <Link
                href={`/fm/runs/${encodeURIComponent(result.run_id)}`}
                className="text-aims-accent underline"
              >
                查看本批次账本详情 →
              </Link>
            </p>
          )}
          {pipeline?.results?.length ? (
            <ul className="max-h-48 space-y-1 overflow-y-auto text-xs text-gray-400">
              {pipeline.results.map((r) => (
                <li key={r.security_id}>
                  {r.symbol || r.security_id}: {r.allowed ? "通过" : "未过"} · {r.action} · 目标{" "}
                  {r.target_weight_pct}%
                  {r.decision_id && (
                    <>
                      {" "}
                      · <Link href={`/decisions/${r.decision_id}`} className="text-aims-accent">详情</Link>
                    </>
                  )}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      )}
    </section>
  );
}
