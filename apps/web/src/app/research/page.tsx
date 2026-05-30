import Link from "next/link";
import { Card } from "@/components/Card";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

const ratingLabel: Record<string, string> = {
  strong_buy: "强烈买入",
  buy: "买入",
  hold: "持有",
  reduce: "减持",
  sell: "卖出",
  neutral: "中性",
};

export default async function ResearchListPage() {
  let items: Awaited<ReturnType<typeof api.researchList>> = [];
  try {
    items = await api.researchList();
  } catch {
    items = [];
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">公司研究</h1>
      <p className="text-sm text-gray-400">
        <span className="text-aims-research">研究观点</span> 与{" "}
        <span className="text-aims-trade">交易动作</span> 分离；交易见决策日志。
      </p>

      <Card>
        <table className="w-full text-left text-sm">
          <thead className="text-gray-400">
            <tr>
              <th>公司</th>
              <th>行业</th>
              <th>评级</th>
              <th>版本</th>
              <th>结论摘要</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.symbol} className="border-t border-aims-border">
                <td className="py-3">
                  {r.name}
                  <span className="ml-1 text-gray-500">{r.symbol}</span>
                </td>
                <td>{r.sector || "—"}</td>
                <td>
                  <span className="text-aims-research">{ratingLabel[r.rating] || r.rating}</span>
                </td>
                <td>v{r.version}</td>
                <td className="max-w-xs truncate text-gray-400">{r.investment_conclusion}</td>
                <td>
                  <Link href={`/research/${encodeURIComponent(r.symbol)}`} className="text-aims-accent">
                    详情
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!items.length && (
          <p className="py-4 text-gray-500">
            暂无研究观点。进入公司页可「生成研究草稿」。
          </p>
        )}
      </Card>
    </div>
  );
}
