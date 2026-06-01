"use client";

import { useEffect, useState } from "react";
import { api, type ProfileSuggestions } from "@/lib/api";

export function ProfileSuggestionsPanel() {
  const [data, setData] = useState<ProfileSuggestions | null>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.profileSuggestions().then(setData).catch(() => setData(null));
  }, []);

  async function apply(field: string, suggested: number) {
    setMsg("应用中…");
    try {
      await api.applyProfileSuggestion(field, suggested);
      setMsg("已应用到投资画像");
      const next = await api.profileSuggestions();
      setData(next);
    } catch (e) {
      setMsg(String(e));
    }
  }

  if (!data?.suggestions.length) {
    return (
      <p className="text-sm text-gray-500">
        {data?.rationale || "提交决策反馈后，这里会出现画像调整建议。"}
      </p>
    );
  }

  return (
    <ul className="space-y-3 text-sm">
      {data.suggestions.map((s) => (
        <li key={s.field} className="rounded border border-aims-border p-3">
          <p className="font-medium">{s.field}</p>
          <p className="text-gray-400">
            {s.current} → {s.suggested} · {s.reason}
          </p>
          <button
            type="button"
            onClick={() => apply(s.field, s.suggested)}
            className="mt-2 text-aims-accent"
          >
            一键应用
          </button>
        </li>
      ))}
      {msg && <p className="text-gray-500">{msg}</p>}
    </ul>
  );
}
