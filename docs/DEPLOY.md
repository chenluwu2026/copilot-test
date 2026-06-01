# AIMS 线上部署指南（路线 C · 个人自用）

目标：**一个 URL 打开完整产品**（组合、决策、研究、数据同步），手机/电脑都能用，并可持续 `git push` 更新。

---

## 方案对比

| 方案 | 适合 | 月成本 |
|------|------|--------|
| **A. Docker Compose（推荐）** | 有云服务器 / 家里 NAS | 服务器费用 |
| **B. Railway** | 不想管服务器 | 免费额度内 ~0 |
| **C. 静态预览** | 只看 UI | 免费 |

静态预览（无交互）：https://chenluwu2026.github.io/copilot-test/

---

## 方案 A：Docker 一键部署（推荐）

### 要求

- 安装 Docker + Docker Compose
- 开放端口 `8080`（可改）

### 步骤

```bash
git clone https://github.com/chenluwu2026/copilot-test.git
cd copilot-test
docker compose -f docker-compose.prod.yml up -d --build
```

浏览器打开：**http://你的服务器IP:8080**

- 首次启动自动建表 + 种子数据（`RUN_SEED=true`）
- 数据存在 Docker volume `aims_pg`，重启不丢

### 首次在云服务器安装（约 5 分钟）

在 **VPS 上**执行（需 root 或 docker 组用户；安全组/防火墙放行 **8080**）：

```bash
# 合并 main 后可用；或指定分支：
# export AIMS_BRANCH=cursor/deploy-online-a5cb
export AIMS_PUBLIC_HOST=你的公网IP   # 可选，用于写入 CORS
curl -fsSL https://raw.githubusercontent.com/chenluwu2026/copilot-test/main/scripts/bootstrap-vps.sh | bash
```

默认安装目录：`/opt/aims/copilot-test`，访问 `http://公网IP:8080`。

### 更新版本（手动）

```bash
cd /opt/aims/copilot-test
bash scripts/deploy.sh
```

### Windows 本地（Docker Desktop）

首次克隆与启动：

```powershell
git clone https://github.com/chenluwu2026/copilot-test.git
cd copilot-test
docker compose -f docker-compose.prod.yml up -d --build
```

浏览器打开：**http://localhost:8080**

**拉取 main 最新代码后更新**（保留数据库 volume）：

```powershell
cd D:\AIMS\copilot-test   # 你的实际路径
git checkout main
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
```

验证：`docker compose -f docker-compose.prod.yml ps`，访问 `http://localhost:8080/health` 或通过 Caddy 打开首页。

可选环境变量（`docker-compose.prod.yml` 的 `api` 服务 `environment`）：

| 变量 | 说明 |
|------|------|
| `DATA_SYNC_CRON_ENABLED=true` | 每日自动同步行情/公告 |
| `AUTO_NAV_AFTER_SYNC=true` | 同步成功后自动记净值点 |
| `AUTO_DAILY_REPORT_AFTER_SYNC=true` | 同步成功后生成日报 |
| `REBALANCE_CRON_ENABLED=true` | 定时生成 CIO 调仓草案（不自动成交） |
| `AGENT_MODE=llm` + `OPENAI_API_KEY` | 启用 LLM CIO |

### 自动部署（push 到 main 即更新 VPS）

**我（Cloud Agent）无法直接登录你的云服务器**，除非你把 SSH 私钥临时提供到对话里（不推荐）。推荐用 **GitHub Actions** 在你 push 后自动 SSH 部署——配置一次，之后每次合并 `main` 都会重建容器。

#### 1. 服务器准备

- 已用上面的 `bootstrap-vps.sh` 装好，且 `http://IP:8080/health` 返回 ok
- 为 GitHub Actions 单独建部署公钥（不要复用个人私钥）：

```bash
ssh-keygen -t ed25519 -C "github-actions-aims" -f ~/aims_deploy -N ""
cat ~/aims_deploy.pub >> ~/.ssh/authorized_keys   # 或部署专用用户的 authorized_keys
```

#### 2. GitHub 仓库 Secrets（Settings → Secrets and variables → Actions）

| Secret | 示例 | 说明 |
|--------|------|------|
| `VPS_HOST` | `1.2.3.4` | 公网 IP 或域名 |
| `VPS_USER` | `root` | SSH 用户名 |
| `VPS_SSH_KEY` | `-----BEGIN OPENSSH...` | `aims_deploy` **私钥**全文 |
| `VPS_DEPLOY_PATH` | `/opt/aims/copilot-test` | 与 bootstrap 目录一致 |
| `VPS_PORT` | `22` | 可选，非 22 时填写 |

