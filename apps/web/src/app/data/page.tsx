import { Card } from "@/components/Card";
import { SyncDataPanel } from "@/components/SyncDataPanel";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function DataPage() {
  let quality: Awaited<ReturnType<typeof api.dataQuality>> | null = null;
  let jobs: Awaited<ReturnType<typeof api.syncJobs>> = [];
  try {
    quality = await api.dataQuality();
    jobs = await api.syncJobs();
  } catch {
    quality = null;
  }

  const s = quality?.summary;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">数据中心</h1>
      <p className="text-sm text-gray-400">
        行情 / 公告 / 财报 / 关注池资讯同步（AkShare）。支持后台全量同步与定时任务（
        DATA_SYNC_CRON_ENABLED、NEWS_SYNC_CRON_ENABLED）。
      </p>

      {s && (
        <div className="grid gap-4 sm:grid-cols-4">
          <Card title="标的数">
            <p className="text-xl">{s.securities}</p>
          </Card>
          <Card title="行情覆盖率">
            <p className="text-xl">{s.coverage_pct}%</p>
            <p className="text-xs text-gray-500">
              新鲜 {s.with_fresh_quotes} · 过期 {s.stale_quotes} · 缺失 {s.missing_quotes}
            </p>
          </Card>
          <Card title="数据源">
            <p className="text-lg">{s.data_provider}</p>
          </Card>
          <Card title="过期阈值">
            <p className="text-lg">{s.stale_threshold_days} 天</p>
          </Card>
        </div>
      )}

      <SyncDataPanel />

      {quality && quality.symbols.length > 0 && (
        <Card title="分标的新鲜度">
          <div className="max-h-64 overflow-auto text-sm">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-aims-border text-gray-500">
                  <th className="py-1">代码</th>
                  <th>最新K线</th>
                  <th>状态</th>
                  <th>公告</th>
                  <th>财报</th>
                </tr>
              </thead>
              <tbody>
                {quality.symbols.map((row) => (
                  <tr key={row.symbol} className="border-b border-aims-border/50">
                    <td className="py-1">{row.symbol}</td>
                    <td>{row.last_bar_date ?? "—"}</td>
                    <td>
                      <span
                        className={
                          row.freshness === "ok"
                            ? "text-green-400"
                            : row.freshness === "stale"
                              ? "text-yellow-400"
                              : "text-red-400"
                        }
                      >
                        {row.freshness}
                      </span>
                    </td>
                    <td>{row.filing_count}</td>
                    <td>{row.financial_report_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {jobs.length > 0 && (
        <Card title="最近同步作业">
          <ul className="space-y-2 text-sm">
            {jobs.map((j) => (
              <li key={j.id} className="rounded border border-aims-border/50 px-2 py-1">
                <span className="font-mono text-xs text-gray-500">{j.job_type}</span>{" "}
                <span
                  className={
                    j.status === "success"
                      ? "text-green-400"
                      : j.status === "failed"
                        ? "text-red-400"
                        : "text-yellow-400"
                  }
                >
                  {j.status}
                </span>
                {j.started_at && (
                  <span className="ml-2 text-gray-500">{j.started_at.slice(0, 19)}</span>
                )}
                {j.error_message && (
                  <p className="text-xs text-red-300 truncate">{j.error_message}</p>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
