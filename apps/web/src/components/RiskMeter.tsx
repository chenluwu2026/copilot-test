import type { RiskDashboard } from "@/lib/api";

export function RiskMeter({ risk }: { risk: RiskDashboard }) {
  return (
    <div className="space-y-2 text-sm">
      <div className="flex justify-between">
        <span className="text-gray-400">现金占比</span>
        <span>{risk.cash_pct.toFixed(1)}% / 下限 {risk.limits.min_cash_pct ?? 5}%</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-400">单票上限</span>
        <span>{risk.limits.max_single_name_pct ?? 10}%</span>
      </div>
      {risk.alerts.length > 0 ? (
        <ul className="text-aims-negative">
          {risk.alerts.map((a, i) => (
            <li key={i}>
              {a.symbol} 权重 {a.weight_pct?.toFixed(1)}% 超限
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-aims-positive">风控通过</p>
      )}
    </div>
  );
}
