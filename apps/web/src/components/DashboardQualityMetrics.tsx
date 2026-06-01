import type { QualityMetrics } from "@/lib/api";

export function DashboardQualityMetrics({ metrics }: { metrics: QualityMetrics | null }) {
  if (!metrics) return null;
  return (
    <section className="rounded-lg border border-aims-border bg-aims-card p-4 text-sm">
      <h2 className="text-sm font-medium text-gray-400">决策成效（路线图指标）</h2>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <p className="text-xs text-gray-500">批准率</p>
          <p className="text-xl font-semibold">{metrics.approval_rate_pct}%</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">证据引用覆盖</p>
          <p className="text-xl font-semibold">{metrics.reference_coverage_pct}%</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">CIO LLM 占比</p>
          <p className="text-xl font-semibold">{metrics.llm_cio_run_pct}%</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">待批准草案</p>
          <p className="text-xl font-semibold">{metrics.draft_count}</p>
        </div>
      </div>
      <p className="mt-2 text-xs text-gray-500">{metrics.agent_mode_hint}</p>
    </section>
  );
}
