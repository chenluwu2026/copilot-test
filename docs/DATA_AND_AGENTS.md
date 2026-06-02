# 数据层（方案 B）与智能 Agent（方案 A）

## 闭环包（最新）

| 能力 | 说明 |
|------|------|
| **增量行情** | `QUOTE_SYNC_INCREMENTAL=true`，从最后 K 线日前推 5 天补全 |
| **同步重试** | `QUOTE_SYNC_RETRIES=2`，失败标的记入 job.errors |
| **复盘真实收益** | 入场=成交价/执行日 K 线，出场=最新 K 线 |
| **复盘图表** | 复盘页柱状图 + 胜率统计 |
| **记忆沉淀** | 复盘自动生成 lesson；已复盘列表可点「记忆」 |

已有库执行：`scripts/migrate_add_price_metadata.sql`

---

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

## LLM 启用检查清单

- [ ] `OPENAI_API_KEY` 已设置（或兼容网关 `OPENAI_BASE_URL`）
- [ ] `AGENT_MODE=llm`（默认 `rule` 不会调用模型）
- [ ] Settings 页「Agent 健康检查」显示 **LLM 运行中**
- [ ] 调仓后收件箱 / Agent 运行详情可见 `cio_mode: llm`（失败则为 `rule` + fallback）
- [ ] 了解费用：`LLM_MODEL` 建议 `gpt-4o-mini`；失败自动回退规则引擎

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

---

## 真实 AI 决策（证据卷宗 + CIO）

### 能力概览

| 环节 | 说明 |
|------|------|
| **Decision Dossier** | 每标的组装研究/估值/因子/事件/财报/记忆/闸门 |
| **Valuation Agent** | 调仓前更新三情景 `scenario_analysis`（规则或 LLM） |
| **Research 刷新** | `CIO_REFRESH_RESEARCH=true` 时刷新过期 agent 草稿（不覆盖人工定稿） |
| **Portfolio LLM** | `AGENT_MODE=llm` 时权重草案可走模型，失败回退评级表 |
| **CIO LLM** | 基于 dossier 生成决策并写入 `decision_references` |
| **证据分** | 收件箱 A/B/C 徽章，低分草案优先展示 |

### 环境变量

```env
AGENT_MODE=llm
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
CIO_DECISION_MODE=batch          # batch | per_symbol
CIO_REFRESH_RESEARCH=false
CIO_MAX_SYMBOLS=12
REBALANCE_CRON_CHAIN_AFTER_SYNC=false   # 全量同步成功后自动跑调仓草案
```

### 成本参考（约 10 标的）

| 模式 | LLM 次数 | 质量 |
|------|----------|------|
| `per_symbol` CIO | ~10 | 高 |
| `batch` CIO | 1–2 | 中 |
| `rule` | 0 | 演示 |

推荐日常：`batch` Portfolio（1 次）+ `per_symbol` CIO（≤8），或全程 `batch` 省成本。

### 验收路径

1. 组合页 **生成 AI 调仓建议** → Agent 运行 `trace.dossiers` 有摘要  
2. 决策详情 **溯源** 面板可见卷宗摘要与证据等级  
3. 收件箱按证据 C→A 排序，Dashboard **事件复审** 展示 24h 内重大事件
