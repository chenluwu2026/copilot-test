import Link from "next/link";
import { Card } from "@/components/Card";
import { StructuredEventCard } from "@/components/StructuredEventCard";
import { GenerateResearchButton } from "@/components/GenerateResearchButton";
import { ResearchEditor } from "@/components/ResearchEditor";
import { PriceChart } from "@/components/PriceChart";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

const sections: { key: string; label: string }[] = [
  { key: "business_model", label: "商业模式" },
  { key: "industry_space", label: "行业空间" },
  { key: "competitive_landscape", label: "竞争格局" },
  { key: "financial_quality", label: "财务质量" },
  { key: "management", label: "管理层" },
  { key: "growth_drivers", label: "增长驱动" },
  { key: "key_risks", label: "主要风险" },
  { key: "current_valuation", label: "当前估值" },
];

const ratingLabel: Record<string, string> = {
  strong_buy: "强烈买入",
  buy: "买入",
  hold: "持有",
  reduce: "减持",
  sell: "卖出",
  neutral: "中性",
};

function formatMetric(v: number | null | undefined): string {
  if (v == null) return "—";
  if (Math.abs(v) >= 1e8) return `${(v / 1e8).toFixed(2)}亿`;
  if (Math.abs(v) >= 1e4) return `${(v / 1e4).toFixed(2)}万`;
  return v.toFixed(2);
}

const scenarioLabel: Record<string, string> = {
  optimistic: "乐观",
  base: "中性",
  pessimistic: "悲观",
};

