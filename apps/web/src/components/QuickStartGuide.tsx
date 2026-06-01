import Link from "next/link";

const steps = [
  { n: 1, label: "画像与股票池", href: "/settings", hint: "风险预算、禁止项" },
  { n: 2, label: "全量同步", href: "/data", hint: "行情 / 公告 / 财报" },
  { n: 3, label: "维护研究", href: "/research", hint: "生成草稿 → 保存" },
  { n: 4, label: "生成调仓", href: "/portfolio", hint: "AI 调仓建议" },
  { n: 5, label: "收件箱批准", href: "/decisions/inbox", hint: "证据 A/B/C" },
  { n: 6, label: "复盘与记忆", href: "/review", hint: "闭环进化" },
];

export function QuickStartGuide() {
  return (
    <section className="rounded-lg border border-aims-border bg-aims-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-gray-400">推荐使用顺序</h2>
        <a
          href="https://github.com/chenluwu2026/copilot-test/blob/main/docs/USAGE.md"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-aims-accent hover:underline"
        >
          完整说明（USAGE.md）→
        </a>
      </div>
      <ol className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {steps.map((s) => (
          <li key={s.n}>
            <Link
              href={s.href}
              className="flex gap-2 rounded border border-transparent px-2 py-1.5 text-sm hover:border-aims-accent/40 hover:bg-aims-border/30"
            >
              <span className="font-mono text-aims-accent">{s.n}.</span>
              <span>
                <span className="text-gray-200">{s.label}</span>
                <span className="block text-xs text-gray-500">{s.hint}</span>
              </span>
            </Link>
          </li>
        ))}
      </ol>
      <p className="mt-2 text-xs text-gray-500">
        模拟盘：AI 仅产 draft，须在收件箱批准后再执行。LLM 需在 .env 设置 AGENT_MODE=llm。
      </p>
    </section>
  );
}
