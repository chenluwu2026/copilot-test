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

### 更新版本

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

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

## 方案 B：Railway（免运维）

Railway 适合个人：Postgres + API + Web，连 GitHub 自动部署。

### 1. 创建项目

1. 打开 https://railway.app ，用 GitHub 登录  
2. **New Project** → **Deploy from GitHub repo** → 选 `copilot-test`

### 2. 添加 PostgreSQL

- **Add Plugin** → **PostgreSQL**  
- 记下自动生成的 `DATABASE_URL`

### 3. 部署 API 服务

- **New Service** → **GitHub Repo** → 同一仓库  
- **Settings** → **Build** → Dockerfile path: `Dockerfile.api`  
- **Variables**：

```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
CORS_ORIGINS=https://你的web域名.up.railway.app
RUN_SEED=true
SCHEMAS_DIR=/schemas
DATA_PROVIDER=akshare
API_KEY=你自己设一串随机密码
```

- **Networking** → Generate domain，得到例如 `https://aims-api-production.up.railway.app`

### 4. 部署 Web 服务

- 再 **New Service**，Dockerfile: `Dockerfile.web`  
- **Variables**：

```env
NEXT_PUBLIC_API_URL=https://aims-api-production.up.railway.app
```

- 若设置了 `API_KEY`，Web 服务需同时设 `NEXT_PUBLIC_API_KEY`（同值），请求会自动带 `X-API-Key`

- Generate domain → `https://aims-web-production.up.railway.app`

### 5. 首次访问

打开 Web 域名 → 应能看到 Dashboard。  
到 **数据** 页点「一键全量」拉行情（AkShare 需能访问外网）。

> **注意**：Railway 免费额度有限，长期自用更划算用方案 A 小 VPS。

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

## 后续开发流程

1. 本地改代码 → `docker compose -f docker-compose.prod.yml up -d --build` 验证  
2. `git push main`  
3. Railway 用户自动 redeploy；Docker 用户在服务器 `git pull && compose up -d --build`
