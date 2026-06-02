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
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(key ? { "X-API-Key": key } : {}),
  };
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("aims_token");
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  return { ...headers, ...(init?.headers as Record<string, string> | undefined) };
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
  getDailyReport: (id: string, reportDate?: string) => {
    const q = reportDate ? `?report_date=${reportDate}` : "";
    return fetchApi<{ summary_md: string; metrics: Record<string, number> }>(
      `/portfolios/${id}/reports/daily${q}`
    );
  },
  dailyReport: (id: string) =>
    fetchApi<{ summary_md: string; metrics: Record<string, number> }>(
      `/portfolios/${id}/reports/daily`,
      { method: "POST" }
    ),
  backfillNav: (id: string) =>
    fetchApi<{ created: number }>(`/portfolios/${id}/nav/backfill-demo`, { method: "POST" }),
  resetNav: (id: string) =>
    fetchApi<{ nav: number; message: string }>(`/portfolios/${id}/nav/reset`, {
      method: "POST",
    }),

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
    fetchApi<{ trade_id: string | null; status: string; message?: string }>(
      `/decisions/${id}/execute`,
      {
        method: "POST",
        body: JSON.stringify({ price }),
      }
    ),
  feedback: (id: string, body: object) =>
    fetchApi(`/decisions/${id}/feedback`, { method: "POST", body: JSON.stringify(body) }),

  watchlists: () => fetchApi<Watchlist[]>("/watchlists"),
  createWatchlist: (body: { name: string; description?: string }) =>
    fetchApi<{ id: string; name: string }>("/watchlists", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  addWatchlistItem: (
    watchlistId: string,
    body: { security_id: string; tier: string; thesis_summary?: string }
  ) =>
    fetchApi<{ id: string }>(`/watchlists/${watchlistId}/items`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  events: (params?: Record<string, string>) => {
    const q = new URLSearchParams(params).toString();
    return fetchApi<StructuredEvent[]>(`/events${q ? `?${q}` : ""}`);
  },
  event: (id: string) => fetchApi<StructuredEvent>(`/events/${id}`),
  ingestNews: (body: object) =>
    fetchApi<{ event_id: string; research_refreshed?: string[] }>("/events/ingest", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  refreshEventResearch: (eventId: string) =>
    fetchApi<{ refreshed_symbols: string[] }>(`/events/${eventId}/refresh-research`, {
      method: "POST",
    }),

  researchList: () => fetchApi<ResearchSummary[]>("/research"),
  researchBySymbol: (symbol: string) => fetchApi<ResearchDetail>(`/research/symbol/${symbol}`),
  researchQuality: (symbol: string) =>
    fetchApi<ResearchQuality>(`/research/symbol/${encodeURIComponent(symbol)}/quality`),
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

  reviewSummary: (portfolioId: string) =>
    fetchApi<ReviewSummary>(`/review/summary?portfolio_id=${portfolioId}`),
  pendingMemories: (portfolioId: string) =>
    fetchApi<PendingMemoryDecision[]>(`/review/pending-memories?portfolio_id=${portfolioId}`),
  openDecisions: (portfolioId?: string) =>
    fetchApi<OpenDecision[]>(
      `/review/open-decisions${portfolioId ? `?portfolio_id=${portfolioId}` : ""}`
    ),
  runReview: (decisionId: string) =>
    fetchApi<ReviewRunResult>(`/review/decisions/${decisionId}/run`, { method: "POST" }),
  monthlyRetrospective: (portfolioId: string, year?: number, month?: number) => {
    const params = new URLSearchParams();
    if (year) params.set("year", String(year));
    if (month) params.set("month", String(month));
    const q = params.toString();
    return fetchApi<MonthlyRetrospective>(
      `/review/retrospective/${portfolioId}${q ? `?${q}` : ""}`
    );
  },
  backtestQuality: (portfolioId: string) =>
    fetchApi<BacktestQualityReport>(`/review/backtest-quality/${portfolioId}`),
  executionQuality: (portfolioId: string) =>
    fetchApi<ExecutionQualityReport>(`/review/execution-quality/${portfolioId}`),
  macroScenarios: () => fetchApi<{ scenarios: MacroScenario[] }>("/scenarios"),
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
  syncNews: (maxSymbols?: number) =>
    fetchApi<{ ingested: number; symbols_scanned: number; errors: string[] }>(
      `/data/sync/news${maxSymbols ? `?max_symbols=${maxSymbols}` : ""}`,
      { method: "POST" }
    ),
  dataQuality: () => fetchApi<DataQualityReport>("/data/quality"),
  agentConfig: () => fetchApi<AgentConfig>("/agents/config"),

  me: () => fetchApi<UserMe>("/users/me"),
  updateProfile: (body: Partial<InvestmentProfile>) =>
    fetchApi<{ investment_profile: InvestmentProfile }>("/users/me/profile", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  profileSuggestions: () => fetchApi<ProfileSuggestions>("/users/me/profile/suggestions"),
  applyProfileSuggestion: (field: string, suggested: number) =>
    fetchApi<{ investment_profile: InvestmentProfile }>("/users/me/profile/apply-suggestion", {
      method: "POST",
      body: JSON.stringify({ field, suggested }),
    }),

  dashboardActions: (portfolioId: string) =>
    fetchApi<DashboardActions>(`/dashboard/actions?portfolio_id=${portfolioId}`),

  dashboardSteps: (portfolioId: string) =>
    fetchApi<OperatorSteps>(`/dashboard/steps?portfolio_id=${portfolioId}`),

  onboardingStatus: (portfolioId?: string) =>
    fetchApi<OnboardingStatus>(
      `/onboarding/status${portfolioId ? `?portfolio_id=${portfolioId}` : ""}`
    ),

  dashboardMetrics: (portfolioId: string) =>
    fetchApi<QualityMetrics>(`/dashboard/metrics?portfolio_id=${portfolioId}`),

  agentConfigHealth: () => fetchApi<AgentConfigHealth>("/agents/config/health"),

  decisionTimeline: (decisionId: string) =>
    fetchApi<DecisionTimeline>(`/decisions/${decisionId}/timeline`),

  dataProviderInfo: () => fetchApi<{ data_provider: string; is_mock: boolean }>("/data/provider"),

  login: (email: string, password: string) =>
    fetchApi<{ access_token: string; email: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  decisionProvenance: (decisionId: string) =>
    fetchApi<DecisionProvenance>(`/decisions/${decisionId}/provenance`),
  decisionCoverage: (decisionId: string) =>
    fetchApi<DecisionCoverage>(`/decisions/${decisionId}/coverage`),

  createResearch: (body: object) =>
    fetchApi<ResearchViewDetail>("/research", { method: "POST", body: JSON.stringify(body) }),

  rules: () => fetchApi<StrategyRuleItem[]>("/rules"),
  createRule: (body: object) =>
    fetchApi<StrategyRuleItem>("/rules", { method: "POST", body: JSON.stringify(body) }),
  updateRule: (id: string, body: object) =>
    fetchApi<StrategyRuleItem>(`/rules/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteRule: (id: string) =>
    fetchApi<{ deleted: string }>(`/rules/${id}`, { method: "DELETE" }),
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
  evidence_grade?: string;
  evidence_score?: number;
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
    cio_mode?: string;
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

export type InvestmentProfile = {
  markets: string[];
  style: string[];
  risk_budget: {
    max_drawdown_pct?: number;
    max_single_name_pct: number;
    max_sector_pct: number;
    min_cash_pct: number;
  };
  forbidden_sectors: string[];
  forbidden_symbols: string[];
  research_max_age_days: number;
  review_due_days: number;
  review_material_move_pct: number;
  notes: string;
};

export type OnboardingStatus = {
  portfolio_id: string;
  phase: number;
  completed_count: number;
  total_count: number;
  all_complete: boolean;
  checks: Record<
    string,
    { ok: boolean; current: number; required: number; hint: string }
  >;
};

export type OperatorStep = {
  id: string;
  label: string;
  href: string;
  status: "complete" | "active" | "blocked";
  blocked_reason: string | null;
};

export type OperatorSteps = {
  portfolio_id: string;
  completed_count: number;
  total_count: number;
  steps: OperatorStep[];
};

export type DecisionTimeline = {
  decision_id: string;
  current_status: string;
  events: {
    key: string;
    label: string;
    status: string;
    at: string | null;
    detail?: string;
  }[];
  agent_runs: {
    run_id: string;
    workflow_name: string;
    status: string;
    trigger: string;
    cio_mode?: string;
    started_at?: string;
  }[];
};

export type AgentConfigHealth = {
  agent_mode: string;
  structuring_mode: string;
  llm_model: string;
  llm_configured: boolean;
  llm_active: boolean;
  openai_base_url_set: boolean;
};

export type DashboardActions = {
  portfolio_id: string;
  review: ReviewSummary;
  draft_decisions: number;
  low_evidence_drafts?: number;
  approved_decisions: number;
  stale_data_symbols: number;
  data_coverage_pct: number;
  assumptions_pending?: {
    decision_id: string;
    assumption_id: string;
    text: string;
    deadline: string;
  }[];
  event_review_todos?: {
    event_id: string;
    symbols: string[];
    summary: string;
    impact_direction: string;
    published_at: string;
    suggested_action: string;
  }[];
};

export type DecisionProvenance = {
  decision_id: string;
  cio_summary: Record<string, unknown>;
  created_by_agent?: string;
  gate_hints: string[];
  linked_memories: { id: string; title: string; content: string; active: boolean }[];
  evidence?: { grade?: string; score?: number; issues?: string[] };
  references?: { ref_type: string; ref_id?: string; excerpt?: string }[];
  dossier_summary?: Record<string, unknown> | null;
  agent_run?: {
    run_id: string;
    workflow_name: string;
    status: string;
    started_at?: string;
    agent_mode?: string;
    cio_mode?: string;
    cio_decision_mode?: string;
    dossier_summary?: Record<string, unknown>;
    memory_query?: { symbols?: string[]; sectors?: string[] };
    memories?: { title: string; content?: string }[];
    portfolio_step?: Record<string, unknown>;
    valuation_step?: Record<string, unknown>;
  } | null;
};

export type ProfileSuggestions = {
  suggestions: {
    field: string;
    current: number;
    suggested: number;
    reason: string;
  }[];
  rationale: string;
  sample_corrections: string[];
};

export type StrategyRuleItem = {
  id: string;
  rule_code: string;
  natural_language: string;
  machine_check: Record<string, unknown>;
  active: boolean;
  source_memory_id?: string | null;
  created_at?: string;
};

export type UserMe = {
  id: string;
  email: string;
  display_name: string;
  investment_profile: InvestmentProfile;
};

export type AgentConfig = {
  agent_mode: string;
  structuring_mode: string;
  llm_configured: boolean;
  llm_active: boolean;
  llm_model: string | null;
  data_sync_cron_enabled: boolean;
  cio_decision_mode?: string;
  event_research_refresh_enabled?: boolean;
  daily_report_cron_enabled?: boolean;
  review_cron_enabled?: boolean;
  review_cron_time?: string;
  news_sync_cron_enabled?: boolean;
  news_sync_cron_time?: string;
  auth_password_configured?: boolean;
  alembic_upgrade_on_start?: boolean;
};

export type QualityMetrics = {
  portfolio_id: string;
  draft_count: number;
  approved_count: number;
  executed_count: number;
  approval_rate_pct: number;
  reference_coverage_pct: number;
  rebalance_runs: number;
  llm_cio_run_pct: number;
  agent_mode_hint: string;
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

export type ReviewSummary = {
  portfolio_id: string;
  open_count: number;
  due_count: number;
  overdue_count: number;
  pending_memory_count: number;
  review_due_days: number;
};

export type PendingMemoryDecision = {
  decision_id: string;
  symbol: string;
  name: string;
  action: string;
  return_pct: number;
  outcome_summary?: string;
  pending_memory_id?: string | null;
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
  executed_at?: string;
  days_since_execution?: number | null;
  review_due?: boolean;
  review_due_days?: number;
  material_move?: boolean;
  urgency?: "overdue" | "due" | "ok" | "unknown";
  pending_memory_id?: string | null;
};

export type ResearchQuality = {
  symbol: string;
  found: boolean;
  has_view?: boolean;
  completion_pct?: number;
  sections?: Record<string, boolean>;
  has_scenarios?: boolean;
  age_days?: number | null;
  quality_score?: number;
  quality_grade?: string;
  issues?: string[];
  gate?: { research_allowed: boolean; reason?: string };
};

export type DecisionCoverage = {
  decision_id: string;
  symbol: string;
  coverage_pct: number;
  checks: { label: string; covered: boolean; detail: string }[];
  evidence_grade?: string;
  evidence_score?: number;
  evidence_issues?: string[];
};

export type ReviewQuality = {
  decision_id: string;
  symbol: string;
  checklist: { item: string; ok: boolean; detail: string }[];
  quality_pct: number;
  memory_id?: string | null;
};

export type ReviewRunResult = {
  memory_id?: string;
  return_since_decision_pct: number;
  outcome_summary?: string;
  price_metadata?: Record<string, unknown>;
  review_quality?: ReviewQuality;
};

export type MonthlyRetrospective = {
  portfolio_id: string;
  year: number;
  month: number;
  summary_md: string;
  stats: Record<string, number>;
};

export type BacktestQualityReport = {
  sample_size: number;
  sharpe?: number | null;
  deflated_sharpe_hint?: number | null;
  overfitting_risk: string;
  message: string;
};

export type ExecutionQualityReport = {
  portfolio_id: string;
  items: {
    decision_id: string;
    symbol: string;
    slippage_vs_hint_pct?: number | null;
    quality_flag: string;
  }[];
  flagged_count: number;
  summary: string;
};

export type MacroScenario = {
  id: string;
  name: string;
  description: string;
  tilts: Record<string, number>;
  watchlist_actions?: string[];
};

export type AttributionReport = {
  sector_attribution: { sector: string; unrealized_pnl: number; contribution_pct: number }[];
  symbol_attribution?: {
    symbol: string;
    unrealized_pnl: number;
    weight_pct: number;
    contribution_pct: number;
  }[];
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
