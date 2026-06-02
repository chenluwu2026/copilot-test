# 能力路线图（A–D）

| 阶段 | 能力 | 状态 |
|------|------|------|
| A | LLM 配置文档、Agent 配置 API | 已落地 |
| B | 复盘 LLM 增强、到期定时复盘 | 已落地 |
| C | 资讯定时同步、记忆检索加分 | 已落地 |
| D | Alembic、JWT 登录、Dashboard 质量指标 | 已落地 |

## 全量交付（本轮已完成）

| 能力 | 说明 |
|------|------|
| 日常闭环 | `DAILY_OPERATOR_PLAYBOOK.md`、Dashboard 六步状态机、`/onboarding/status` |
| 决策灵魂 | 时间线、低证据门禁、假设待验证、黄金链 seed |
| 研究深度 | 新鲜度提示、十段式占位、估值元数据 |
| Agent | `/agents/config/health`、调仓 trace |
| 产品化 | mock 横幅、高级折叠、部署 FAQ |

## 质量提升（Phase A–C，已落地）

| 阶段 | API / UI | 说明 |
|------|----------|------|
| A | `GET /research/symbol/{sym}/quality`、研究页质量面板 | 十段式完成度、闸门、情景 |
| A | `GET /decisions/{id}/coverage`、决策页卷宗对照 | 卷宗 vs CIO 覆盖度 |
| A | 复盘 `review_quality`、`GET /review/retrospective/{pid}` | 复盘清单、月度 Markdown |
| A | `test_golden_path_e2e.py` | seed + onboarding 全绿 E2E |
| B | `POST /data/ingest/financial-text` | 财报/公告文本 → 指标入库 |
| B | `memory_tier` + `embedding`、MEM-VEC 检索 | 分层记忆 + 本地向量相似度 |
| B | `examples/golden_path_fixtures.json` | CIO 评测 fixture |
| C | `symbol_attribution`、回测/执行质量 API | 归因增强、过拟合提示、滑点 |
| C | `GET /scenarios`、组合页宏观情景 | 静态情景库 |

## 二期 backlog（XL，不阻塞当前发布）

| ID | 项 | 说明 |
|----|-----|------|
| P2-04 | 财报 PDF/HTML 深度解析管道 | 关键指标自动入库 |
| P4-05 | 完整行业归因 | Review 页多维度归因 |
| MEM-VEC | 向量数据库记忆检索 | 替代/增强关键词 memory |
| MULTI | 多用户注册与隔离 | 个人 VPS 暂不需要 |

- 多用户注册（轻量，非 XL）
- 实盘券商接口（独立开关）