export default async function ResearchDetailPage({
  params,
}: {
  params: { symbol: string };
}) {
  const symbol = decodeURIComponent(params.symbol);
  let data: Awaited<ReturnType<typeof api.researchBySymbol>> | null = null;
  try {
    data = await api.researchBySymbol(symbol);
  } catch {
    data = null;
  }

  if (!data) {
    const securities = await api.securities(symbol);
    const sec = securities.find((s) => s.symbol === symbol);
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">{symbol}</h1>
        <p className="text-gray-400">暂无研究观点。</p>
        {sec && <GenerateResearchButton securityId={sec.id} symbol={symbol} />}
      </div>
    );
  }

  const { security, latest, history, related_events } = data;
  const fa = latest.fundamental_analysis;
  const scenarios = latest.scenario_analysis?.scenarios || [];

  let bars: Awaited<ReturnType<typeof api.barsBySymbol>> = [];
  let financials: Awaited<ReturnType<typeof api.financialsBySymbol>> | null = null;
  let symbolQuality: { last_bar_date: string | null; freshness: string } | null = null;
  try {
    bars = await api.barsBySymbol(symbol, 120);
    financials = await api.financialsBySymbol(symbol);
    const dq = await api.dataQuality();
    symbolQuality = dq.symbols.find((s) => s.symbol === symbol) || null;
  } catch {
    bars = [];
  }

  let factorRow = null;
  try {
    const portfolios = await api.portfolios();
    if (portfolios[0]) {
      const factors = await api.factors(portfolios[0].id);
      factorRow = factors.find((f) => f.symbol === symbol) || null;
    }
  } catch {
    factorRow = null;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold">
            {security.name}{" "}
            <span className="text-lg text-gray-500">{security.symbol}</span>
          </h1>
          <p className="text-sm text-gray-400">
            {security.sector} · 现价 {security.last_price ?? "—"} ·{" "}
            <span className="text-aims-research">
              {ratingLabel[latest.rating] || latest.rating}
            </span>{" "}
            · v{latest.version} · {latest.agent_name}
            {latest.created_at && (
              <> · 更新于 {latest.created_at.slice(0, 10)}</>
            )}
          </p>
          {symbolQuality && symbolQuality.freshness !== "ok" && (
            <p className="mt-1 text-xs text-yellow-400">
              行情数据 {symbolQuality.freshness === "stale" ? "已过期" : "缺失"}
              （最新 K 线：{symbolQuality.last_bar_date ?? "无"}）—{" "}
              <Link href="/data" className="underline">
                前往同步
              </Link>
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <GenerateResearchButton securityId={security.id} symbol={symbol} />
          <Link href="/decisions" className="rounded border border-aims-trade px-3 py-1 text-sm text-aims-trade">
            相关决策 →
          </Link>
        </div>
      </div>

      <Card title="投资结论">
        <p className="text-sm leading-relaxed">{latest.investment_conclusion}</p>
      </Card>

      <Card title="行情走势（真实 K 线）">
        <PriceChart data={bars} />
      </Card>

      {financials && financials.reports.length > 0 && (
        <Card title="财报摘要">
          <table className="w-full text-left text-sm">
            <thead className="text-gray-400">
              <tr>
                <th>报告期</th>
                <th>归母净利润</th>
                <th>营业总收入</th>
                <th>ROE</th>
              </tr>
            </thead>
            <tbody>
              {financials.reports.slice(0, 4).map((r) => (
                <tr key={r.period_key} className="border-t border-aims-border">
                  <td className="py-2">{r.period_key}</td>
                  <td>{formatMetric(r.metrics["归母净利润"])}</td>
                  <td>{formatMetric(r.metrics["营业总收入"])}</td>
                  <td>{formatMetric(r.metrics["净资产收益率"] || r.metrics["ROE"])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {sections.map(({ key, label }) => {
          const text =
            typeof fa[key] === "string"
              ? fa[key]
              : Array.isArray(fa[key])
                ? (fa[key] as string[]).join("；")
                : "";
          return (
            <Card key={key} title={label}>
              <p className="text-sm text-gray-300">
                {text || (
                  <span className="italic text-gray-500">
                    暂无内容 — 可生成研究草稿或手动编辑
                  </span>
                )}
              </p>
            </Card>
          );
        })}
        <Card title="未来 6-12 个月核心变量">
          <ul className="list-disc pl-5 text-sm">
            {(fa.core_variables_6_12m as string[] | undefined)?.map((v) => (
              <li key={v}>{v}</li>
            )) || <li>—</li>}
          </ul>
        </Card>
      </div>

      {factorRow && (
        <Card title="因子分析 (Factor Agent)">
          <div className="grid grid-cols-3 gap-2 text-sm sm:grid-cols-6">
            {Object.entries(factorRow.factors).map(([k, v]) => (
              <div key={k} className="rounded bg-aims-bg p-2 text-center">
                <p className="text-xs text-gray-500">{k}</p>
                <p className="font-semibold">{v}</p>
              </div>
            ))}
          </div>
          {factorRow.warnings.length > 0 && (
            <p className="mt-2 text-xs text-yellow-400">{factorRow.warnings.join("；")}</p>
          )}
        </Card>
      )}

      {scenarios.length > 0 && (
        <Card title="估值情景">
          <p className="mb-2 text-xs text-gray-500">
            币种 {latest.scenario_analysis?.currency ?? "—"}
            {latest.scenario_analysis?.current_price != null &&
              ` · 现价 ${latest.scenario_analysis.current_price}`}
            {latest.created_at && ` · 观点更新 ${latest.created_at.slice(0, 10)}`}
          </p>
          <table className="w-full text-left text-sm">
            <thead className="text-gray-400">
              <tr>
                <th>情景</th>
                <th>目标价区间</th>
                <th>触发条件</th>
              </tr>
            </thead>
            <tbody>
              {scenarios.map((s) => (
                <tr key={s.name} className="border-t border-aims-border">
                  <td className="py-2">{scenarioLabel[s.name] || s.name}</td>
                  <td>
                    {s.target_price_low} — {s.target_price_high}{" "}
                    {latest.scenario_analysis?.currency}
                  </td>
                  <td className="text-gray-400">{s.triggers?.join("；")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <Card title="相关事件">
        <div className="space-y-3">
          {related_events?.map((e) => (
            <StructuredEventCard key={e.id} event={e} />
          ))}
          {!related_events?.length && (
            <p className="text-sm text-gray-500">暂无相关结构化事件</p>
          )}
        </div>
      </Card>

      <ResearchEditor data={data} />

      {history.length > 0 && (
        <Card title="历史观点版本">
          <ul className="space-y-2 text-sm text-gray-400">
            {history.map((h) => (
              <li key={h.id}>
                v{h.version} · {ratingLabel[h.rating]} · {h.created_at?.slice(0, 10)}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
