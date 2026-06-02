import Link from "next/link";
import type { OperatorSteps } from "@/lib/api";

const statusStyle: Record<string, string> = {
  complete: "border-aims-positive/40 text-aims-positive",
  active: "border-aims-accent/50 text-aims-accent",
  blocked: "border-yellow-600/40 text-yellow-400",
};

export function DashboardOperatorSteps({ data }: { data: OperatorSteps | null }) {
  if (!data?.steps?.length) return null;

  return (
    <section className="rounded-lg border border-aims-border bg-aims-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-gray-400">基金经理一日</h2>
        <span className="text-xs text-gray-500">
          {data.completed_count}/{data.total_count} 步完成
        </span>
      </div>
      <ol className="mt-3 space-y-2">
        {data.steps.map((s, i) => (
          <li
            key={s.id}
            className={`flex flex-wrap items-center justify-between gap-2 rounded border px-3 py-2 text-sm ${statusStyle[s.status] || "border-aims-border"}`}
          >
            <span>
              <span className="text-gray-500">{i + 1}.</span>{" "}
              <Link href={s.href} className="hover:underline">
                {s.label}
              </Link>
            </span>
            <span className="text-xs capitalize">{s.status}</span>
            {s.blocked_reason && s.status !== "complete" && (
              <p className="w-full text-xs text-gray-500">{s.blocked_reason}</p>
            )}
          </li>
        ))}
      </ol>
      <p className="mt-2 text-xs text-gray-600">
        详见 <code className="text-gray-400">docs/DAILY_OPERATOR_PLAYBOOK.md</code>
      </p>
    </section>
  );
}
