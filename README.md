# AIMS — Agentic Investment Management System

AI 投资组合**模拟**决策系统：研究 → 决策 → 模拟交易 → 复盘 → 进化。

> 目标不是预测涨跌，而是按你的投资框架完成可追溯的模拟基金管理。

## 文档

完整架构设计见 [`docs/`](./docs/README.md)。

## 阶段规划

1. **Phase 1**：组合、模拟交易、净值、决策日志、日报（地基）
2. **Phase 2**：新闻/公告/财报结构化、研究页
3. **Phase 3**：多 Agent 协作与调仓建议
4. **Phase 4**：归因、决策记忆、策略进化

## 结构化输出

核心 JSON Schema 位于 [`schemas/`](./schemas/)：

- `decision_order.schema.json` — 决策单（系统核心）
- `structured_event.schema.json` — 信息结构化
- `research_view.schema.json` — 研究观点（与交易分离）
- `valuation_scenario.schema.json` — 估值情景
- `review_attribution.schema.json` — 复盘归因

## 本地运行（Phase 1 MVP）

```bash
# 1. 启动数据库
docker compose up -d db

# 2. API（另开终端）
cd apps/api && pip install -r requirements.txt
export DATABASE_URL=postgresql://aims:aims@localhost:5432/aims
uvicorn app.main:app --reload --port 8000

# 3. 前端（另开终端）
cd apps/web && npm install && npm run dev
```

打开 http://localhost:3000 — 首次启动 API 会自动种子数据（标的、组合、示例决策）。

或使用根目录 `make up` / `make api` / `make web`。

### Phase 2（已实现）

- **信息流** `/events`：结构化事件列表、筛选、新闻录入→自动结构化
- **公司研究** `/research`、`/research/[symbol]`：十段式基本面、估值情景、相关事件、研究生成草稿
- 升级数据库：删除 `data/aims.db` 后重启 API 以加载新表与种子

### Phase 3 & 4（已实现）

- **组合页** →「生成 AI 调仓建议」：Factor → Portfolio → Risk → CIO 工作流，输出决策草稿
- **研究页** → Factor Agent 因子得分
- **复盘页** → 待复盘决策、行业归因、记忆库激活、Agent 运行记录、简化回测
- 升级数据库：删除 `data/aims.db` 后重启 API

### 行情 & 公告财报（AkShare）

- **数据中心** `/data`：同步行情 / 公告 / 财报 / 一键全量
- A 股日线、港股日线、巨潮/东财公告、财报摘要；重要公告自动进入信息流
- 研究页展示真实 K 线与财报表格；`DATA_PROVIDER=mock` 可无网络降级
