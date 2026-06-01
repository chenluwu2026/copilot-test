"use client";

import { useEffect, useState } from "react";
import { api, type InvestmentProfile } from "@/lib/api";

export function InvestmentProfileForm() {
  const [profile, setProfile] = useState<InvestmentProfile | null>(null);
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .me()
      .then((u) => setProfile(u.investment_profile))
      .catch((e) => setStatus(String(e)))
      .finally(() => setLoading(false));
  }, []);

  async function save() {
    if (!profile) return;
    setStatus("保存中…");
    try {
      const res = await api.updateProfile({
        markets: profile.markets,
        style: profile.style,
        risk_budget: profile.risk_budget,
        forbidden_sectors: profile.forbidden_sectors,
        forbidden_symbols: profile.forbidden_symbols,
        research_max_age_days: profile.research_max_age_days,
        review_due_days: profile.review_due_days,
        review_material_move_pct: profile.review_material_move_pct,
        notes: profile.notes,
      });
      setProfile(res.investment_profile);
      setStatus("已保存，组合风控参数已同步。");
    } catch (e) {
      setStatus(String(e));
    }
  }

  if (loading) return <p className="text-sm text-gray-400">加载投资画像…</p>;
  if (!profile) return <p className="text-sm text-red-400">{status || "加载失败"}</p>;

  return (
    <div className="space-y-4 text-sm">
      <div>
        <label className="text-gray-400">市场（逗号分隔，如 CN_A,HK）</label>
        <input
          className="mt-1 w-full rounded border border-aims-border bg-aims-bg px-3 py-2"
          value={profile.markets.join(", ")}
          onChange={(e) =>
            setProfile({
              ...profile,
              markets: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
            })
          }
        />
      </div>
      <div>
        <label className="text-gray-400">风格标签</label>
        <input
          className="mt-1 w-full rounded border border-aims-border bg-aims-bg px-3 py-2"
          value={profile.style.join(", ")}
          onChange={(e) =>
            setProfile({
              ...profile,
              style: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
            })
          }
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="text-gray-400">单票上限 %</label>
          <input
            type="number"
            className="mt-1 w-full rounded border border-aims-border bg-aims-bg px-3 py-2"
            value={profile.risk_budget.max_single_name_pct}
            onChange={(e) =>
              setProfile({
                ...profile,
                risk_budget: {
                  ...profile.risk_budget,
                  max_single_name_pct: Number(e.target.value),
                },
              })
            }
          />
        </div>
        <div>
          <label className="text-gray-400">行业上限 %</label>
          <input
            type="number"
            className="mt-1 w-full rounded border border-aims-border bg-aims-bg px-3 py-2"
            value={profile.risk_budget.max_sector_pct}
            onChange={(e) =>
              setProfile({
                ...profile,
                risk_budget: {
                  ...profile.risk_budget,
                  max_sector_pct: Number(e.target.value),
                },
              })
            }
          />
        </div>
        <div>
          <label className="text-gray-400">最低现金 %</label>
          <input
            type="number"
            className="mt-1 w-full rounded border border-aims-border bg-aims-bg px-3 py-2"
            value={profile.risk_budget.min_cash_pct}
            onChange={(e) =>
              setProfile({
                ...profile,
                risk_budget: {
                  ...profile.risk_budget,
                  min_cash_pct: Number(e.target.value),
                },
              })
            }
          />
        </div>
        <div>
          <label className="text-gray-400">研究有效期（天）</label>
          <input
            type="number"
            className="mt-1 w-full rounded border border-aims-border bg-aims-bg px-3 py-2"
            value={profile.research_max_age_days}
            onChange={(e) =>
              setProfile({
                ...profile,
                research_max_age_days: Number(e.target.value),
              })
            }
          />
        </div>
        <div>
          <label className="text-gray-400">复盘提醒周期（天）</label>
          <input
            type="number"
            className="mt-1 w-full rounded border border-aims-border bg-aims-bg px-3 py-2"
            value={profile.review_due_days}
            onChange={(e) =>
              setProfile({
                ...profile,
                review_due_days: Number(e.target.value),
              })
            }
          />
        </div>
        <div>
          <label className="text-gray-400">重大波动阈值（%）</label>
          <input
            type="number"
            className="mt-1 w-full rounded border border-aims-border bg-aims-bg px-3 py-2"
            value={profile.review_material_move_pct}
            onChange={(e) =>
              setProfile({
                ...profile,
                review_material_move_pct: Number(e.target.value),
              })
            }
          />
        </div>
      </div>
      <div>
        <label className="text-gray-400">禁止行业（逗号分隔）</label>
        <input
          className="mt-1 w-full rounded border border-aims-border bg-aims-bg px-3 py-2"
          value={profile.forbidden_sectors.join(", ")}
          onChange={(e) =>
            setProfile({
              ...profile,
              forbidden_sectors: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
            })
          }
        />
      </div>
      <div>
        <label className="text-gray-400">禁止标的（逗号分隔，如 600519.SH）</label>
        <input
          className="mt-1 w-full rounded border border-aims-border bg-aims-bg px-3 py-2"
          value={profile.forbidden_symbols.join(", ")}
          onChange={(e) =>
            setProfile({
              ...profile,
              forbidden_symbols: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
            })
          }
        />
      </div>
      <div>
        <label className="text-gray-400">投资笔记</label>
        <textarea
          className="mt-1 min-h-[80px] w-full rounded border border-aims-border bg-aims-bg px-3 py-2"
          value={profile.notes}
          onChange={(e) => setProfile({ ...profile, notes: e.target.value })}
        />
      </div>
      <button
        type="button"
        onClick={save}
        className="rounded bg-aims-accent px-4 py-2 text-white hover:opacity-90"
      >
        保存投资画像
      </button>
      {status && <p className="text-gray-400">{status}</p>}
    </div>
  );
}
