"use client";

import { useRouter, useSearchParams } from "next/navigation";

const impacts = ["", "positive", "negative", "neutral", "mixed"];
const sensitivities = ["", "low", "medium", "high"];

export function EventsFilter() {
  const router = useRouter();
  const params = useSearchParams();

  function update(key: string, value: string) {
    const p = new URLSearchParams(params.toString());
    if (value) p.set(key, value);
    else p.delete(key);
    router.push(`/events?${p.toString()}`);
  }

  return (
    <div className="flex flex-wrap gap-2 text-sm">
      <select
        className="rounded border border-aims-border bg-aims-card px-2 py-1"
        value={params.get("impact_direction") || ""}
        onChange={(e) => update("impact_direction", e.target.value)}
      >
        <option value="">影响方向</option>
        {impacts.filter(Boolean).map((v) => (
          <option key={v} value={v}>
            {v}
          </option>
        ))}
      </select>
      <select
        className="rounded border border-aims-border bg-aims-card px-2 py-1"
        value={params.get("time_sensitivity") || ""}
        onChange={(e) => update("time_sensitivity", e.target.value)}
      >
        <option value="">时间敏感度</option>
        {sensitivities.filter(Boolean).map((v) => (
          <option key={v} value={v}>
            {v}
          </option>
        ))}
      </select>
      <input
        className="rounded border border-aims-border bg-aims-card px-2 py-1"
        placeholder="事件类型 earnings_release..."
        defaultValue={params.get("event_type") || ""}
        onBlur={(e) => update("event_type", e.target.value)}
      />
    </div>
  );
}
