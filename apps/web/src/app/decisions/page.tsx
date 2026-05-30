import Link from "next/link";
import { Card } from "@/components/Card";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

const actionColor: Record<string, string> = {
  buy: "text-aims-trade",
  add: "text-aims-trade",
  sell: "text-aims-negative",
  reduce: "text-aims-negative",
  hold: "text-gray-300",
  watch: "text-aims-research",
  ban: "text-red-400",
};

export default async function DecisionsPage() {
  const portfolios = await api.portfolios();
  const pid = portfolios[0]?.id;
  const decisions = await api.decisions(pid);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">决策日志</h1>
        <Link
          href="/decisions/new"
          className="rounded bg-aims-accent px-4 py-2 text-sm text-white"
        >
          新建决策
        </Link>
      </div>
      <p className="text-sm text-gray-400">
        系统护城河：记录 AI/人工为何调仓，以及假设与复盘条件。
      </p>

      <Card>
        <table className="w-full text-left text-sm">
          <thead className="text-gray-400">
            <tr>
              <th>标的</th>
              <th>动作</th>
              <th>仓位变化</th>
              <th>信心</th>
              <th>状态</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {decisions.map((d) => (
              <tr key={d.id} className="border-t border-aims-border">
                <td className="py-3">{d.name}</td>
                <td className={actionColor[d.action] || ""}>{d.action}</td>
                <td>
                  {d.current_weight_pct}% → {d.target_weight_pct}%
                </td>
                <td>{d.confidence_grade || "—"}</td>
                <td>{d.status}</td>
                <td>
                  <Link href={`/decisions/${d.id}`} className="text-aims-accent">
                    详情
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
