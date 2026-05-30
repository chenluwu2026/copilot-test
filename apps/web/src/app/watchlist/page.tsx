import Link from "next/link";
import { Card } from "@/components/Card";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

const tierLabel: Record<string, string> = {
  core: "核心",
  track: "跟踪",
  idea: "想法",
};

export default async function WatchlistPage() {
  const lists = await api.watchlists();

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">股票池</h1>
      {lists.map((wl) => (
        <Card key={wl.id} title={wl.name}>
          <table className="w-full text-left text-sm">
            <thead className="text-gray-400">
              <tr>
                <th>标的</th>
                <th>层级</th>
                <th>论点</th>
              </tr>
            </thead>
            <tbody>
              {wl.items.map((i) => (
                <tr key={i.symbol} className="border-t border-aims-border">
                  <td className="py-2">
                    <Link
                      href={`/research/${encodeURIComponent(i.symbol)}`}
                      className="text-aims-accent hover:underline"
                    >
                      {i.name}
                    </Link>{" "}
                    <span className="text-gray-500">{i.symbol}</span>
                  </td>
                  <td>{tierLabel[i.tier] || i.tier}</td>
                  <td className="text-gray-400">{i.thesis_summary || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ))}
      {!lists.length && <p className="text-gray-500">暂无股票池</p>}
    </div>
  );
}
