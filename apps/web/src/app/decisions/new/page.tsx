"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Portfolio, type Security } from "@/lib/api";

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

  useEffect(() => {
    api.portfolios().then((p) => {
      setPortfolios(p);
      if (p[0]) setPortfolioId(p[0].id);
    });
    api.securities().then(setSecurities);
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

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <h1 className="text-2xl font-bold">新建决策</h1>
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
