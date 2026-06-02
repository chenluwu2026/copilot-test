import type { ResearchQuality } from "@/lib/api";

const sectionLabels: Record<string, string> = {
  business_model: "商业模式",
  industry_space: "行业空间",
  competitive_landscape: "竞争格局",
  financial_quality: "财务质量",
  management: "管理层",
  growth_drivers: "增长驱动",
  key_risks: "主要风险",
  current_valuation: "当前估值",
};

export function ResearchQualityPanel({ quality }: { quality: ResearchQuality }) {
  if (!quality.found) {
    return <p className="text-sm text-gray-500">标的不存在</p>;
  }
  if (!quality.has_view) {
    return (
      <div className="space-y-2 text-sm">
        <p className="text-yellow-400">尚无研究观点</p>
        <ul className="list-disc pl-5 text-gray-400">
          {(quality.issues || []).map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      </div>
    );
  }

  const gradeClass =
    quality.quality_grade === "A"
      ? "text-aims-research"
      : quality.quality_grade === "B"
        ? "text-yellow-400"
        : "text-aims-negative";

  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap gap-3">
        <span>
          完成度 <strong>{quality.completion_pct}%</strong>
        </span>
        <span className={gradeClass}>
          质量 {quality.quality_grade}（{quality.quality_score} 分）
        </span>
        {quality.age_days != null && (
          <span className="text-gray-400">研究 {quality.age_days} 天前更新</span>
        )}
        {quality.gate && (
          <span className={quality.gate.research_allowed ? "text-aims-research" : "text-aims-negative"}>
            闸门 {quality.gate.research_allowed ? "通过" : "未通过"}
          </span>
        )}
      </div>
      <div className="grid gap-1 sm:grid-cols-2">
        {Object.entries(quality.sections || {}).map(([key, ok]) => (
          <div key={key} className="flex items-center gap-2">
            <span className={ok ? "text-aims-research" : "text-gray-500"}>{ok ? "✓" : "○"}</span>
            <span>{sectionLabels[key] || key}</span>
          </div>
        ))}
      </div>
      {(quality.issues || []).length > 0 && (
        <ul className="list-disc pl-5 text-xs text-yellow-400">
          {quality.issues!.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
