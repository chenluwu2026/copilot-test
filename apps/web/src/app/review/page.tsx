import Link from "next/link";
import { Card } from "@/components/Card";
import { AttributionChart } from "@/components/AttributionChart";
import { BacktestChart } from "@/components/BacktestChart";
import { BacktestList } from "@/components/BacktestList";
import { MemoryPanel } from "@/components/MemoryPanel";
import { ReviewBoard } from "@/components/ReviewBoard";
import { ReviewPendingMemoryPanel } from "@/components/ReviewPendingMemoryPanel";
import { ReviewSummaryBanner } from "@/components/ReviewSummaryBanner";
import { DailyReportPanel } from "@/components/DailyReportPanel";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ReviewPage() {
  const portfolios = await api.portfolios();
  const pid = portfolios[0]?.id;
  let reportMd = "";
  let open: Awaited<ReturnType<typeof api.openDecisions>> = [];
  let attribution = null;
  let backtest: Awaited<ReturnType<typeof api.backtest>> = [];
  let memories: Awaited<ReturnType<typeof api.memories>> = [];
  let runs: Awaited<ReturnType<typeof api.agentRuns>> = [];
  let reviewSummary: Awaited<ReturnType<typeof api.reviewSummary>> | null = null;
  let pendingMemories: Awaited<ReturnType<typeof api.pendingMemories>> = [];

  if (pid) {
    try {
      const r = await api.getDailyReport(pid);
      reportMd = r.summary_md;
    } catch {
      reportMd = "";
    }
    open = await api.openDecisions(pid);
    reviewSummary = await api.reviewSummary(pid);
    pendingMemories = await api.pendingMemories(pid);
    attribution = await api.attribution(pid);
    backtest = await api.backtest(pid);
    memories = await api.memories();
    runs = await api.agentRuns(pid);
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">复盘与进化</h1>

      <ReviewSummaryBanner summary={reviewSummary} />

      <Card title="待复盘决策 (Review Agent)">
        <ReviewBoard items={open} />
      </Card>

      <Card title="已复盘 · 待激活记忆">
        <p className="mb-3 text-xs text-gray-500">
          激活后的教训会在下次「生成 AI 调仓建议」时注入 CIO（可在 Agent 运行记录的 trace.memories 查看）。
        </p>
        <ReviewPendingMemoryPanel items={pendingMemories} />
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="行业归因">
          {attribution && <AttributionChart data={attribution} />}
          {attribution && (
            <p className="mt-2 text-xs text-gray-500">
              已复盘 {attribution.decision_stats.reviewed} 条 · 均收益{" "}
              {attribution.decision_stats.avg_return_pct}% · 胜率{" "}
              {attribution.decision_stats.win_rate_pct ?? 0}%
            </p>
          )}
        </Card>
        <Card title="决策复盘收益（真实 K 线）">
          <BacktestChart items={backtest} />
          <BacktestList items={backtest} />
        </Card>
      </div>

      <Card title="投资决策记忆库">
        <MemoryPanel memories={memories} />
      </Card>

      <Card title="Agent 运行记录">
        <ul className="space-y-2 text-sm">
          {runs.map((r) => (
            <li key={r.id} className="flex flex-wrap justify-between gap-2 border-b border-aims-border pb-2">
              <Link href={`/agents/${r.id}`} className="text-aims-accent">
                {r.workflow_name} · {r.status} · {r.started_at?.slice(0, 16)}
                {r.agent_mode ? ` · ${r.agent_mode}` : ""}
              </Link>
              <span className="text-gray-400">{r.decision_ids?.length || 0} 条决策</span>
            </li>
          ))}
          {!runs.length && <li className="text-gray-500">在组合页触发「生成 AI 调仓建议」</li>}
        </ul>
      </Card>

      {pid && (
        <Card title="每日组合日报">
          <DailyReportPanel portfolioId={pid} initialMd={reportMd} />
        </Card>
      )}
    </div>
  );
}
