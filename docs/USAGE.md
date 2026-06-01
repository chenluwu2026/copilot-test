# AIMS 使用指南

模拟盘 + 人工批准。详见 [INTEGRATION.md](./INTEGRATION.md)、[DATA_AND_AGENTS.md](./DATA_AND_AGENTS.md)。

## 日课流程

画像/股票池 → 数据同步 → 研究 → 组合「生成 AI 调仓」→ 收件箱批准/确认 → 复盘激活记忆。

## LLM（A）

```env
AGENT_MODE=llm
OPENAI_API_KEY=sk-...
CIO_DECISION_MODE=batch
```

画像页或 `/api/v1/agents/config` 查看 `llm_active`。失败自动回退规则引擎。

## 定时（C/D）

```env
DATA_SYNC_CRON_ENABLED=true
DAILY_REPORT_CRON_ENABLED=true
REVIEW_CRON_ENABLED=true
NEWS_SYNC_CRON_ENABLED=true
```

## 登录（D，可选）

```env
JWT_SECRET=随机长字符串
AUTH_PASSWORD=你的口令
```

`POST /api/v1/auth/login` → 前端设置 `NEXT_PUBLIC_API_KEY` 或后续 Bearer（当前仍可用 X-API-Key）。

## 质量指标

`GET /api/v1/dashboard/metrics?portfolio_id=` — 批准率、证据引用率、LLM 占比。
