import Link from "next/link";
import type { DecisionTimeline } from "@/lib/api";

export function DecisionTimelinePanel({ timeline }: { timeline: DecisionTimeline | null }) {
  if (!timeline) return null;

  return (
    <section className="rounded-lg border border-aims-border bg-aims-card p-4">
      <h2 className="text-sm font-medium text-gray-400">决策时间线</h2>
      <ol className="mt-3 space-y-3 border-l border-aims-border pl-4">
        {timeline.events.map((e) => (
          <li key={e.key} className="relative text-sm">
            <span className="absolute -left-[1.35rem] top-1 h-2 w-2 rounded-full bg-aims-accent" />
            <p className="font-medium">{e.label}</p>
            {e.at && <p className="text-xs text-gray-500">{e.at}</p>}
            {e.detail && <p className="text-xs text-gray-400">{e.detail}</p>}
          </li>
        ))}
      </ol>
      {timeline.agent_runs.length > 0 && (
        <div className="mt-4 border-t border-aims-border pt-3">
          <p className="text-xs text-gray-500">关联 Agent 运行</p>
          <ul className="mt-1 space-y-1 text-sm">
            {timeline.agent_runs.map((r) => (
              <li key={r.run_id}>
                <Link href={`/agents/${r.run_id}`} className="text-aims-accent hover:underline">
                  {r.workflow_name}
                </Link>
                <span className="ml-2 text-xs text-gray-500">
                  {r.status}
                  {r.cio_mode ? ` · ${r.cio_mode}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
