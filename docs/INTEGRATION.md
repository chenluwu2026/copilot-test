# 系统整合说明

本文档描述各模块如何串联（事件 → 研究 → 调仓 → 复盘）。

## 事件 → 研究

- 新闻/公告入库（`ingest_news`、公告同步）后，若 `EVENT_RESEARCH_REFRESH_ENABLED=true`（默认），对**高敏感度**或**重大事件类型**自动调用 `refresh_stale_research`（不覆盖 `human` 定稿）。
- 手动：`POST /api/v1/events/{event_id}/refresh-research`
- UI：信息流卡片「刷新相关研究」；Dashboard「事件复审」区块。

## 定时任务

| 环境变量 | 默认 | 行为 |
|----------|------|------|
| `DATA_SYNC_CRON_ENABLED` | false | 18:30 全量同步 |
| `DAILY_REPORT_CRON_ENABLED` | false | 19:05 生成日报 |
| `REBALANCE_CRON_ENABLED` | false | 19:00 调仓草案 |
| `REBALANCE_CRON_CHAIN_AFTER_SYNC` | false | 同步成功后链式调仓 |

## 日报

- `GET /portfolios/{id}/reports/daily` — 读取当日已生成日报（不自动创建）
- `POST` 同路径 — 生成/更新日报并记 NAV
- 复盘页默认 GET；需更新时点「重新生成今日日报」。

## 策略规则 → 风控

- `ban_action`：禁止行业加仓（已有）
- `require_extra_review`：记忆激活后写入的规则，Risk 输出 `REQUIRE_EXTRA_REVIEW` violation，`extra_review_symbols` 供 Agent trace 使用

## 导航整合

- 调仓完成 → `/decisions/inbox`
- 顶栏 **Agent** → 运行列表与配置摘要
