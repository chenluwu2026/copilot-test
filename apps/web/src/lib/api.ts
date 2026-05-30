const BASE = "/api/v1";

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

export const api = {
  portfolios: () => fetchApi<Portfolio[]>("/portfolios"),
  portfolioSummary: (id: string) => fetchApi<PortfolioSummary>(`/portfolios/${id}/summary`),
  portfolioNav: (id: string, days = 90) =>
    fetchApi<NavPoint[]>(`/portfolios/${id}/nav?days=${days}`),
  portfolioTrades: (id: string) => fetchApi<Trade[]>(`/portfolios/${id}/trades`),
  createTrade: (id: string, body: object) =>
    fetchApi<Trade>(`/portfolios/${id}/trades`, { method: "POST", body: JSON.stringify(body) }),
  dailyReport: (id: string) =>
    fetchApi<{ summary_md: string; metrics: Record<string, number> }>(
      `/portfolios/${id}/reports/daily`,
      { method: "POST" }
    ),
  backfillNav: (id: string) =>
    fetchApi<{ created: number }>(`/portfolios/${id}/nav/backfill-demo`, { method: "POST" }),

  securities: (q?: string) =>
    fetchApi<Security[]>(`/securities${q ? `?q=${encodeURIComponent(q)}` : ""}`),

  decisions: (portfolioId?: string, status?: string) => {
    const params = new URLSearchParams();
    if (portfolioId) params.set("portfolio_id", portfolioId);
    if (status) params.set("status", status);
    const q = params.toString();
    return fetchApi<Decision[]>(`/decisions${q ? `?${q}` : ""}`);
  },
  decision: (id: string) => fetchApi<Decision>(`/decisions/${id}`),
  createDecision: (body: object) =>
    fetchApi<Decision>("/decisions", { method: "POST", body: JSON.stringify(body) }),
  updateDecisionStatus: (id: string, status: string) =>
    fetchApi<Decision>(`/decisions/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  executeDecision: (id: string, price?: number) =>
    fetchApi<{ trade_id: string }>(`/decisions/${id}/execute`, {
      method: "POST",
      body: JSON.stringify({ price }),
    }),
  feedback: (id: string, body: object) =>
    fetchApi(`/decisions/${id}/feedback`, { method: "POST", body: JSON.stringify(body) }),

  watchlists: () => fetchApi<Watchlist[]>("/watchlists"),
};

export type Portfolio = {
  id: string;
  name: string;
  cash_balance: number;
  initial_cash: number;
};

export type PortfolioSummary = {
  portfolio_id: string;
  name: string;
  nav: number;
  cash: number;
  cumulative_return_pct: number;
  cash_pct: number;
  position_count: number;
  positions: {
    symbol: string;
    name: string;
    weight_pct: number;
    market_value: number;
    unrealized_pnl: number;
    sector?: string;
  }[];
};

export type NavPoint = {
  snapshot_date: string;
  nav: number;
  daily_return_pct?: number;
  cumulative_return_pct?: number;
};

export type Trade = {
  id: string;
  symbol?: string;
  name?: string;
  side: string;
  quantity: number;
  price: number;
  amount: number;
  trade_date: string;
};

export type Security = {
  id: string;
  symbol: string;
  name: string;
  market: string;
  last_price?: number;
};

export type Decision = {
  id: string;
  symbol: string;
  name: string;
  action: string;
  status: string;
  current_weight_pct: number;
  target_weight_pct: number;
  delta_weight_pct: number;
  decision_reason: string;
  main_risks: string[];
  review_conditions: string[];
  confidence_grade?: string;
  holding_period?: string;
  assumptions: { text: string; measurable: boolean }[];
  references: { ref_type: string; excerpt?: string }[];
  created_at?: string;
};

export type Watchlist = {
  id: string;
  name: string;
  items: { symbol: string; name: string; tier: string; thesis_summary?: string }[];
};
