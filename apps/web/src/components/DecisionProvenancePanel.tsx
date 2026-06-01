import Link from "next/link";
import type { DecisionProvenance } from "@/lib/api";

export function DecisionProvenancePanel({ data }: { data: DecisionProvenance | null }) {
  if (!data) {
    return <p className="text-sm text-gray-500">暂无溯源信息（可能为手工录入决策）。</p>;
  }

  const run = data.agent_run;
  const evidence = data.evidence;

  return (
    <div className="space-y-4 text-sm">
      {evidence?.grade && (
        <p>
          证据完整度：
          <span className="font-medium text-aims-accent">
            {evidence.grade}
            {evidence.score != null ? `（${evidence.score} 分）` : ""}
          </span>
          {evidence.issues && evidence.issues.length > 0 && (
            <ul className="mt-1 list-disc pl-5 text-xs text-gray-400">
              {evidence.issues.map((issue, i) => (
                <li key={i}>{issue}</li>
              ))}
            </ul>
          )}
        </p>
      )}
      {data.created_by_agent && (
        <p className="text-gray-400">创建方：{data.created_by_agent}</p>
      )}
      {(data.dossier_summary || run?.dossier_summary) && (
        <div className="rounded border border-aims-border p-3">
          <p className="font-medium">证据卷宗摘要</p>
          <pre className="mt-2 overflow-x-auto text-xs text-gray-400">
            {JSON.stringify(data.dossier_summary || run?.dossier_summary, null, 2)}
          </pre>
        </div>
      )}
      {data.references && data.references.length > 0 && (
        <div>
          <p className="font-medium">决策引用</p>
          <ul className="mt-1 space-y-1">
            {data.references.map((r, i) => (
              <li key={i} className="rounded border border-aims-border p-2 text-xs">
                <span className="text-aims-accent">{r.ref_type}</span>
                {r.excerpt && <p className="text-gray-500">{r.excerpt}</p>}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.gate_hints.length > 0 && (
        <div>
          <p className="font-medium text-yellow-400">闸门 / 约束</p>
          <ul className="mt-1 list-disc pl-5 text-gray-300">
            {data.gate_hints.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        </div>
      )}
      {data.linked_memories.length > 0 && (
        <div>
          <p className="font-medium">关联记忆</p>
          <ul className="mt-1 space-y-1">
            {data.linked_memories.map((m) => (
              <li key={m.id} className="rounded border border-aims-border p-2">
                <span className="text-aims-accent">{m.title}</span>
                {m.active && (
                  <span className="ml-2 text-xs text-aims-positive">已激活</span>
                )}
                <p className="text-xs text-gray-500">{m.content}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
      {run && (
        <div>
          <p className="font-medium">Agent 运行</p>
          <Link href={`/agents/${run.run_id}`} className="text-aims-accent">
            {run.workflow_name} · {run.status} · {run.cio_mode || run.agent_mode}
            {run.cio_decision_mode ? ` · ${run.cio_decision_mode}` : ""}
          </Link>
          {run.portfolio_step && (
            <p className="mt-1 text-xs text-gray-500">
              组合模式：{(run.portfolio_step as { mode?: string }).mode || "rule"}
            </p>
          )}
          {run.valuation_step && (
            <p className="text-xs text-gray-500">
              估值更新：{(run.valuation_step as { count?: number }).count ?? 0} 只
            </p>
          )}
          {run.memories && run.memories.length > 0 && (
            <ul className="mt-2 text-xs text-gray-400">
              <li>本次 CIO 引用记忆：</li>
              {run.memories.map((m, i) => (
                <li key={i}>
                  {m.title}: {m.content?.slice(0, 80)}
                </li>
              ))}
            </ul>
          )}
          {run.memory_query && (
            <p className="mt-1 text-xs text-gray-500">
              检索上下文：标的 {run.memory_query.symbols?.join(", ")} · 行业{" "}
              {run.memory_query.sectors?.join(", ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
