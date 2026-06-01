import type { AgentConfig } from "@/lib/api";

export function AgentConfigPanel({ cfg }: { cfg: AgentConfig }) {
  const rows: { label: string; value: string }[] = [
    { label: "Agent 模式", value: cfg.agent_mode },
    { label: "结构化", value: cfg.structuring_mode },
    {
      label: "LLM",
      value: cfg.llm_active
        ? `已启用 · ${cfg.llm_model ?? "—"}`
        : cfg.llm_configured
          ? "已配置密钥（当前为 rule）"
          : "未配置 OPENAI_API_KEY",
    },
    { label: "CIO", value: cfg.cio_decision_mode ?? "batch" },
    {
      label: "事件→研究",
      value: cfg.event_research_refresh_enabled ? "开启" : "关闭",
    },
    {
      label: "数据定时",
      value: cfg.data_sync_cron_enabled ? "开启" : "关闭",
    },
    {
      label: "复盘定时",
      value: cfg.review_cron_enabled
        ? `开启 · ${cfg.review_cron_time ?? "20:00"}`
        : "关闭",
    },
    {
      label: "资讯定时",
      value: cfg.news_sync_cron_enabled
        ? `开启 · ${cfg.news_sync_cron_time ?? "09:00"}`
        : "关闭",
    },
    {
      label: "日报定时",
      value: cfg.daily_report_cron_enabled ? "开启" : "关闭",
    },
    {
      label: "登录口令",
      value: cfg.auth_password_configured ? "已配置 AUTH_PASSWORD" : "未配置",
    },
    {
      label: "Alembic",
      value: cfg.alembic_upgrade_on_start ? "启动时升级" : "关闭",
    },
  ];

  return (
    <section className="rounded-lg border border-aims-border bg-aims-card p-4 text-sm">
      <h2 className="text-sm font-medium text-gray-400">运行时配置（只读）</h2>
      <p className="mt-1 text-xs text-gray-500">
        通过 API 环境变量调整；详见 docs/USAGE.md 与 docs/CAPABILITY_ROADMAP.md。
      </p>
      <dl className="mt-3 grid gap-2 sm:grid-cols-2">
        {rows.map((r) => (
          <div key={r.label} className="flex justify-between gap-2 border-b border-aims-border/40 pb-1">
            <dt className="text-gray-500">{r.label}</dt>
            <dd className="text-right text-gray-200">{r.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
