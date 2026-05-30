import Link from "next/link";
import { Card } from "@/components/Card";
import { AttributionChart } from "@/components/AttributionChart";
import { MemoryPanel } from "@/components/MemoryPanel";
import { ReviewBoard } from "@/components/ReviewBoard";
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

  if (pid) {
    try {
      const r = await api.dailyReport(pid);
      reportMd = r.summary_md;
    } catch {
      reportMd = "";
    }
    open = await api.openDecisions(pid);
    attribution = await api.attribution(pid);
    backtest = await api.backtest(pid);
    memories = await api.memories();
    runs = await api.agentRuns(pid);
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">复盘与进化</h1>

      <Card title="待复盘决策 (Review Agent)">
        <ReviewBoard items={open} />
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="行业归因">
          {attribution && <AttributionChart data={attribution} />}
          {attribution && (
            <p className="mt-2 text-xs text-gray-500">
              已复盘决策 {attribution.decision_stats.reviewed} 条，平均收益{" "}
              {attribution.decision_stats.avg_return_pct}%
            </p>
          )}
        </Card>
        <Card title="决策回测（简化）">
          <ul className="space-y-1 text-sm">
            {backtest.map((b) => (
              <li key={b.decision_id} className="flex justify-between">
                <Link href={`/decisions/${b.decision_id}`} className="text-aims-accent">
                  {b.decision_id.slice(0, 8)}…
                </Link>
                <span
                  className={
                    b.return_pct >= 0 ? "text-aims-positive" : "text-aims-negative"
                  }
                >
                  {b.return_pct}%
                </span>
              </li>
            ))}
            {!backtest.length && (
              <li className="text-gray-500">运行复盘后显示历史决策收益</li>
            )}
          </ul>
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

      <Card title="每日组合日报">
        <pre className="whitespace-pre-wrap text-sm text-gray-300">{reportMd}</pre>
      </Card>
    </div>
  );
}
