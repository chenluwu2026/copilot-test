"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { MemoryItem } from "@/lib/api";
import { api } from "@/lib/api";

export function MemoryPanel({ memories }: { memories: MemoryItem[] }) {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);

  async function activate(id: string) {
    setLoading(id);
    try {
      await api.activateMemory(id);
      router.refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(null);
    }
  }

  return (
    <ul className="space-y-3 text-sm">
      {memories.map((m) => (
        <li key={m.id} className="rounded border border-aims-border p-3">
          <div className="flex items-center gap-2">
            <span className="rounded bg-aims-border px-1 text-xs">{m.memory_type}</span>
            {m.active ? (
              <span className="text-xs text-aims-positive">已激活</span>
            ) : m.pending ? (
              <span className="text-xs text-yellow-400">待确认</span>
            ) : null}
          </div>
          <p className="mt-1 font-medium">{m.title}</p>
          <p className="text-gray-400">{m.content}</p>
          {m.pending && !m.active && (
            <button
              onClick={() => activate(m.id)}
              disabled={loading === m.id}
              className="mt-2 text-xs text-aims-accent"
            >
              确认并激活
            </button>
          )}
        </li>
      ))}
      {!memories.length && <p className="text-gray-500">暂无记忆条目</p>}
    </ul>
  );
}
