import { Card } from "@/components/Card";
import type { DecisionLedger } from "@/lib/api";

export function DecisionLedgerPanel({ ledger }: { ledger: DecisionLedger | null }) {
  if (!ledger) return null;

  const plan = ledger.execution_plan_json || {};
  const risk = ledger.risk_result_json || {};
  const exec = ledger.execution_result_json || {};

  return (
    <Card title="决策账本（Ledger）">
      <div className="space-y-2 text-sm text-gray-300">
        <p>
          状态 <strong>{ledger.status}</strong>
          {ledger.run_id && (
            <>
              {" "}
              · run <code className="text-xs text-gray-500">{ledger.run_id}</code>
            </>
          )}
        </p>
        {risk.allowed != null && (
          <p>
            风控：{risk.allowed ? "通过" : "未通过"}
            {Array.isArray(risk.failed_gates) && risk.failed_gates.length > 0 && (
              <span className="text-gray-500">（{risk.failed_gates.join(", ")}）</span>
            )}
          </p>
        )}
        {plan.order_notional != null && (
          <p>
            执行计划：名义 {Number(plan.order_notional).toLocaleString()} · 滑点{" "}
            {String(plan.estimated_slippage_bps ?? "—")} bps · 节奏{" "}
            {String((plan.schedule as { style?: string } | undefined)?.style ?? "—")}
          </p>
        )}
        {exec.mode != null && (
          <p>
            执行结果（{String(exec.mode)}）：成交价 {String(exec.executed_price ?? "—")} · 成交比例{" "}
            {String(exec.fill_ratio ?? "—")}
          </p>
        )}
      </div>
    </Card>
  );
}
