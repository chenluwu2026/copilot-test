"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Security, Watchlist } from "@/lib/api";
import { api } from "@/lib/api";

export function WatchlistEditor({
  lists,
  securities,
}: {
  lists: Watchlist[];
  securities: Security[];
}) {
  const router = useRouter();
  const [watchlistId, setWatchlistId] = useState(lists[0]?.id || "");
  const [securityId, setSecurityId] = useState("");
  const [tier, setTier] = useState("track");
  const [thesis, setThesis] = useState("");
  const [newName, setNewName] = useState("");
  const [msg, setMsg] = useState("");

  async function addItem() {
    if (!watchlistId || !securityId) return;
    setMsg("");
    try {
      await api.addWatchlistItem(watchlistId, {
        security_id: securityId,
        tier,
        thesis_summary: thesis || undefined,
      });
      setMsg("已加入股票池");
      router.refresh();
    } catch (e) {
      setMsg(String(e));
    }
  }

  async function createList() {
    if (!newName.trim()) return;
    try {
      const w = await api.createWatchlist({ name: newName.trim() });
      setWatchlistId(w.id);
      setNewName("");
      setMsg(`已创建：${w.name}`);
      router.refresh();
    } catch (e) {
      setMsg(String(e));
    }
  }

  return (
    <div className="rounded-lg border border-aims-border bg-aims-card p-4 text-sm">
      <h2 className="font-medium text-gray-300">管理股票池</h2>
      <div className="mt-3 flex flex-wrap gap-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="新建池名称"
          className="rounded border border-aims-border bg-aims-bg px-2 py-1"
        />
        <button
          type="button"
          onClick={createList}
          className="rounded bg-aims-border px-3 py-1 text-xs"
        >
          创建
        </button>
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <select
          value={watchlistId}
          onChange={(e) => setWatchlistId(e.target.value)}
          className="rounded border border-aims-border bg-aims-bg px-2 py-1"
        >
          {lists.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
        <select
          value={securityId}
          onChange={(e) => setSecurityId(e.target.value)}
          className="rounded border border-aims-border bg-aims-bg px-2 py-1"
        >
          <option value="">选择标的</option>
          {securities.map((s) => (
            <option key={s.id} value={s.id}>
              {s.symbol} {s.name}
            </option>
          ))}
        </select>
        <select
          value={tier}
          onChange={(e) => setTier(e.target.value)}
          className="rounded border border-aims-border bg-aims-bg px-2 py-1"
        >
          <option value="core">核心</option>
          <option value="track">跟踪</option>
          <option value="idea">想法</option>
        </select>
        <button
          type="button"
          onClick={addItem}
          className="rounded bg-aims-accent px-3 py-1 text-white"
        >
          加入
        </button>
      </div>
      <input
        value={thesis}
        onChange={(e) => setThesis(e.target.value)}
        placeholder="论点摘要（可选）"
        className="mt-2 w-full rounded border border-aims-border bg-aims-bg px-2 py-1"
      />
      {msg && <p className="mt-2 text-xs text-gray-500">{msg}</p>}
    </div>
  );
}
