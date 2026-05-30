# 后端模块架构

推荐：**Monorepo** + API 服务（FastAPI 或 NestJS）+ Worker（Celery/BullMQ）+ 对象存储（研报 PDF）。

```
aims/
├── apps/
│   ├── api/                 # REST + WebSocket
│   └── worker/              # 定时任务、Agent 编排
├── packages/
│   ├── domain/              # 实体、用例、业务规则
│   ├── agents/              # Agent 提示词、工具、编排
│   └── data-connectors/     # 行情/公告/新闻适配器
└── schemas/                 # JSON Schema
```

---

## 模块一览

| 模块 | Phase | 职责 |
|------|-------|------|
| **auth** | 1 | 用户、会话、投资画像 CRUD |
| **security-master** | 1 | 标的、行业分类、股票池 |
| **portfolio** | 1 | 组合、持仓、现金、暴露计算 |
| **sim-trading** | 1 | 模拟下单、成交、成本、滑点模型 |
| **nav-pnl** | 1 | 日终净值、回撤、盈亏、归因占位 |
| **decision** | 1 | 决策单 CRUD、假设、引用、状态机 |
| **reporting** | 1 | 每日组合日报生成 |
| **market-data** | 1→2 | 行情拉取、缓存、复权 |
| **ingestion** | 2 | 新闻/公告/财报管道 |
| **structuring** | 2 | 非结构化 → structured_event |
| **research** | 2 | 研究页、十段式模板、版本管理 |
| **valuation** | 2→3 | 估值模型计算与快照 |
| **factor** | 3 | 因子信号、暴露报告 |
| **risk** | 3 | 约束检查、违规解释 |
| **agent-orchestrator** | 3 | 多 Agent 工作流 |
| **review** | 4 | 复盘、归因、记忆写入 |
| **memory** | 4 | Decision Memory 检索与规则同步 |
| **feedback** | 1→4 | 用户点评 → 记忆候选 |

---

## API 分层（整洁架构）

```
HTTP Controller
    → Application Service（用例）
        → Domain（实体 + 领域服务）
            → Repository Interface
                → Infra（Postgres / Redis / S3）
```

**关键领域服务（Domain Services）**

| 服务 | 逻辑 |
|------|------|
| `PositionCalculator` | 根据成交价更新持仓、均价 |
| `ExposureCalculator` | 行业/风格/单票权重 |
| `NavCalculator` | 市值+现金、日收益、回撤 |
| `RiskChecker` | 对比 `risk_limits`，返回 violations |
| `DecisionValidator` | 观点与交易分离；必须有假设与复盘条件 |
| `SimTradeExecutor` | 决策 approved → 生成 trade → 更新持仓 |

---

## REST API 草案（Phase 1 MVP）

### 组合与交易

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/v1/portfolios` | 列表 |
| POST | `/api/v1/portfolios` | 创建模拟组合 |
| GET | `/api/v1/portfolios/:id/summary` | 净值、暴露、Top 持仓 |
| GET | `/api/v1/portfolios/:id/positions` | 持仓 |
| GET | `/api/v1/portfolios/:id/nav?from=&to=` | 净值曲线 |
| POST | `/api/v1/portfolios/:id/trades` | 手动模拟交易 |
| POST | `/api/v1/portfolios/:id/rebalance/preview` | 调仓预览（Phase 3） |

### 股票池

| GET/POST | `/api/v1/watchlists` |
| POST | `/api/v1/watchlists/:id/items` |

### 决策（核心）

| GET | `/api/v1/decisions?portfolio_id=&status=&security_id=` |
| POST | `/api/v1/decisions` | 创建（人工或 Agent） |
| GET | `/api/v1/decisions/:id` | 含 assumptions + references |
| PATCH | `/api/v1/decisions/:id/status` | approve / execute / cancel |
| POST | `/api/v1/decisions/:id/feedback` | 用户点评 |

### 日报

| GET | `/api/v1/reports/daily?portfolio_id=&date=` |
| POST | `/api/v1/reports/daily/generate` | 触发日报（Worker） |

### Phase 2+

| GET | `/api/v1/events?security_id=&from=` | 结构化事件流 |
| GET | `/api/v1/research/:security_id` | 研究观点版本列表 |
| POST | `/api/v1/ingestion/upload` | 研报/纪要上传 |
| POST | `/api/v1/agents/workflows/:name/run` | 触发 Agent 流程 |

---

## Worker 定时任务

| Cron | 任务 | Agent/模块 |
|------|------|------------|
| 交易日 18:00 | 拉取日线、更新持仓市值 | market-data |
| 交易日 18:30 | 计算净值快照 | nav-pnl |
| 交易日 19:00 | 生成每日组合日报 | reporting |
| 交易日 20:00（Phase 3） | 调仓建议工作流 | agent-orchestrator |
| 周末 | 决策复盘扫描（开放决策） | review |

---

## 外部数据适配器（Data Agent）

先 Mock + 1 个真实源，接口统一：

```typescript
interface MarketDataProvider {
  getDailyBars(symbol: string, from: Date, to: Date): Promise<Bar[]>;
}
interface NewsProvider {
  fetchBySymbol(symbol: string, since: Date): Promise<RawArticle[]>;
}
```

| 数据类型 | MVP 建议源 |
|----------|------------|
| A股/港股日线 | Tushare / AkShare / 付费 API |
| 财报 | 巨潮 / 港交所披露易 |
| 新闻 | 财联社 RSS / 自定义爬虫 |
| 社交 | Phase 2 后期 |

---

## 技术选型建议

| 层 | 推荐 |
|----|------|
| API | FastAPI + Pydantic v2（Python 生态利于量化）或 NestJS（TS 全栈） |
| DB | PostgreSQL + Prisma / SQLAlchemy |
| Queue | Redis + Celery / BullMQ |
| Agent | LangGraph / 自研状态机 + OpenAI/Claude API |
| 前端 | Next.js 14 App Router + shadcn/ui + Recharts |
| 搜索 | PostgreSQL FTS → 后期 Meilisearch |

---

## 安全与审计

- 所有 `decisions` / `trades` 写入 append-only 审计日志表 `audit_logs`。
- Agent 调用记录 `agent_runs`，便于复现。
- API Key 与数据源凭证放密钥管理，不进库明文。
