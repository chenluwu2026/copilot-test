# 基金经理一日操作剧本

> 目标：30 分钟内完成「同步 → 研究 → 调仓 → 批准 → 复盘」闭环。Dashboard 六步状态机与此文档一致。

## 开盘前（可选）

| 步骤 | 页面 | 动作 |
|------|------|------|
| 1 | `/settings` | 确认投资画像、股票池 ≥3 只核心标的 |
| 2 | `/data` | 若覆盖率 &lt;70% 或有过期标的，执行全量/增量同步 |

## 收盘后（推荐）

| 步骤 | 页面 | API / Cron |
|------|------|------------|
| 1 | `/data` | `POST /api/v1/data/sync/all` 或 Cron：`POST /api/v1/data/sync/cron`（`X-Cron-Secret`） |
| 2 | `/events` | 浏览高影响事件，必要时「刷新相关研究」 |
| 3 | `/research` | 维护十段式观点；数据过期时先同步 |
| 4 | `/portfolio` | 「生成 AI 调仓建议」→ CIO 草案 |
| 5 | `/decisions/inbox` | 批准（低证据 C 且无参考将被拦截）→ 执行 |
| 6 | `/review` | 到期复盘、激活记忆；`POST /portfolios/{id}/reports/daily` 生成日报 |

## 环境变量（无人值守）

```env
DATA_PROVIDER=akshare
DATA_SYNC_CRON_ENABLED=true
DATA_SYNC_CRON_TIME=18:30
DAILY_REPORT_CRON_ENABLED=true
REBALANCE_CRON_ENABLED=false   # 建议先手动批准
AGENT_MODE=llm                  # 可选
OPENAI_API_KEY=sk-...
```

## Phase 1 验收

`GET /api/v1/onboarding/status?portfolio_id=<id>` 返回五项均为 `ok: true`。

本地：`make onboarding-check`（使用 sqlite `.onboarding.db`）。

详见 [06-mvp-task-list.md](./06-mvp-task-list.md)。

## 质量检查（每日可选）

| 环节 | 页面 / API | 通过标准 |
|------|------------|----------|
| 研究 | `/research/[symbol]` · `GET .../quality` | 完成度 ≥60%、闸门通过、研究未过期 |
| 决策 | `/decisions/[id]` · `GET .../coverage` | 卷宗覆盖 ≥70%、证据非 C 级（若启用拦截） |
| 复盘 | `/review` · 运行复盘后 `review_quality` | 清单 ≥80%、激活关键记忆 |
| 月度 | 复盘页「生成月度复盘」 | Markdown 含执行/复盘统计 |
| 宏观 | `/portfolio` 情景卡片 | 对照当前环境选择 tilt |
