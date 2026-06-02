"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  api,
  type DecisionPipelineResponse,
  type Portfolio,
  type Security,
} from "@/lib/api";

export default function NewDecisionPage() {
  const router = useRouter();
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [securities, setSecurities] = useState<Security[]>([]);
  const [portfolioId, setPortfolioId] = useState("");
  const [securityId, setSecurityId] = useState("");
  const [action, setAction] = useState("add");
  const [reason, setReason] = useState("");
  const [currentW, setCurrentW] = useState(0);
  const [targetW, setTargetW] = useState(5);
  const [assumption, setAssumption] = useState("");
  const [risk, setRisk] = useState("");
  const [review, setReview] = useState("");
  const [error, setError] = useState("");
  const [pipelineScore, setPipelineScore] = useState(1);
  const [autoApprove, setAutoApprove] = useState(true);
  const [autoSimulate, setAutoSimulate] = useState(true);
  const [pipelineResult, setPipelineResult] = useState<DecisionPipelineResponse | null>(null);

  useEffect(() => {
    api.portfolios().then((p) => {
      setPortfolios(p);
      if (p[0]) setPortfolioId(p[0].id);
    });
    api.securities().then((s) => {
      setSecurities(s);
      if (s[0]) setSecurityId((prev) => prev || s[0].id);
    });
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const d = await api.createDecision({
        portfolio_id: portfolioId,
        security_id: securityId,
        action,
        decision_reason: reason,
        current_weight_pct: currentW,
        target_weight_pct: targetW,
        main_risks: risk ? [risk] : [],
        review_conditions: review ? [review] : [],
        assumptions: assumption ? [{ text: assumption }] : [],
        confidence_grade: "B",
        holding_period: "3-6个月",
      });
      router.push(`/decisions/${d.id}`);
    } catch (err) {
      setError(String(err));
    }
  }

  async function runPipeline(e: React.FormEvent) {
    e.preventDefault();
    if (!portfolioId || !securityId) return;
    setError("");
    setPipelineResult(null);
    try {
      const out = await api.runDecisionPipeline({
        portfolio_id: portfolioId,
        candidates: [{ security_id: securityId, score: pipelineScore }],
        max_turnover_pct: 30,
        auto_approve: autoApprove,
        auto_execute_simulated: autoSimulate,
        simulated_fill_ratio: 0.7,
        auto_retry_resize: true,
        max_retry_steps: 3,
        retry_decay_factor: 0.75,
        auto_apply_fallback_partial: true,
      });
      setPipelineResult(out);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <h1 className="text-2xl font-bold">新建决策</h1>
      <form onSubmit={runPipeline} className="space-y-3 rounded border border-aims-border p-3 text-sm">
        <h2 className="font-semibold text-aims-accent">智能流水线（推荐）</h2>
        <p className="text-xs text-gray-400">
          自动执行：目标权重→风控→重试/降级→建单，可选自动审批与模拟执行。
        </p>
        <label className="block">
          候选分数
          <input
            type="number"
            step="0.1"
            className="mt-1 w-full rounded border border-aims-border bg-aims-card p-2"
            value={pipelineScore}
            onChange={(e) => setPipelineScore(Number(e.target.value))}
          />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={autoApprove} onChange={(e) => setAutoApprove(e.target.checked)} />
            自动审批
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={autoSimulate} onChange={(e) => setAutoSimulate(e.target.checked)} />
            自动模拟执行
          </label>
        </div>
        <button type="submit" className="rounded bg-aims-research px-4 py-2 text-white">
          运行流水线
        </button>
      </form>

      {pipelineResult && (
        <div className="space-y-2 rounded border border-aims-border p-3 text-sm">
          <p className="text-xs text-gray-400">
            目标现金占比：{pipelineResult.cash_target_pct}% · 结果 {pipelineResult.results.length} 条
          </p>
          {pipelineResult.results.map((r) => (
            <div key={`${r.security_id}-${r.decision_id || "none"}`} className="rounded bg-aims-card p-2">
              <p>
                <strong>{r.symbol || r.security_id}</strong> · 动作 {r.action} ·{" "}
                {r.current_weight_pct}% → {r.target_weight_pct}% ·{" "}
                {r.allowed ? "通过" : "未通过"}
              </p>
              {r.decision_id && <p className="text-xs text-aims-accent">decision_id: {r.decision_id}</p>}
              {r.execution_plan && (
                <p className="text-xs text-gray-400">
                  滑点 {r.execution_plan.estimated_slippage_bps.toFixed(2)} bps · shortfall{" "}
                  {r.execution_plan.estimated_shortfall.toFixed(2)} · 执行 {r.execution_plan.schedule?.style}
                </p>
              )}
              {r.downgrade_advice && (
                <p className="text-xs text-yellow-400">
                  降级建议：{r.downgrade_advice.suggested_action}（{r.downgrade_advice.reason}）
                </p>
              )}
              {r.retry?.attempted && (
                <p className="text-xs text-gray-400">
                  重试：{r.retry.passed ? "通过" : "失败"} · fallback {r.retry.fallback_action || "—"}
                </p>
              )}
              {r.fallback?.applied && (
                <p className="text-xs text-aims-research">
                  已执行 fallback：{r.fallback.mode}（目标 {r.fallback.target_weight_pct}%）
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      <form onSubmit={submit} className="space-y-3 text-sm">
        <label className="block">
          组合
          <select
            className="mt-1 w-full rounded border border-aims-border bg-aims-card p-2"
            value={portfolioId}
            onChange={(e) => setPortfolioId(e.target.value)}
          >
            {portfolios.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          标的
          <select
            className="mt-1 w-full rounded border border-aims-border bg-aims-card p-2"
            value={securityId}
            onChange={(e) => setSecurityId(e.target.value)}
            required
          >
            <option value="">选择...</option>
            {securities.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.symbol})
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          动作
          <select
            className="mt-1 w-full rounded border border-aims-border bg-aims-card p-2"
            value={action}
            onChange={(e) => setAction(e.target.value)}
          >
            {["buy", "sell", "add", "reduce", "hold", "watch", "ban"].map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label>
            当前仓位 %
            <input
              type="number"
              className="mt-1 w-full rounded border border-aims-border bg-aims-card p-2"
              value={currentW}
              onChange={(e) => setCurrentW(Number(e.target.value))}
            />
          </label>
          <label>
            目标仓位 %
            <input
              type="number"
              className="mt-1 w-full rounded border border-aims-border bg-aims-card p-2"
              value={targetW}
              onChange={(e) => setTargetW(Number(e.target.value))}
            />
          </label>
        </div>
        <label className="block">
          决策理由
          <textarea
            required
            className="mt-1 w-full rounded border border-aims-border bg-aims-card p-2"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
        <label className="block">
          核心假设
          <input
            className="mt-1 w-full rounded border border-aims-border bg-aims-card p-2"
            value={assumption}
            onChange={(e) => setAssumption(e.target.value)}
          />
        </label>
        <label className="block">
          主要风险
          <input
            className="mt-1 w-full rounded border border-aims-border bg-aims-card p-2"
            value={risk}
            onChange={(e) => setRisk(e.target.value)}
          />
        </label>
        <label className="block">
          复盘条件
          <input
            className="mt-1 w-full rounded border border-aims-border bg-aims-card p-2"
            value={review}
            onChange={(e) => setReview(e.target.value)}
          />
        </label>
        {error && <p className="text-aims-negative">{error}</p>}
        <button type="submit" className="rounded bg-aims-accent px-4 py-2 text-white">
          保存草稿
        </button>
      </form>
    </div>
  );
}
