import { Card } from "@/components/Card";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function PortfolioPage() {
  const portfolios = await api.portfolios();
  const p = portfolios[0];
  if (!p) return <p>暂无组合</p>;
  const summary = await api.portfolioSummary(p.id);
  const trades = await api.portfolioTrades(p.id);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">模拟组合 — {summary.name}</h1>
      <div className="grid gap-4 sm:grid-cols-3">
        <Card title="净值">
          <p className="text-xl">{summary.nav.toLocaleString("zh-CN")}</p>
        </Card>
        <Card title="现金">
          <p className="text-xl">{summary.cash.toLocaleString("zh-CN")}</p>
        </Card>
        <Card title="累计收益">
          <p className="text-xl">{summary.cumulative_return_pct.toFixed(2)}%</p>
        </Card>
      </div>

      <Card title="持仓">
        <table className="w-full text-left text-sm">
          <thead className="text-gray-400">
            <tr>
              <th className="pb-2">标的</th>
              <th>权重</th>
              <th>市值</th>
              <th>浮盈亏</th>
              <th>行业</th>
            </tr>
          </thead>
          <tbody>
            {summary.positions.map((pos) => (
              <tr key={pos.symbol} className="border-t border-aims-border">
                <td className="py-2">
                  {pos.name}
                  <span className="ml-1 text-gray-500">{pos.symbol}</span>
                </td>
                <td>{pos.weight_pct.toFixed(2)}%</td>
                <td>{pos.market_value.toLocaleString("zh-CN")}</td>
                <td
                  className={
                    pos.unrealized_pnl >= 0 ? "text-aims-positive" : "text-aims-negative"
                  }
                >
                  {pos.unrealized_pnl.toLocaleString("zh-CN")}
                </td>
                <td>{pos.sector || "—"}</td>
              </tr>
            ))}
            {!summary.positions.length && (
              <tr>
                <td colSpan={5} className="py-4 text-gray-500">
                  暂无持仓
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>

      <Card title="交易历史">
        <table className="w-full text-left text-sm">
          <thead className="text-gray-400">
            <tr>
              <th>日期</th>
              <th>标的</th>
              <th>方向</th>
              <th>数量</th>
              <th>价格</th>
              <th>金额</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t) => (
              <tr key={t.id} className="border-t border-aims-border">
                <td className="py-2">{t.trade_date}</td>
                <td>{t.name}</td>
                <td className={t.side === "buy" ? "text-aims-positive" : "text-aims-negative"}>
                  {t.side}
                </td>
                <td>{t.quantity}</td>
                <td>{t.price}</td>
                <td>{t.amount.toLocaleString("zh-CN")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
