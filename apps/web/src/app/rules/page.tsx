import { Card } from "@/components/Card";
import { RulesPanel } from "@/components/RulesPanel";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function RulesPage() {
  let rules: Awaited<ReturnType<typeof api.rules>> = [];
  try {
    rules = await api.rules();
  } catch {
    rules = [];
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">策略规则</h1>
      <p className="text-sm text-gray-400">
        与 Risk Agent 联动。从复盘激活 anti_pattern 记忆时会自动生成带 sectors 的 ban 规则。
      </p>
      <Card title="规则库">
        <RulesPanel rules={rules} />
      </Card>
    </div>
  );
}
