import Link from "next/link";
import { Card } from "@/components/Card";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AgentsPage() {
  const portfolios = await api.portfolios();
  const pid = portfolios[0]?.id;
  const runs = pid ? await api.agentRuns(pid) : [];
  let cfg: Awaited<ReturnType<typeof api.agentConfig>> | null = null;
  try {
    cfg = await api.agentConfig();
  } catch {
    cfg = null;
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Agent 运行</h1>
      {cfg && (
        <p className="text-sm text-gray-400">
          模式 {cfg.agent_mode}
          {cfg.llm_active ? ` · LLM ${cfg.llm_model}` : ""} · CIO {cfg.cio_decision_mode} ·
          事件→研究 {cfg.event_research_refresh_enabled ? "开" : "关"}
        </p>
      )}
      <Card title="最近工作流">
        <ul className="space-y-2 text-sm">
          {runs.map((r) => (
            <li key={r.id} className="flex justify-between border-b border-aims-border pb-2">
              <Link href={`/agents/${r.id}`} className="text-aims-accent">
                {r.workflow_name} · {r.status}
              </Link>
              <span className="text-gray-500">{r.decision_ids?.length ?? 0} 决策</span>
            </li>
          ))}
          {!runs.length && (
            <li className="text-gray-500">尚无记录，请先在组合页生成 AI 调仓建议。</li>
          )}
        </ul>
      </Card>
      {pid && (
        <p className="text-xs text-gray-500">
          <Link href="/portfolio" className="text-aims-accent">
            前往组合页触发调仓 →
          </Link>
        </p>
      )}
    </div>
  );
}
