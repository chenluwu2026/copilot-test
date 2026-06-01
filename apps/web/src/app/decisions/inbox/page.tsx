import Link from "next/link";
import { Card } from "@/components/Card";
import { DecisionInboxTable } from "@/components/DecisionInboxTable";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function DecisionInboxPage({
  searchParams,
}: {
  searchParams: { tab?: string };
}) {
  const portfolios = await api.portfolios();
  const pid = portfolios[0]?.id;
  const tab = searchParams.tab || "draft";

  let drafts: Awaited<ReturnType<typeof api.decisions>> = [];
  let approved: Awaited<ReturnType<typeof api.decisions>> = [];
  if (pid) {
    drafts = await api.decisions(pid, "draft");
    approved = await api.decisions(pid, "approved");
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">决策收件箱</h1>
        <Link href="/decisions" className="text-sm text-aims-accent">
          全部决策 →
        </Link>
      </div>
      <p className="text-sm text-gray-400">
        CIO 调仓产出为 draft，需批准后才可模拟成交。拒绝将标记为 cancelled。
      </p>

      <div className="flex gap-2 text-sm">
        <Link
          href="/decisions/inbox"
          className={tab === "draft" ? "text-aims-accent" : "text-gray-400"}
        >
          待批准 ({drafts.length})
        </Link>
        <Link
          href="/decisions/inbox?tab=approved"
          className={tab === "approved" ? "text-aims-accent" : "text-gray-400"}
        >
          待执行 ({approved.length})
        </Link>
      </div>

      <Card title={tab === "approved" ? "已批准 · 待成交" : "草案 · 待批准"}>
        <DecisionInboxTable
          items={tab === "approved" ? approved : drafts}
          showReject={tab !== "approved"}
        />
      </Card>
    </div>
  );
}
