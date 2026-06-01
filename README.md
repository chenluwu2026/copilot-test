# AIMS — Agentic Investment Management System

AI 投资组合**模拟**决策系统：研究 → 决策 → 模拟交易 → 复盘 → 进化。

> 目标不是预测涨跌，而是按你的投资框架完成可追溯的模拟基金管理。

## 文档

完整架构设计见 [`docs/`](./docs/README.md)。模块串联见 [`docs/INTEGRATION.md`](./docs/INTEGRATION.md)。

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

## 快速预览界面（无需启动服务）

在浏览器打开静态 HTML 即可查看当前 UI 长什么样：

```bash
cd preview && python3 -m http.server 8080
# 打开 http://localhost:8080/aims-preview.html
```

或直接打开仓库内文件 `preview/aims-preview.html`。

GitHub Pages 静态预览（无 API 交互）：https://chenluwu2026.github.io/copilot-test/

## 线上部署（完整产品 · 推荐）

个人 VPS / 本机 Docker 一键启动（组合、决策、研究、数据同步均可交互）：

```bash
docker compose -f docker-compose.prod.yml up -d --build
# 或: make prod
```

浏览器打开 **http://localhost:8080**（服务器则换成公网 IP）。

**云服务器（方案 A）**：`scripts/bootstrap-vps.sh` + GitHub Actions 自动部署。

**Railway（方案 B）**：`docs/DEPLOY_RAILWAY.md` — Postgres + API + Web，push 自动更新。

详见 [`docs/DEPLOY.md`](./docs/DEPLOY.md)。

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

### 数据（方案 B）与 LLM Agent（方案 A）

- **数据中心** `/data`：质量看板、同步作业、后台全量、定时 Cron（见 [`docs/DATA_AND_AGENTS.md`](./docs/DATA_AND_AGENTS.md)）
- **LLM CIO**：`AGENT_MODE=llm` + `OPENAI_API_KEY`；失败自动回退规则引擎

### 行情 & 公告财报（AkShare）

- **数据中心** `/data`：同步行情 / 公告 / 财报 / 一键全量 / 后台全量
- A 股日线、港股日线、巨潮/东财公告、财报摘要；重要公告自动进入信息流
- 研究页展示真实 K 线与财报表格；`DATA_PROVIDER=mock` 可无网络降级
