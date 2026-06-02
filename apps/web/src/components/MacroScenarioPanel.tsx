import type { MacroScenario } from "@/lib/api";

export function MacroScenarioPanel({ scenarios }: { scenarios: MacroScenario[] }) {
  if (!scenarios.length) {
    return <p className="text-sm text-gray-500">暂无宏观情景</p>;
  }
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {scenarios.map((s) => (
        <div key={s.id} className="rounded border border-aims-border p-3 text-sm">
          <h3 className="font-medium text-aims-research">{s.name}</h3>
          <p className="mt-1 text-gray-400">{s.description}</p>
          <p className="mt-2 text-xs text-gray-500">
            倾斜：权益 {((s.tilts.equity || 0) * 100).toFixed(0)}% / 债券{" "}
            {((s.tilts.bond || 0) * 100).toFixed(0)}% / 现金{" "}
            {((s.tilts.cash || 0) * 100).toFixed(0)}%
          </p>
          {s.watchlist_actions && s.watchlist_actions.length > 0 && (
            <ul className="mt-2 list-disc pl-4 text-xs text-gray-400">
              {s.watchlist_actions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}
