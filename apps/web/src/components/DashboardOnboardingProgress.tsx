import Link from "next/link";
import type { OnboardingStatus } from "@/lib/api";

export function DashboardOnboardingProgress({ status }: { status: OnboardingStatus | null }) {
  if (!status) return null;

  const pct = Math.round((status.completed_count / status.total_count) * 100);

  return (
    <section className="rounded-lg border border-aims-border bg-aims-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-gray-400">Phase 1 完成度</h2>
        <span className="text-sm text-gray-300">
          {status.completed_count}/{status.total_count} · {pct}%
        </span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded bg-aims-border">
        <div
          className="h-full bg-aims-accent transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <ul className="mt-3 space-y-1 text-xs">
        {Object.entries(status.checks).map(([key, c]) => (
          <li key={key} className="flex items-start gap-2">
            <span className={c.ok ? "text-aims-positive" : "text-gray-500"}>
              {c.ok ? "✓" : "○"}
            </span>
            <span className="text-gray-400">
              {key}: {c.current}/{c.required}
              {!c.ok && <span className="ml-1 text-gray-600">— {c.hint}</span>}
            </span>
          </li>
        ))}
      </ul>
      {status.all_complete && (
        <p className="mt-2 text-xs text-aims-positive">Phase 1 DoD 已全部满足。</p>
      )}
      <Link href="/decisions" className="mt-2 inline-block text-xs text-aims-accent hover:underline">
        查看决策日志 →
      </Link>
    </section>
  );
}
