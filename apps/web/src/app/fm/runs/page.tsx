import { Card } from "@/components/Card";
import { FmRunsPanel } from "@/components/FmRunsPanel";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function FmRunsPage() {
  const portfolios = await api.portfolios();
  const p = portfolios[0];
  if (!p) return <p className="text-gray-400">暂无组合</p>;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">流水线批次（run_id）</h1>
      <p className="text-sm text-gray-500">
        每次「运行一日流水线」会生成唯一 run_id，下方为各批次的账本汇总与拒单率。
      </p>
      <Card title="批次列表">
        <FmRunsPanel portfolioId={p.id} />
      </Card>
    </div>
  );
}
