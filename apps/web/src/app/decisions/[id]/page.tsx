import { DecisionActions } from "@/components/DecisionActions";
import { AdvancedFold } from "@/components/AdvancedFold";
import { DecisionProvenancePanel } from "@/components/DecisionProvenancePanel";
import { DecisionCoveragePanel } from "@/components/DecisionCoveragePanel";
import { DecisionTimelinePanel } from "@/components/DecisionTimeline";
import Link from "next/link";
import { DecisionLedgerPanel } from "@/components/DecisionLedgerPanel";
import { Card } from "@/components/Card";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function DecisionDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const d = await api.decision(params.id);
  const portfolios = await api.portfolios();
  let provenance: Awaited<ReturnType<typeof api.decisionProvenance>> | null = null;
  try {
    provenance = await api.decisionProvenance(params.id);
  } catch {
    provenance = null;
  }
  let timeline: Awaited<ReturnType<typeof api.decisionTimeline>> | null = null;
  try {
    timeline = await api.decisionTimeline(params.id);
  } catch {
    timeline = null;
  }
  let coverage: Awaited<ReturnType<typeof api.decisionCoverage>> | null = null;
  try {
    coverage = await api.decisionCoverage(params.id);
  } catch {
    coverage = null;
  }
  let ledger: Awaited<ReturnType<typeof api.decisionLedger>> | null = null;
  try {
    ledger = await api.decisionLedger(params.id);
  } catch {
    ledger = null;
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">
        {d.name}{" "}
        <span className="text-aims-trade text-lg">({d.action})</span>
      </h1>
      <div className="flex flex-wrap gap-2 text-sm">
        <span className="rounded bg-aims-border px-2 py-1">状态: {d.status}</span>
        <span className="rounded bg-aims-border px-2 py-1">
          仓位: {d.current_weight_pct}% → {d.target_weight_pct}%
        </span>
        {d.confidence_grade && (
          <span className="rounded bg-aims-border px-2 py-1">信心: {d.confidence_grade}</span>
        )}
        {d.holding_period && (
          <span className="rounded bg-aims-border px-2 py-1">周期: {d.holding_period}</span>
        )}
        {d.created_by_agent && (
          <span className="rounded bg-aims-border px-2 py-1">来源: {d.created_by_agent}</span>
        )}
        {d.run_id && (
          <Link
            href={`/fm/runs/${encodeURIComponent(d.run_id)}`}
            className="rounded bg-aims-border px-2 py-1 text-aims-accent hover:underline"
          >
            批次 {d.run_id}
          </Link>
        )}
        {d.ledger_status && (
          <span className="rounded bg-aims-border px-2 py-1">账本: {d.ledger_status}</span>
        )}
      </div>

      <DecisionLedgerPanel ledger={ledger} />

      <Card title="决策理由">
        <p className="text-sm leading-relaxed">{d.decision_reason}</p>
      </Card>

      <Card title="核心假设">
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {d.assumptions.map((a, i) => (
            <li key={i}>
              {a.text}
              {a.measurable && (
                <span className="ml-2 text-xs text-aims-research">可验证</span>
              )}
            </li>
          ))}
        </ul>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="主要风险">
          <ul className="list-disc pl-5 text-sm text-aims-negative">
            {d.main_risks.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </Card>
        <Card title="复盘 / 止损条件（假设驱动）">
          <ul className="list-disc pl-5 text-sm">
            {d.review_conditions.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </Card>
      </div>

      {d.references.length > 0 && (
        <Card title="参考信息">
          <ul className="space-y-2 text-sm">
            {d.references.map((r, i) => (
              <li key={i} className="border-l-2 border-aims-accent pl-3">
                <span className="text-gray-400">[{r.ref_type}]</span> {r.excerpt}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <DecisionTimelinePanel timeline={timeline} />

      {coverage && (
        <Card title="卷宗 vs CIO 对照">
          <DecisionCoveragePanel data={coverage} />
        </Card>
      )}

      <AdvancedFold title="决策溯源（Agent / 记忆 / 闸门）" defaultOpen>
        <DecisionProvenancePanel data={provenance} />
      </AdvancedFold>

      <DecisionActions
        decisionId={d.id}
        status={d.status}
        action={d.action}
        portfolioId={portfolios[0]?.id || ""}
      />
    </div>
  );
}