#### 3. 启用自动部署开关（Repository Variables）

Settings → Secrets and variables → **Actions** → **Variables**：

| Variable | 值 |
|----------|-----|
| `VPS_DEPLOY_ENABLED` | `true` |
| `VPS_PORT` | `8080`（可选，给部署脚本健康检查用） |

设置后，向 `main` 推送涉及 `apps/`、Dockerfile、`docker-compose.prod.yml` 等的提交会触发 [`.github/workflows/deploy-vps.yml`](../.github/workflows/deploy-vps.yml)。

未设 `VPS_DEPLOY_ENABLED` 时，仍可在 Actions 页 **手动 Run workflow**（`workflow_dispatch`）。

#### 4. 验证

1. 改一行 README 推到 `main`
2. Actions → **Deploy VPS** 变绿
3. 浏览器刷新站点，确认新版本

有数据后请在服务器 `.env` 里设 `RUN_SEED=false`，避免每次部署重复灌种子。

### 环境变量（可选，编辑 `docker-compose.prod.yml`）

| 变量 | 说明 |
|------|------|
| `API_KEY` | 设置后请求需带头 `X-API-Key`（防陌生人扫端口） |
| `DATA_PROVIDER` | `akshare` 或 `mock` |
| `RUN_SEED` | 仅首次 `true`，有数据后改 `false` |

### 手机访问

- 服务器有公网 IP：直接 `http://IP:8080`
- 建议前面加 **HTTPS**（Caddy 自动证书 / Cloudflare Tunnel / 宝塔反代）

---

## 方案 B：Railway（免运维 · 已配套）

连 GitHub 后 **push 自动部署**，无需 VPS。项目内包含：

- `railway.api.toml` / `railway.web.toml` — 分服务构建与健康检查  
- `deploy/railway.*.vars.example` — 变量模板（含 `${{aims-api.RAILWAY_PUBLIC_DOMAIN}}` 引用）  
- API 支持 `CORS_ALLOW_RAILWAY=true`、Railway Postgres SSL  

**逐步图文说明见 [`docs/DEPLOY_RAILWAY.md`](./DEPLOY_RAILWAY.md)**（约 15 分钟配完 Postgres + API + Web）。

快速变量示例：

```env
# API 服务
DATABASE_URL=${{Postgres.DATABASE_URL}}
RUN_SEED=true
CORS_ALLOW_RAILWAY=true

# Web 服务（服务名 aims-api 需与 Dashboard 一致）
NEXT_PUBLIC_API_URL=https://${{aims-api.RAILWAY_PUBLIC_DOMAIN}}
API_URL=https://${{aims-api.RAILWAY_PUBLIC_DOMAIN}}
```

> Railway 免费额度有限；长期 heavy 使用更推荐方案 A。

---

## 方案 C：仅本地开发

```bash
# 终端 1
cd apps/api && pip install -r requirements.txt
export DATABASE_URL=postgresql://aims:aims@localhost:5432/aims  # 或 sqlite
export RUN_SEED=true
python3 -m uvicorn app.main:app --reload --port 8000

# 终端 2
cd apps/web && npm install && npm run dev
```

---

## 架构说明

```
浏览器
   │
   ▼
Caddy :8080  ──/api/v1──►  FastAPI (api)
   │                      PostgreSQL
   └──/*────►  Next.js (web)
```

同源部署时前端请求 `/api/v1`，无需配置 CORS 公网双域名。

---

## 常见问题

**Q: 页面能开但数据为空？**  
A: API 未启动或 CORS 未包含前端域名；检查 `docker compose logs api`。

**Q: 同步行情失败？**  
A: 容器需能访问外网；AkShare 源不稳定时可设 `DATA_PROVIDER=mock`。

**Q: 如何备份？**  
A: `docker compose exec db pg_dump -U aims aims > backup.sql`

---

## Railway 定时拉数（Cron）

在 Railway 项目添加 **Cron Job**（或外部 cron），每日执行：

```bash
curl -X POST "https://<你的 API 域名>/api/v1/data/sync/cron" \
  -H "X-Cron-Secret: <与 API 环境变量 CRON_SECRET 相同>"
```

API 需设置 `CRON_SECRET`；若同时设 `DATA_SYNC_CRON_ENABLED=true`，进程内也会在 18:30 自动同步。

---

## 后续开发流程

1. 本地改代码 → `docker compose -f docker-compose.prod.yml up -d --build` 验证  
2. `git push` → 合并 **main**  
3. **VPS**：GitHub Actions 自动 `deploy.sh`；或服务器手动 `bash scripts/deploy.sh`  
4. **Railway**：连 GitHub 后平台自动 redeploy
