import { Card } from "@/components/Card";

export default function EventsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">News & Events</h1>
      <Card>
        <p className="text-sm text-gray-400">
          <span className="text-aims-research">Phase 2</span>：结构化事件流（公司、事件类型、影响方向、
          follow_ups）。Data Agent + Structuring Agent 接入后在此展示。
        </p>
      </Card>
    </div>
  );
}
