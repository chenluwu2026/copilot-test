import Link from "next/link";
import { Card } from "@/components/Card";
import { PortfolioWeightCompareChart } from "@/components/PortfolioWeightCompareChart";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function FmRunDetailPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  const portfolios = await api.portfolios();
  const p = portfolios[0];
  if (!p) return <p className="text-gray-400">暂无组合</p>;

  let detail: Awaited<ReturnType<typeof api.fmRun>> | null = null;
  try {
    detail = await api.fmRun(p.id, decodeURIComponent(runId));
  } catch {
    return (
      <div className="space-y-2">
        <p className="text-aims-negative">未找到批次 {runId}</p>
        <Link href="/fm/runs" className="text-aims-accent">
          ← 返回批次列表
        </Link>
      </div>
    );
  }

  const weightRows = detail.ledgers
    .map((l) => {
      const prop = l.proposal_json || {};
      return {
        security_id: l.security_id,
        symbol: String(prop.symbol || prop.security_symbol || l.security_id.slice(0, 8)),
        current_weight_pct: Number(prop.current_weight_pct ?? 0),
        target_weight_pct: Number(prop.target_weight_pct ?? 0),
      };
    })
    .filter((r) => r.target_weight_pct > 0 || r.current_weight_pct > 0);

  const gateEntries = Object.entries(detail.gate_failure_stats || {});

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-2xl font-bold">批次详情</h1>
        <Link href="/fm/runs" className="text-sm text-aims-accent">
          ← 批次列表
        </Link>
      </div>
      <p className="font-mono text-sm text-gray-400">{detail.run_id}</p>
      <p className="text-sm">
        <Link
          href={`/review?run_id=${encodeURIComponent(detail.run_id)}`}
          className="text-aims-accent underline"
        >
          在复盘页筛选本批次 →
        </Link>
        {" · "}
        <Link
          href={`/decisions/inbox?tab=draft`}
          className="text-gray-400 hover:text-aims-accent"
        >
          交易台收件箱
        </Link>
      </p>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="权重对比（账本提案）">
          <PortfolioWeightCompareChart targets={weightRows} />
        </Card>
        {gateEntries.length > 0 && (
          <Card title="风控门失败统计">
            <ul className="space-y-1 text-sm text-gray-300">
              {gateEntries.map(([gate, count]) => (
                <li key={gate} className="flex justify-between border-b border-aims-border py-1">
                  <span>{gate}</span>
                  <span>{count}</span>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>

      <Card title={`账本明细（${detail.ledger_count}）`}>
        <table className="w-full text-left text-sm">
          <thead className="text-gray-400">
            <tr>
              <th className="pb-2">状态</th>
              <th>目标%</th>
              <th>当前%</th>
              <th>风控</th>
              <th>决策</th>
            </tr>
          </thead>
          <tbody>
            {detail.ledgers.map((l) => {
              const prop = l.proposal_json || {};
              const risk = l.risk_result_json || {};
              const pm = l.postmortem_json || {};
              return (
                <tr key={l.id} className="border-t border-aims-border">
                  <td className="py-2">{l.status}</td>
                  <td>{Number(prop.target_weight_pct ?? 0).toFixed(2)}</td>
                  <td>{Number(prop.current_weight_pct ?? 0).toFixed(2)}</td>
                  <td>{risk.allowed === false ? "未过" : risk.allowed === true ? "通过" : "—"}</td>
                  <td>
                    {l.decision_id ? (
                      <Link href={`/decisions/${l.decision_id}`} className="text-aims-accent">
                        决策
                      </Link>
                    ) : (
                      "—"
                    )}
                    {pm.return_since_decision_pct != null && (
                      <span className="ml-2 text-xs text-gray-500">
                        复盘 {String(pm.return_since_decision_pct)}%
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
