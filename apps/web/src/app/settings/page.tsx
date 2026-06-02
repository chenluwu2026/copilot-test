import { AgentConfigPanel } from "@/components/AgentConfigPanel";
import { Card } from "@/components/Card";
import { InvestmentProfileForm } from "@/components/InvestmentProfileForm";
import { ProfileSuggestionsPanel } from "@/components/ProfileSuggestionsPanel";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  let cfg: Awaited<ReturnType<typeof api.agentConfig>> | null = null;
  let health: Awaited<ReturnType<typeof api.agentConfigHealth>> | null = null;
  try {
    cfg = await api.agentConfig();
    health = await api.agentConfigHealth();
  } catch {
    cfg = null;
    health = null;
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold">投资画像</h1>
      <p className="text-sm text-gray-400">
        配置你的市场范围、风控上限与禁止项。保存后会同步到所有模拟组合的风控参数，并在 CIO
        调仓时注入记忆检索与研究闸门。
      </p>
      <Card title="方法论与约束">
        <InvestmentProfileForm />
      </Card>
      <Card title="反馈驱动的画像建议">
        <ProfileSuggestionsPanel />
      </Card>
      {cfg && <AgentConfigPanel cfg={cfg} />}
      {health && (
        <Card title="Agent 健康检查">
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div className="flex justify-between gap-2">
              <dt className="text-gray-500">LLM 已配置</dt>
              <dd>{health.llm_configured ? "是" : "否"}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-gray-500">LLM 运行中</dt>
              <dd className={health.llm_active ? "text-aims-positive" : "text-gray-400"}>
                {health.llm_active ? "是 (AGENT_MODE=llm)" : "否 (规则引擎)"}
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-gray-500">模型</dt>
              <dd>{health.llm_model}</dd>
            </div>
          </dl>
          <p className="mt-2 text-xs text-gray-500">
            启用 LLM 见 docs/DATA_AND_AGENTS.md 检查清单。
          </p>
        </Card>
      )}
    </div>
  );
}
