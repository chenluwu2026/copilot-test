# 数据层（方案 B）与智能 Agent（方案 A）

## 方案 B · 数据

### 功能

| 能力 | API | 说明 |
|------|-----|------|
| 数据质量 | `GET /data/quality` | 覆盖率、分标的新鲜度 |
| 后台全量同步 | `POST /data/sync/all/async` | 立即返回 `job_id`，避免 HTTP 超时 |
| 作业状态 | `GET /data/sync/jobs/{id}` | 轮询后台任务 |
| 定时同步 | 环境变量 + APScheduler | 见下 |
| 外部 Cron | `POST /data/sync/cron` | Header `X-Cron-Secret` |

### 环境变量

```env
DATA_STALE_DAYS=3
DATA_SYNC_CRON_ENABLED=true
DATA_SYNC_CRON_TIME=18:30
DATA_SYNC_CRON_TZ=Asia/Shanghai
CRON_SECRET=随机字符串
```

### Railway Cron 示例

在 Railway 添加 Cron Job，每日调用：

```bash
curl -X POST "https://<api域名>/api/v1/data/sync/cron" \
  -H "X-Cron-Secret: <CRON_SECRET>"
```

### 前端

- **数据中心** `/data`：同步按钮、质量表、作业历史

---

## 方案 A · 智能（LLM）

### 开启 CIO LLM

```env
AGENT_MODE=llm
OPENAI_API_KEY=sk-...
# 可选兼容网关：
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
STRUCTURING_MODE=llm   # 新闻结构化也用 LLM（可选）
```

- `AGENT_MODE=rule`（默认）：规则引擎，CI 与无 Key 环境使用
- LLM 失败时 **自动回退** 规则 CIO
- 研究草稿 `generate-draft`、新闻结构化在 `AGENT_MODE=llm` 时同样可走模型

### 工作流不变

组合页 **生成 AI 调仓建议** → Factor / Portfolio / Risk（规则）→ **CIO（LLM 或规则）** → 决策草稿。

复盘页可点 Agent 运行记录查看 `trace` 与 `cio_mode`。

### 成本提示

每次调仓会对多个标的调用一次 JSON 模式 LLM；个人使用建议 `gpt-4o-mini` 或国产兼容端点。
