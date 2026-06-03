import Link from "next/link";
import { Card } from "@/components/Card";
import { PortfolioWeightCompareChart } from "@/components/PortfolioWeightCompareChart";
import { api } from "@/lib/api";

export async function PortfolioLatestFmTargets({ portfolioId }: { portfolioId: string }) {
  let latest: Awaited<ReturnType<typeof api.fmLatestTargets>> | null = null;
  try {
    latest = await api.fmLatestTargets(portfolioId);
  } catch {
    latest = null;
  }

  if (!latest?.run_id || !latest.targets.length) {
    return (
      <Card title="最新流水线目标权重">
        <p className="text-sm text-gray-500">
          尚未运行一日流水线。请前往{" "}
          <Link href="/" className="text-aims-accent underline">
            指挥中心
          </Link>{" "}
          运行后，此处将展示当前持仓与最新目标权重对比。
        </p>
      </Card>
    );
  }

  return (
    <Card title="最新流水线目标权重">
      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-gray-500">
        <span>
          批次 <code className="text-gray-400">{latest.run_id}</code>
        </span>
        {latest.created_at && <span>· {latest.created_at.replace("T", " ").slice(0, 19)}</span>}
        <span>· 拒单率 {latest.rejection_rate_pct}%</span>
        {latest.cash_target_pct != null && <span>· 目标现金 {latest.cash_target_pct}%</span>}
        <Link
          href={`/fm/runs/${encodeURIComponent(latest.run_id)}`}
          className="text-aims-accent underline"
        >
          批次详情 →
        </Link>
      </div>
      <PortfolioWeightCompareChart targets={latest.targets} maxBars={14} />
    </Card>
  );
}
