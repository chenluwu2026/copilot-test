import Link from "next/link";

const steps = [
  { n: 1, label: "画像与股票池", href: "/settings" },
  { n: 2, label: "全量同步", href: "/data" },
  { n: 3, label: "维护研究", href: "/research" },
  { n: 4, label: "生成调仓", href: "/portfolio" },
  { n: 5, label: "收件箱批准", href: "/decisions/inbox" },
  { n: 6, label: "复盘记忆", href: "/review" },
];

export function QuickStartGuide() {
  return (
    <section className="rounded-lg border border-aims-border bg-aims-card p-4">
      <h2 className="text-sm font-medium text-gray-400">推荐使用顺序</h2>
      <ol className="mt-2 flex flex-wrap gap-2 text-sm">
        {steps.map((s) => (
          <li key={s.n}>
            <Link href={s.href} className="text-aims-accent hover:underline">
              {s.n}. {s.label}
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}
