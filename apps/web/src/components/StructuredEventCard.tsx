import Link from "next/link";
import type { StructuredEvent } from "@/lib/api";

const impactColor: Record<string, string> = {
  positive: "text-aims-positive",
  negative: "text-aims-negative",
  neutral: "text-gray-400",
  mixed: "text-yellow-400",
};

const eventTypeLabel: Record<string, string> = {
  earnings_release: "业绩发布",
  buyback: "回购",
  regulation: "监管",
  product_launch: "产品",
  macro_policy: "宏观政策",
  industry_trend: "行业",
  general_news: "综合",
};

export function StructuredEventCard({ event }: { event: StructuredEvent }) {
  return (
    <article className="rounded-lg border border-aims-border bg-aims-card p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded bg-aims-border px-2 py-0.5">
          {eventTypeLabel[event.event_type] || event.event_type}
        </span>
        <span className={impactColor[event.impact_direction] || ""}>
          {event.impact_direction}
        </span>
        <span className="text-gray-500">置信度 {event.confidence}</span>
        <span className="text-gray-500">敏感度 {event.time_sensitivity}</span>
        <span className="ml-auto text-gray-500">
          {event.published_at.slice(0, 10)}
        </span>
      </div>
      <h3 className="font-medium">{event.summary || event.article?.title}</h3>
      <p className="mt-1 text-sm text-gray-400">
        {event.companies.map((c) => c.name).join("、")}
      </p>
      <div className="mt-2 flex flex-wrap gap-1">
        {event.impact_dimensions.map((d) => (
          <span key={d} className="rounded bg-aims-bg px-2 py-0.5 text-xs text-aims-research">
            {d}
          </span>
        ))}
      </div>
      {event.follow_ups.length > 0 && (
        <div className="mt-3 border-t border-aims-border pt-2">
          <p className="text-xs text-gray-500">需跟踪</p>
          <ul className="mt-1 list-disc pl-4 text-xs text-gray-300">
            {event.follow_ups.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </div>
      )}
      {event.companies[0]?.symbol && (
        <Link
          href={`/research/${encodeURIComponent(event.companies[0].symbol)}`}
          className="mt-2 inline-block text-xs text-aims-accent"
        >
          查看研究 →
        </Link>
      )}
    </article>
  );
}
