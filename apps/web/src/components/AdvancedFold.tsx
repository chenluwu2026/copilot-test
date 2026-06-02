"use client";

import { useState } from "react";

export function AdvancedFold({
  title = "高级 / 调试",
  children,
  defaultOpen = false,
}: {
  title?: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-lg border border-aims-border/60">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-2 text-left text-sm text-gray-400 hover:text-gray-200"
      >
        {title}
        <span>{open ? "▲" : "▼"}</span>
      </button>
      {open && <div className="border-t border-aims-border px-4 py-3">{children}</div>}
    </div>
  );
}
