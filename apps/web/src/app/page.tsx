import Link from "next/link";
import { NavChart } from "@/components/NavChart";
import { Card } from "@/components/Card";
import { DashboardActionCenter } from "@/components/DashboardActionCenter";
import { QuickStartGuide } from "@/components/QuickStartGuide";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const portfolios = await api.portfolios();
  const p = portfolios[0];
  if (!p) {
    return <p className="text-gray-400">暂无组合，请先启动 API 并完成种子初始化。</p>;
  }
  const summary = await api.portfolioSummary(p.id);
  let nav = await api.portfolioNav(p.id, 90);
  if (nav.length === 0) {
    await api.backfillNav(p.id);
    nav = await api.portfolioNav(p.id, 90);
  }
  const decisions = await api.decisions(p.id);
  let actions: Awaited<ReturnType<typeof api.dashboardActions>> | null = null;
  try {
    actions = await api.dashboardActions(p.id);
  } catch {
    actions = null;
  }
  let memories: { title: string; content: string }[] = [];
  try {
    const mem = await api.memories();
    memories = mem.filter((m) => m.active).slice(0, 2);
  } catch {
    memories = [];
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <QuickStartGuide />

      <section>
        <h2 className="mb-2 text-sm font-medium text-gray-400">今日待办</h2>
        <DashboardActionCenter actions={actions} />
      </section>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card title="组合净值">
          <p className="text-2xl font-semibold">{summary.nav.toLocaleString("zh-CN")}</p>
        </Card>
        <Card title="累计收益">
          <p
            className={`text-2xl font-semibold ${
              summary.cumulative_return_pct >= 0 ? "text-aims-positive" : "text-aims-negative"
            }`}
          >
            {summary.cumulative_return_pct.toFixed(2)}%
          </p>
        </Card>
        <Card title="现金占比">
          <p className="text-2xl font-semibold">{summary.cash_pct.toFixed(1)}%</p>
        </Card>
        <Card title="持仓数">
          <p className="text-2xl font-semibold">{summary.position_count}</p>
        </Card>
      </div>

      <Card title="净值曲线">
        <NavChart data={nav} />
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="最新决策">
          <ul className="space-y-2 text-sm">
            {decisions.slice(0, 5).map((d) => (
              <li key={d.id} className="flex justify-between border-b border-aims-border pb-2">
                <span>
                  <span className="text-aims-trade">{d.action}</span> {d.name}
                </span>
                <Link href={`/decisions/${d.id}`} className="text-aims-accent">
                  {d.status}
                </Link>
              </li>
            ))}
          </ul>
          <Link href="/decisions" className="mt-2 inline-block text-sm text-aims-accent">
            查看全部 →
          </Link>
        </Card>
        <Card title="Top 持仓">
          <ul className="space-y-1 text-sm">
            {summary.positions.slice(0, 6).map((pos) => (
              <li key={pos.symbol} className="flex justify-between">
                <span>{pos.name}</span>
                <span>{pos.weight_pct.toFixed(1)}%</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="投资记忆">
          <ul className="space-y-2 text-sm text-gray-300">
            {memories.map((m) => (
              <li key={m.title}>
                <span className="font-medium text-aims-accent">{m.title}</span>
                <p className="text-xs text-gray-500">{m.content.slice(0, 80)}…</p>
              </li>
            ))}
            {!memories.length && (
              <li>
                <Link href="/review" className="text-aims-accent">
                  前往复盘页查看记忆库 →
                </Link>
              </li>
            )}
          </ul>
        </Card>
      </div>
    </div>
  );
}
