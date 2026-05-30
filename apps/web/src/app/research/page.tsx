import { Card } from "@/components/Card";

export default function ResearchPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">公司研究</h1>
      <Card>
        <p className="text-sm text-gray-400">
          <span className="text-aims-research">Phase 2</span>：十段式基本面、估值情景、研报上传与
          Research Agent 草稿。当前请通过「决策日志」记录投资观点。
        </p>
      </Card>
    </div>
  );
}
