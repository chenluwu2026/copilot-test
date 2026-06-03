"use client";

import Link from "next/link";

export type BatchResultRow = {
  id: string;
  ok: boolean;
  label?: string;
  detail?: string;
  href?: string;
};

export function BatchOperationResultPanel({
  title,
  succeeded,
  failed,
  rows,
  onDismiss,
}: {
  title: string;
  succeeded: number;
  failed: number;
  rows: BatchResultRow[];
  onDismiss: () => void;
}) {
  if (!rows.length) return null;

  return (
    <section className="rounded-lg border border-aims-border bg-aims-card p-4 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="font-medium text-gray-200">{title}</h3>
          <p className="mt-1 text-xs text-gray-500">
            成功 <span className="text-aims-positive">{succeeded}</span> · 失败{" "}
            <span className={failed > 0 ? "text-aims-negative" : ""}>{failed}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="text-xs text-gray-500 hover:text-gray-300"
        >
          关闭
        </button>
      </div>
      <ul className="mt-3 max-h-56 space-y-1 overflow-y-auto text-xs">
        {rows.map((r) => (
          <li
            key={r.id}
            className={`flex flex-wrap items-baseline justify-between gap-2 rounded px-2 py-1 ${
              r.ok ? "bg-aims-positive/5" : "bg-aims-negative/10"
            }`}
          >
            <span>
              {r.ok ? "✓" : "✗"}{" "}
              {r.href ? (
                <Link href={r.href} className="text-aims-accent hover:underline">
                  {r.label || r.id.slice(0, 8)}
                </Link>
              ) : (
                <span>{r.label || r.id.slice(0, 8)}</span>
              )}
            </span>
            <span className="text-gray-500">{r.detail || (r.ok ? "完成" : "失败")}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
