/** 生产环境：NEXT_PUBLIC_API_URL 指向独立 API；同源部署（Caddy）则走 /api/v1 */
export function getApiBase(): string {
  const pub = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (pub) return `${pub}/api/v1`;
  const server = process.env.API_URL?.replace(/\/$/, "");
  if (typeof window === "undefined" && server) return `${server}/api/v1`;
  return "/api/v1";
}

function apiHeaders(init?: RequestInit): HeadersInit {
  const key = process.env.NEXT_PUBLIC_API_KEY;
  return {
    "Content-Type": "application/json",
    ...(key ? { "X-API-Key": key } : {}),
    ...init?.headers,
  };
}

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers: apiHeaders(init),
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

  events: (params?: Record<string, string>) => {
    const q = new URLSearchParams(params).toString();
    return fetchApi<StructuredEvent[]>(`/events${q ? `?${q}` : ""}`);
  },
  event: (id: string) => fetchApi<StructuredEvent>(`/events/${id}`),
  ingestNews: (body: object) =>
    fetchApi<{ event_id: string }>("/events/ingest", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  researchList: () => fetchApi<ResearchSummary[]>("/research"),
  researchBySymbol: (symbol: string) => fetchApi<ResearchDetail>(`/research/symbol/${symbol}`),
  generateResearchDraft: (securityId: string) =>
    fetchApi(`/research/${securityId}/generate-draft`, { method: "POST" }),

  runRebalance: (portfolioId: string) =>
    fetchApi<{ run_id: string; decision_ids: string[] }>(
      `/agents/workflows/rebalance/${portfolioId}`,
      { method: "POST" }
    ),
  agentRuns: (portfolioId?: string) =>
    fetchApi<AgentRun[]>(`/agents/runs${portfolioId ? `?portfolio_id=${portfolioId}` : ""}`),
  agentRun: (id: string) => fetchApi<AgentRunDetail>(`/agents/runs/${id}`),
  factors: (portfolioId: string) => fetchApi<FactorRow[]>(`/agents/factors/${portfolioId}`),
  riskDashboard: (portfolioId: string) => fetchApi<RiskDashboard>(`/agents/risk/${portfolioId}`),

  memories: (pending?: boolean) => {
    const q = pending !== undefined ? `?pending=${pending}` : "";
    return fetchApi<MemoryItem[]>(`/memory${q}`);
  },
  activateMemory: (id: string) =>
    fetchApi(`/memory/${id}/activate`, { method: "POST" }),

  openDecisions: (portfolioId?: string) =>
    fetchApi<OpenDecision[]>(
      `/review/open-decisions${portfolioId ? `?portfolio_id=${portfolioId}` : ""}`
    ),
  runReview: (decisionId: string) =>
    fetchApi<{
      memory_id?: string;
      return_since_decision_pct: number;
      price_metadata?: Record<string, unknown>;
    }>(`/review/decisions/${decisionId}/run`, { method: "POST" }),
  promoteReviewMemory: (decisionId: string, body?: { title?: string; activate?: boolean }) =>
    fetchApi<{ memory_id: string }>(`/review/decisions/${decisionId}/memory`, {
      method: "POST",
      body: JSON.stringify(body || {}),
    }),
  attribution: (portfolioId: string) => fetchApi<AttributionReport>(`/review/attribution/${portfolioId}`),
  backtest: (portfolioId: string) => fetchApi<BacktestRow[]>(`/review/backtest/${portfolioId}`),

  syncQuotes: (body?: object) =>
    fetchApi<Record<string, unknown>>("/data/sync/quotes", {
      method: "POST",
      body: JSON.stringify(body || {}),
    }),
  syncFilings: (body?: object) =>
    fetchApi<Record<string, unknown>>("/data/sync/filings", {
      method: "POST",
      body: JSON.stringify(body || {}),
    }),
  syncFinancials: (body?: object) =>
    fetchApi<Record<string, unknown>>("/data/sync/financials", {
      method: "POST",
      body: JSON.stringify(body || {}),
    }),
  syncAll: (body?: object) =>
    fetchApi<Record<string, unknown>>("/data/sync/all", {
      method: "POST",
      body: JSON.stringify(body || {}),
    }),
  syncAllAsync: (body?: object) =>
    fetchApi<{ job_id: string; status: string; message?: string }>("/data/sync/all/async", {
      method: "POST",
      body: JSON.stringify(body || {}),
    }),
  syncJob: (id: string) => fetchApi<SyncJob>(`/data/sync/jobs/${id}`),
  syncJobs: () => fetchApi<SyncJob[]>(`/data/sync/jobs`),
  dataQuality: () => fetchApi<DataQualityReport>("/data/quality"),
  agentConfig: () => fetchApi<AgentConfig>("/agents/config"),
  barsBySymbol: (symbol: string, days = 90) =>
    fetchApi<MarketBar[]>(`/data/bars/symbol/${encodeURIComponent(symbol)}?days=${days}`),
  filings: (securityId?: string, limit = 50) =>
    fetchApi<FilingItem[]>(
      `/data/filings${securityId ? `?security_id=${securityId}&limit=${limit}` : `?limit=${limit}`}`
    ),
  financialsBySymbol: (symbol: string) =>
    fetchApi<FinancialsPayload>(`/data/financials/symbol/${encodeURIComponent(symbol)}`),
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

export type StructuredEvent = {
  id: string;
  event_type: string;
  impact_direction: string;
  impact_dimensions: string[];
  confidence: string;
  time_sensitivity: string;
  companies: { symbol: string; name: string; security_id?: string }[];
  related_securities: { symbol: string }[];
  follow_ups: string[];
  summary: string;
  published_at: string;
  article?: { title: string; body?: string; source_name: string };
};

export type ResearchSummary = {
  security_id: string;
  symbol: string;
  name: string;
  sector?: string;
  rating: string;
  horizon?: string;
  version: number;
  investment_conclusion: string;
  updated_at?: string;
};

export type ResearchDetail = {
  security: { id: string; symbol: string; name: string; sector?: string; last_price?: number };
  latest: ResearchViewDetail;
  history: ResearchViewDetail[];
  related_events: StructuredEvent[];
};

export type AgentRun = {
  id: string;
  workflow_name: string;
  status: string;
  decision_ids: string[];
  started_at?: string;
  agent_mode?: string;
};

export type AgentRunDetail = AgentRun & {
  input_context?: { agent_mode?: string; portfolio_id?: string };
  output?: {
    trace?: { steps?: unknown[]; cio_mode?: string; agent_mode?: string };
    decision_ids?: string[];
  };
  error_message?: string;
  finished_at?: string;
};

export type FactorRow = {
  symbol: string;
  name: string;
  data_complete?: boolean;
  factors: Record<string, number>;
  warnings: string[];
};

export type DataQualityReport = {
  summary: {
    securities: number;
    with_fresh_quotes: number;
    stale_quotes: number;
    missing_quotes: number;
    coverage_pct: number;
    stale_threshold_days: number;
    data_provider: string;
  };
  symbols: {
    symbol: string;
    name: string;
    market: string;
    last_bar_date: string | null;
    freshness: string;
    filing_count: number;
    financial_report_count: number;
  }[];
};

export type AgentConfig = {
  agent_mode: string;
  structuring_mode: string;
  llm_configured: boolean;
  llm_active: boolean;
  llm_model: string | null;
  data_sync_cron_enabled: boolean;
};

export type RiskDashboard = {
  limits: Record<string, number>;
  cash_pct: number;
  alerts: { type: string; symbol?: string; weight_pct?: number; limit?: number }[];
  ok: boolean;
};

export type MemoryItem = {
  id: string;
  memory_type: string;
  title: string;
  content: string;
  active: boolean;
  pending: boolean;
};

export type OpenDecision = {
  decision_id: string;
  symbol: string;
  name: string;
  action: string;
  return_since_decision_pct?: number;
  price_source?: string;
  entry_price?: number;
  exit_price?: number;
  has_outcome?: boolean;
};

export type AttributionReport = {
  sector_attribution: { sector: string; unrealized_pnl: number; contribution_pct: number }[];
  decision_stats: {
    reviewed: number;
    avg_return_pct: number;
    win_rate_pct?: number;
    best_pct?: number;
    worst_pct?: number;
  };
};

export type BacktestRow = {
  decision_id: string;
  symbol?: string;
  name?: string;
  action?: string;
  return_pct: number;
  summary?: string;
  price_source?: string;
};

export type SyncJob = {
  id: string;
  job_type: string;
  status: string;
  result: Record<string, unknown>;
  started_at?: string;
  finished_at?: string;
  error_message?: string;
};

export type MarketBar = {
  bar_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type FilingItem = {
  id: string;
  symbol?: string;
  name?: string;
  filing_type: string;
  title: string;
  published_at?: string;
  source_url?: string;
  structured_event_id?: string;
};

export type FinancialsPayload = {
  symbol: string;
  name: string;
  reports: { period_key: string; metrics: Record<string, number | null> }[];
};

export type ResearchViewDetail = {
  id: string;
  rating: string;
  horizon?: string;
  version: number;
  agent_name: string;
  created_at?: string;
  fundamental_analysis: Record<string, string | string[]>;
  investment_conclusion: string;
  valuation_snapshot?: Record<string, unknown>;
  scenario_analysis?: {
    methods?: string[];
    scenarios?: {
      name: string;
      target_price_low: number;
      target_price_high: number;
      triggers: string[];
      probability_weight?: number;
      downside_risk_note?: string;
    }[];
    current_price?: number;
    currency?: string;
  };
};
