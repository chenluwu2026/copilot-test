import Link from "next/link";
import { Card } from "@/components/Card";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ReviewPage() {
  const portfolios = await api.portfolios();
  const pid = portfolios[0]?.id;
  let reportMd = "";
  if (pid) {
    try {
      const r = await api.dailyReport(pid);
      reportMd = r.summary_md;
    } catch {
      reportMd = "请确保 API 已启动";
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">复盘与日报</h1>
      <Card title="每日组合日报">
        <pre className="prose-aims whitespace-pre-wrap text-sm text-gray-300">{reportMd}</pre>
      </Card>
      <Card>
        <p className="text-sm text-gray-400">
          <span className="text-aims-research">Phase 4</span>：决策归因、memory_entries、策略规则库。
          现阶段请使用{" "}
          <Link href="/decisions" className="text-aims-accent">
            决策日志
          </Link>{" "}
          的用户反馈功能。
        </p>
      </Card>
    </div>
  );
}
