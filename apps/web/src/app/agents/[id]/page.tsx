import Link from "next/link";
import { Card } from "@/components/Card";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AgentRunPage({ params }: { params: { id: string } }) {
  let run: Awaited<ReturnType<typeof api.agentRun>> | null = null;
  try {
    run = await api.agentRun(params.id);
  } catch {
    run = null;
  }

  if (!run) {
    return (
      <p>
        运行记录不存在。<Link href="/review" className="text-aims-accent">返回复盘</Link>
      </p>
    );
  }

  const trace = run.output?.trace as { steps?: unknown[]; cio_mode?: string; agent_mode?: string } | undefined;

  return (
    <div className="space-y-4">
      <Link href="/review" className="text-sm text-aims-accent">
        ← 复盘
      </Link>
      <h1 className="text-2xl font-bold">Agent 运行详情</h1>
      <div className="grid gap-4 sm:grid-cols-3">
        <Card title="工作流">
          <p>{run.workflow_name}</p>
        </Card>
        <Card title="状态">
          <p>{run.status}</p>
        </Card>
        <Card title="模式">
          <p>{trace?.cio_mode ?? run.input_context?.agent_mode ?? "—"}</p>
        </Card>
      </div>
      {run.error_message && (
        <p className="rounded border border-red-800 bg-red-950/30 p-3 text-sm text-red-300">
          {run.error_message}
        </p>
      )}
      <Card title="Trace（JSON）">
        <pre className="max-h-96 overflow-auto text-xs text-gray-300">
          {JSON.stringify(run.output, null, 2)}
        </pre>
      </Card>
    </div>
  );
}
