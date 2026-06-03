import { DecisionInboxClient } from "@/components/DecisionInboxClient";
import { api } from "@/lib/api";
import type { InboxTab } from "@/lib/inboxSelection";

export const dynamic = "force-dynamic";

export default async function DecisionInboxPage({
  searchParams,
}: {
  searchParams: { tab?: string };
}) {
  const portfolios = await api.portfolios();
  const pid = portfolios[0]?.id;
  const tab: InboxTab = searchParams.tab === "approved" ? "approved" : "draft";

  if (!pid) {
    return <p className="text-gray-400">暂无组合</p>;
  }

  const drafts = await api.decisions(pid, "draft", true);
  const approved = await api.decisions(pid, "approved", true);

  return (
    <DecisionInboxClient tab={tab} drafts={drafts} approved={approved} />
  );
}
