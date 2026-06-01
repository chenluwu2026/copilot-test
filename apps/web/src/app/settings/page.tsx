import { Card } from "@/components/Card";
import { InvestmentProfileForm } from "@/components/InvestmentProfileForm";
import { ProfileSuggestionsPanel } from "@/components/ProfileSuggestionsPanel";

export const dynamic = "force-dynamic";

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold">投资画像</h1>
      <p className="text-sm text-gray-400">
        配置你的市场范围、风控上限与禁止项。保存后会同步到所有模拟组合的风控参数，并在 CIO
        调仓时注入记忆检索与研究闸门。
      </p>
      <Card title="方法论与约束">
        <InvestmentProfileForm />
      </Card>
      <Card title="反馈驱动的画像建议">
        <ProfileSuggestionsPanel />
      </Card>
    </div>
  );
}
