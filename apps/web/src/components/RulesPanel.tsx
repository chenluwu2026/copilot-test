"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { StrategyRuleItem } from "@/lib/api";
import { api } from "@/lib/api";

export function RulesPanel({ rules }: { rules: StrategyRuleItem[] }) {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);

  async function addRule() {
    if (!code.trim() || !text.trim()) return;
    setLoading(true);
    try {
      await api.createRule({
        rule_code: code.trim(),
        natural_language: text.trim(),
        machine_check: { type: "note" },
        active: true,
      });
      setCode("");
      setText("");
      router.refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function toggle(id: string, active: boolean) {
    await api.updateRule(id, { active: !active });
    router.refresh();
  }

  async function remove(id: string) {
    if (!confirm("删除该规则？")) return;
    await api.deleteRule(id);
    router.refresh();
  }

  return (
    <div className="space-y-4">
      <div className="rounded border border-aims-border p-4 space-y-2">
        <p className="text-sm font-medium">新增规则</p>
        <input
          className="w-full rounded border border-aims-border bg-aims-bg px-2 py-1 text-sm"
          placeholder="rule_code 如 NO_INTERNET_ADD"
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        <textarea
          className="w-full rounded border border-aims-border bg-aims-bg px-2 py-1 text-sm"
          placeholder="自然语言描述（Risk Agent 会读取）"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={2}
        />
        <button
          type="button"
          onClick={addRule}
          disabled={loading}
          className="rounded bg-aims-accent px-3 py-1 text-sm text-white"
        >
          添加
        </button>
      </div>

      <ul className="space-y-2 text-sm">
        {rules.map((r) => (
          <li key={r.id} className="rounded border border-aims-border p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-xs text-aims-accent">{r.rule_code}</span>
              <div className="space-x-2">
                <button
                  type="button"
                  onClick={() => toggle(r.id, r.active)}
                  className="text-xs text-aims-accent"
                >
                  {r.active ? "停用" : "启用"}
                </button>
                <button
                  type="button"
                  onClick={() => remove(r.id)}
                  className="text-xs text-gray-500"
                >
                  删除
                </button>
              </div>
            </div>
            <p className="mt-1">{r.natural_language}</p>
            <p className="mt-1 text-xs text-gray-500">
              machine_check: {JSON.stringify(r.machine_check)}
              {r.source_memory_id && ` · 来自记忆 ${r.source_memory_id.slice(0, 8)}`}
            </p>
          </li>
        ))}
        {!rules.length && <li className="text-gray-500">暂无策略规则</li>}
      </ul>
    </div>
  );
}
