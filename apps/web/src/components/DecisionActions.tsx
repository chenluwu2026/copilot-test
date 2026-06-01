"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export function DecisionActions({
  decisionId,
  status,
  action,
  portfolioId,
}: {
  decisionId: string;
  status: string;
  action: string;
  portfolioId: string;
}) {
  const router = useRouter();
  const [msg, setMsg] = useState("");
  const [rating, setRating] = useState(4);
  const [correction, setCorrection] = useState("");

  async function approve() {
    try {
      await api.updateDecisionStatus(decisionId, "approved");
      setMsg("已批准");
      router.refresh();
    } catch (e) {
      setMsg(String(e));
    }
  }

  async function reject() {
    try {
      await api.updateDecisionStatus(decisionId, "cancelled");
      setMsg("已拒绝");
      router.refresh();
    } catch (e) {
      setMsg(String(e));
    }
  }

  async function execute() {
    try {
      await api.executeDecision(decisionId);
      setMsg("已执行模拟成交");
      router.refresh();
    } catch (e) {
      setMsg(String(e));
    }
  }

  async function submitFeedback() {
    try {
      await api.feedback(decisionId, { rating, correction });
      setMsg("反馈已保存");
      router.refresh();
    } catch (e) {
      setMsg(String(e));
    }
  }

  const canTrade = !["hold", "watch", "ban"].includes(action);

  return (
    <div className="rounded-lg border border-aims-border bg-aims-card p-4 space-y-3">
      <h3 className="font-medium">操作</h3>
      <div className="flex flex-wrap gap-2">
        {status === "draft" && (
          <>
            <button
              onClick={approve}
              className="rounded bg-aims-accent px-4 py-2 text-sm text-white"
            >
              批准
            </button>
            <button
              onClick={reject}
              className="rounded border border-aims-border px-4 py-2 text-sm text-gray-300"
            >
              拒绝
            </button>
          </>
        )}
        {status === "approved" && canTrade && (
          <button
            onClick={execute}
            className="rounded bg-aims-trade px-4 py-2 text-sm text-white"
          >
            执行模拟交易
          </button>
        )}
      </div>

      <div className="border-t border-aims-border pt-3">
        <p className="mb-2 text-sm text-gray-400">用户反馈</p>
        <div className="flex items-center gap-2">
          <label className="text-sm">评分</label>
          <input
            type="number"
            min={1}
            max={5}
            value={rating}
            onChange={(e) => setRating(Number(e.target.value))}
            className="w-16 rounded border border-aims-border bg-aims-bg px-2 py-1"
          />
        </div>
        <textarea
          className="mt-2 w-full rounded border border-aims-border bg-aims-bg p-2 text-sm"
          placeholder="纠正或补充..."
          value={correction}
          onChange={(e) => setCorrection(e.target.value)}
          rows={2}
        />
        <button
          onClick={submitFeedback}
          className="mt-2 rounded border border-aims-border px-3 py-1 text-sm"
        >
          提交反馈
        </button>
      </div>
      {msg && <p className="text-sm text-gray-300">{msg}</p>}
    </div>
  );
}
