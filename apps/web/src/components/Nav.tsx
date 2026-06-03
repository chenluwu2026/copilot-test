"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "指挥中心" },
  { href: "/decisions/inbox", label: "交易台" },
  { href: "/research", label: "研究池" },
  { href: "/watchlist", label: "股票池" },
  { href: "/review", label: "复盘" },
  { href: "/portfolio", label: "组合" },
  { href: "/decisions", label: "决策日志" },
  { href: "/events", label: "事件" },
  { href: "/data", label: "数据" },
  { href: "/agents", label: "Agent" },
  { href: "/settings", label: "设置" },
];

export function Nav() {
  const path = usePathname();
  return (
    <nav className="flex flex-wrap gap-1 border-b border-aims-border bg-aims-card px-4 py-3">
      <span className="mr-4 font-semibold text-aims-accent">AIMS</span>
      {links.map((l) => (
        <Link
          key={l.href}
          href={l.href}
          className={`rounded px-3 py-1 text-sm ${
            path === l.href || (l.href !== "/" && path.startsWith(l.href))
              ? "bg-aims-accent text-white"
              : "text-gray-300 hover:bg-aims-border"
          }`}
        >
          {l.label}
        </Link>
      ))}
    </nav>
  );
}
