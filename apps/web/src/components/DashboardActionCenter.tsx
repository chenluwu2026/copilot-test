import Link from "next/link";
import type { DashboardActions } from "@/lib/api";

export function DashboardActionCenter({ actions }: { actions: DashboardActions | null }) {
  if (!actions) return null;

  const { review, draft_decisions, approved_decisions, stale_data_symbols, data_coverage_pct } =
    actions;

  const items = [
    {
      label: "待复盘",
      value: review.open_count,
      highlight: review.due_count > 0,
      href: "/review",
      sub:
        review.due_count > 0
          ? `${review.due_count} 条到期${review.overdue_count > 0 ? `，${review.overdue_count} 逾期` : ""}`
          : undefined,
    },
    {
      label: "待批准决策",
      value: draft_decisions,
      highlight: draft_decisions > 0,
      href: "/decisions/inbox",
      sub: draft_decisions > 0 ? "CIO 草案待处理" : undefined,
    },
    {
      label: "待执行",
      value: approved_decisions,
      highlight: approved_decisions > 0,
      href: "/decisions/inbox?tab=approved",
      sub: approved_decisions > 0 ? "已批准未成交" : undefined,
    },
    {
      label: "数据过期/缺失",
      value: stale_data_symbols,
      highlight: stale_data_symbols > 0,
      href: "/data",
      sub: `覆盖率 ${data_coverage_pct}%`,
    },
    {
      label: "待激活记忆",
      value: review.pending_memory_count,
      highlight: review.pending_memory_count > 0,
      href: "/review",
    },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      {items.map((item) => (
        <Link
          key={item.label}
          href={item.href}
          className={`rounded-lg border p-4 transition hover:border-aims-accent ${
            item.highlight ? "border-yellow-600/50 bg-yellow-900/10" : "border-aims-border bg-aims-card"
          }`}
        >
          <p className="text-xs text-gray-400">{item.label}</p>
          <p className="mt-1 text-2xl font-semibold">{item.value}</p>
          {item.sub && <p className="mt-1 text-xs text-gray-500">{item.sub}</p>}
        </Link>
      ))}
    </div>
  );
}
