import { Suspense } from "react";
import { StructuredEventCard } from "@/components/StructuredEventCard";
import { EventsFilter } from "@/components/EventsFilter";
import { NewsIngestForm } from "@/components/NewsIngestForm";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function EventsPage({
  searchParams,
}: {
  searchParams: {
    impact_direction?: string;
    time_sensitivity?: string;
    event_type?: string;
    highlight?: string;
  };
}) {
  const params: Record<string, string> = {};
  if (searchParams.impact_direction) params.impact_direction = searchParams.impact_direction;
  if (searchParams.time_sensitivity) params.time_sensitivity = searchParams.time_sensitivity;
  if (searchParams.event_type) params.event_type = searchParams.event_type;

  const events = await api.events(params);
  const highlight = searchParams.highlight;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">News & Events</h1>
      <p className="text-sm text-gray-400">
        结构化信息流：公司、事件类型、影响方向、维度、置信度与 follow-ups。
      </p>

      <Suspense>
        <EventsFilter />
      </Suspense>

      <NewsIngestForm />

      <div className="space-y-3">
        {events.map((e) => (
          <div
            key={e.id}
            id={`event-${e.id}`}
            className={highlight === e.id ? "ring-2 ring-aims-accent rounded-lg" : ""}
          >
            <StructuredEventCard event={e} />
          </div>
        ))}
        {!events.length && (
          <p className="text-gray-500">暂无事件。请启动 API 或录入新闻。</p>
        )}
      </div>
    </div>
  );
}
