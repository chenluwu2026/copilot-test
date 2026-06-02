# MVP 开发任务清单

按 **Phase 1 → 4** 排列。每项含：优先级、预估复杂度、验收标准。

复杂度：**S**（<1d） / **M**（2-3d） / **L**（4-7d） / **XL**（>1 周）

---

## Phase 1：组合与决策地基（必须先完成）

> **里程碑**：能手动/半自动记录一条完整决策，并看到净值曲线与日报。

### 1.1 工程脚手架

| ID | 任务 | 复杂度 | 验收 |
|----|------|--------|------|
| P1-01 | Monorepo 初始化（api + web + schemas） | M | CI 通过 lint/test |
| P1-02 | PostgreSQL + 迁移工具（Prisma/Alembic） | M | 本地 docker-compose 一键起 |
| P1-03 | 认证（邮箱 magic link 或简单 JWT） | M | 用户可登录 |
| P1-04 | `securities` 种子数据（50 只 A+H 样本） | S | 可搜索标的 |

### 1.2 组合与模拟交易

| ID | 任务 | 复杂度 | 验收 |
|----|------|--------|------|
| P1-10 | portfolios / positions / trades CRUD | M | API 文档齐全 |
| P1-11 | 模拟成交：更新持仓、均价、现金 | M | 买卖后权重正确 |
| P1-12 | 佣金与最小交易单位 | S | 港股 lot 校验 |
| P1-13 | 日终行情导入（先 CSV/API 一种） | M | 可更新市值 |
| P1-14 | nav_snapshots 日终批处理 | M | 净值曲线 30 点+ |
| P1-15 | pnl_records（持仓浮盈亏） | M | Portfolio 页展示 |

### 1.3 股票池

| ID | 任务 | 复杂度 | 验收 |
|----|------|--------|------|
| P1-20 | watchlists CRUD | S | 多列表 |
| P1-21 | watchlist_items + tier | S | 核心/跟踪/想法 |

### 1.4 决策日志（核心）

| ID | 任务 | 复杂度 | 验收 |
|----|------|--------|------|
| P1-30 | decisions 表 + JSON schema 校验 | M | 非法 JSON 拒绝 |
| P1-31 | assumptions + references 子表 | M | 详情页完整展示 |
| P1-32 | 决策状态机 draft→approved→executed | M | 执行生成 trade |
| P1-33 | Decisions 列表/详情前端 | L | 筛选、详情时间线 |
| P1-34 | 人工创建决策表单 | M | 不经过 Agent 可录入 |
| P1-35 | user_feedback 基础版 | S | 评分+纠正文本 |

### 1.5 日报与 Dashboard

| ID | 任务 | 复杂度 | 验收 |
|----|------|--------|------|
| P1-40 | daily_portfolio_reports 生成 | M | 含净值、Top 持仓、涨跌 |
| P1-41 | Dashboard KPI + 净值图 | M | 打开即见组合状态 |
| P1-42 | Portfolio 页持仓表+交易历史 | M | 与 API 一致 |
| P1-43 | Watchlist 页 | S | 增删改查 |

### Phase 1 完成定义（DoD）

- [x] 创建 1 个模拟组合，录入 ≥5 笔交易（种子 5 笔 + `GET /onboarding/status`）
- [x] 创建 ≥3 条决策（含假设、复盘条件、参考信息）
- [x] 至少 1 条决策 approve 并 execute（种子自动执行 add 决策）
- [x] 生成 5 个交易日净值点与 1 份日报（种子 backfill + daily report）
- [x] Decisions 页可检索并查看完整决策单

---

## Phase 2：研究与信息系统

| ID | 任务 | 复杂度 | 验收 |
|----|------|--------|------|
| P2-01 | news/filings 表 + 抓取适配器 1 个 | L | 每日新文章入库 |
| P2-02 | Structuring Agent + structured_events | L | 示例新闻正确提取 |
| P2-03 | Events 信息流页 | M | 过滤与卡片 |
| P2-04 | 财报 PDF/HTML 解析管道 | XL | 关键指标入库 |
| P2-05 | research_views 十段式模板 | L | Research 页展示 |
| P2-06 | 文档上传 S3 + 解析 | M | 纪要可检索 |
| P2-07 | Research Agent 生成草稿 | L | 人工可编辑保存 |
| P2-08 | Valuation Agent 情景分析 | L | 三情景+目标价区间 |
| P2-09 | research 与 decisions 分离展示 | S | 同页分栏 |

---

## Phase 3：AI 决策系统

| ID | 任务 | 复杂度 | 验收 |
|----|------|--------|------|
| P3-01 | agent_runs 观测 | M | 每次工作流可追踪 |
| P3-02 | Factor Agent + 基础因子 | L | 因子 Tab 有数据 |
| P3-03 | Risk Agent + risk_limits 检查 | M | 违规返回 violations |
| P3-04 | Portfolio Agent 调仓草案 | L | proposed_weights |
| P3-05 | CIO Workflow 端到端 | XL | 输出合法 decision draft |
| P3-06 | 决策审批 UI | S | Approve 流 |
| P3-07 | 调仓建议按钮 | M | 触发 workflow |
| P3-08 | Memory 检索注入 CIO（只读已有 memory） | M | prompt 含教训 |

---

## Phase 4：自我进化

| ID | 任务 | 复杂度 | 验收 |
|----|------|--------|------|
| P4-01 | decision_outcomes 跟踪 | M | 收益、回撤 |
| P4-02 | Review Agent 自动复盘 | L | 填写对错 |
| P4-03 | memory_entries CRUD + 确认流 | M | 用户激活教训 |
| P4-04 | strategy_rules 与 Risk 联动 | M | 违反规则拦截 |
| P4-05 | 归因分析（行业/选股） | XL | Review 页图表 |
| P4-06 | 回测模块（简化） | XL | 历史决策模拟收益 |
| P4-07 | 反馈 → profile 更新建议 | M | 偏好可见 |
| P4-08 | Review 页完整 | L | 开放决策看板 |

---

## 建议迭代顺序（前 4 周等价工作量）

```
Week A: P1-01 ~ P1-15（组合能跑）
Week B: P1-30 ~ P1-35 + Decisions 前端（灵魂）
Week C: P1-40 ~ P1-43 + Dashboard/Portfolio/Watchlist
Week D: P2-01 ~ P2-03（信息流入）
```

---

## 风险与依赖

| 风险 | 缓解 |
|------|------|
| 数据源不稳定 | 先 CSV + Mock，抽象 Provider |
| Agent 输出不稳定 | 强制 JSON Schema + 重试 + 人工 approve |
| 范围膨胀 | Phase 1 完成前不开 Agent 自动交易 |
| 估值模型过重 | Phase 2 先做 PE+历史分位数，DCF 后补 |

---

## 第一版交付包（给用户演示）

1. 7 个页面壳 + Phase 1 全功能（Decisions 完整）
2. 数据库迁移脚本
3. 示例组合 + 3 条示例决策 JSON
4. 产品宪法 + Agent 工作流文档（本 repo `docs/`）
