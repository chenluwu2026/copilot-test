import type { DecisionCoverage } from "@/lib/api";

export function DecisionCoveragePanel({ data }: { data: DecisionCoverage }) {
  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap gap-3">
        <span>
          卷宗覆盖 <strong>{data.coverage_pct}%</strong>
        </span>
        {data.evidence_grade && (
          <span>
            证据 {data.evidence_grade}
            {data.evidence_score != null ? `（${data.evidence_score}）` : ""}
          </span>
        )}
      </div>
      <ul className="space-y-2">
        {data.checks.map((c) => (
          <li key={c.label} className="flex gap-2 border-l-2 border-aims-border pl-2">
            <span className={c.covered ? "text-aims-research" : "text-aims-negative"}>
              {c.covered ? "✓" : "✗"}
            </span>
            <div>
              <span className="font-medium">{c.label}</span>
              <p className="text-xs text-gray-500">{c.detail}</p>
            </div>
          </li>
        ))}
      </ul>
      {(data.evidence_issues || []).length > 0 && (
        <ul className="list-disc pl-5 text-xs text-yellow-400">
          {data.evidence_issues!.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
