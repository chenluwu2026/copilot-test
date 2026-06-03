import type { QualityMetrics } from "@/lib/api";

export function DashboardQualityMetrics({ metrics }: { metrics: QualityMetrics | null }) {
  if (!metrics) return null;
  const alerts = metrics.drift_alerts ?? [];
  return (
    <section className="rounded-lg border border-aims-border bg-aims-card p-4 text-sm">
      <h2 className="text-sm font-medium text-gray-400">决策成效与策略漂移</h2>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
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
        <div>
          <p className="text-xs text-gray-500">流水线拒单率</p>
          <p
            className={`text-xl font-semibold ${
              (metrics.pipeline_rejection_rate_pct ?? 0) >= 40 ? "text-aims-negative" : ""
            }`}
          >
            {metrics.pipeline_rejection_rate_pct ?? 0}%
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">平均权重偏离</p>
          <p className="text-xl font-semibold">{metrics.avg_weight_drift_pct ?? 0}%</p>
        </div>
      </div>
      {alerts.length > 0 && (
        <ul className="mt-3 space-y-1 rounded border border-aims-border/60 bg-aims-bg/40 p-2 text-xs">
          {alerts.map((a) => (
            <li
              key={a.code}
              className={a.level === "warning" ? "text-aims-negative" : "text-amber-200/90"}
            >
              {a.message}
            </li>
          ))}
        </ul>
      )}
      <p className="mt-2 text-xs text-gray-500">{metrics.agent_mode_hint}</p>
    </section>
  );
}
