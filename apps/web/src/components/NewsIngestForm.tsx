"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Security } from "@/lib/api";

export function NewsIngestForm({ onDone }: { onDone?: () => void }) {
  const router = useRouter();
  const [securities, setSecurities] = useState<Security[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.securities().then(setSecurities);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMsg("");
    try {
      const res = await api.ingestNews({
        title,
        body,
        security_ids: selected,
      });
      setMsg(`已结构化，事件 ID: ${res.event_id}`);
      setTitle("");
      setBody("");
      router.refresh();
      onDone?.();
    } catch (err) {
      setMsg(String(err));
    }
  }

  return (
    <form onSubmit={submit} className="space-y-2 rounded border border-aims-border bg-aims-card p-4 text-sm">
      <p className="font-medium text-gray-300">录入新闻（自动结构化）</p>
      <input
        required
        className="w-full rounded border border-aims-border bg-aims-bg p-2"
        placeholder="标题"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <textarea
        className="w-full rounded border border-aims-border bg-aims-bg p-2"
        rows={3}
        placeholder="正文"
        value={body}
        onChange={(e) => setBody(e.target.value)}
      />
      <select
        multiple
        className="h-24 w-full rounded border border-aims-border bg-aims-bg p-2"
        value={selected}
        onChange={(e) =>
          setSelected(Array.from(e.target.selectedOptions, (o) => o.value))
        }
      >
        {securities.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name} ({s.symbol})
          </option>
        ))}
      </select>
      <button type="submit" className="rounded bg-aims-accent px-3 py-1 text-white">
        提交并结构化
      </button>
      {msg && <p className="text-xs text-gray-400">{msg}</p>}
    </form>
  );
}
