import type { ReviewSummary } from "@/lib/api";

export function ReviewSummaryBanner({ summary }: { summary: ReviewSummary | null }) {
  if (!summary || summary.open_count === 0) {
    return (
      <p className="rounded border border-aims-border bg-aims-card px-4 py-3 text-sm text-gray-400">
        当前无待复盘决策。执行新交易后，系统会按画像中的复盘周期（默认 {summary?.review_due_days ?? 30} 天）提醒复盘。
      </p>
    );
  }

  return (
    <div className="rounded border border-aims-border bg-aims-card px-4 py-3 text-sm">
      <p>
        <span className="font-medium text-white">{summary.open_count}</span> 条待复盘
        {summary.due_count > 0 && (
          <>
            ，其中 <span className="text-yellow-400">{summary.due_count}</span> 条已到期待复盘
          </>
        )}
        {summary.overdue_count > 0 && (
          <>
            （<span className="text-aims-negative">{summary.overdue_count}</span> 条已逾期）
          </>
        )}
        。
      </p>
      {summary.pending_memory_count > 0 && (
        <p className="mt-1 text-aims-accent">
          {summary.pending_memory_count} 条已复盘决策的记忆尚未激活，激活后将在下次 CIO 调仓时注入。
        </p>
      )}
      <p className="mt-1 text-xs text-gray-500">
        复盘周期：执行后 {summary.review_due_days} 天，或收益波动超过画像中的「重大波动」阈值。
      </p>
    </div>
  );
}
