# 方案 B：Railway 免运维部署（详细）

适合：**不想管 VPS**，用 GitHub 连 Railway，**push 自动部署**。一个项目里 3 块：**PostgreSQL + API + Web**。

---

## 架构

```
浏览器 ──HTTPS──► aims-web (*.up.railway.app)
                      │ NEXT_PUBLIC_API_URL
                      ▼
                 aims-api (*.up.railway.app) ──► Postgres (插件)
```

Web 与 API **分域名**（跨域）。API 已支持 `CORS_ALLOW_RAILWAY=true` 自动放行 `*.up.railway.app`，也可再设精确 `CORS_ORIGINS`。

---

## 一次性配置（约 15 分钟）

### 1. 创建 Railway 项目

1. 登录 https://railway.app ，用 GitHub 授权  
2. **New Project** → **Deploy from GitHub repo** → 选择 `copilot-test`  
3. 若 PR 未合并，先选分支 `cursor/deploy-online-a5cb` 或合并 `main` 后用 `main`

### 2. 添加 PostgreSQL

1. 项目画布 **+ New** → **Database** → **PostgreSQL**  
2. 服务名建议：`Postgres`（下文引用 `${{Postgres.DATABASE_URL}}`）

### 3. 创建 API 服务

1. **+ New** → **GitHub Repo** → 同一仓库（或 Duplicate 已有服务）  
2. 服务名：`aims-api`  
3. **Settings → Build**  
   - Builder: **Dockerfile**  
   - Dockerfile path: `Dockerfile.api`  
4. **Settings → Config-as-code**  
   - 配置文件路径：`/railway.api.toml`  
5. **Variables**（可从 [`deploy/railway.api.vars.example`](../deploy/railway.api.vars.example) 复制，按你的服务名改引用）：

```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
SCHEMAS_DIR=/schemas
RUN_SEED=true
DATA_PROVIDER=akshare
CORS_ALLOW_RAILWAY=true
```

6. **Networking** → **Generate Domain** → 得到如 `aims-api-production-xxxx.up.railway.app`  
7. 等待 Deploy 成功，访问 `https://<api域名>/health` 应返回 `{"status":"ok"}`

> 有真实数据后把 `RUN_SEED` 改为 `false`，避免每次部署重复种子。

### 4. 创建 Web 服务

1. 再 **+ New** → **GitHub Repo** → 同一仓库  
2. 服务名：`aims-web`  
3. **Build** → Dockerfile: `Dockerfile.web`  
4. **Config-as-code** → `/railway.web.toml`  
5. **Variables**（[`deploy/railway.web.vars.example`](../deploy/railway.web.vars.example)）：

```env
NEXT_PUBLIC_API_URL=https://${{aims-api.RAILWAY_PUBLIC_DOMAIN}}
API_URL=https://${{aims-api.RAILWAY_PUBLIC_DOMAIN}}
```

> `aims-api` 须与你在第 3 步起的 **服务名** 一致，否则引用变量要改名。

6. **Generate Domain** → 打开 `https://<web域名>/` 应看到 Dashboard

### 5. （可选）收紧 CORS

API 服务追加：

```env
CORS_ORIGINS=https://${{aims-web.RAILWAY_PUBLIC_DOMAIN}}
```

### 6. （可选）API Key

API：

```env
API_KEY=你的随机密钥
```

Web（需 **Redeploy** 以重新构建前端）：

```env
NEXT_PUBLIC_API_KEY=你的随机密钥
```

---

## 自动更新

Railway 已连 GitHub 时：

1. 本地开发 → `git push` 合并到 **main**（或你绑定的分支）  
2. **aims-api** 仅在 `apps/api/**`、`schemas/**` 等变更时重建（见 `watchPatterns`）  
3. **aims-web** 仅在 `apps/web/**` 变更时重建  

无需 VPS、无需 SSH。在 Railway Dashboard → **Deployments** 查看日志。

---

## 常见问题

| 现象 | 处理 |
|------|------|
| Web 能开但接口 401/网络错误 | 检查 `NEXT_PUBLIC_API_URL` 是否含 `https://`，且 API 已 Generate Domain |
| API 启动失败 / DB | 确认 `DATABASE_URL=${{Postgres.DATABASE_URL}}`；Railway 会自动带 SSL |
| CORS 报错 | 设 `CORS_ALLOW_RAILWAY=true` 或正确 `CORS_ORIGINS` |
| 改 API 地址后 Web 仍连旧地址 | Web 需 **Redeploy**（`NEXT_PUBLIC_*` 在构建时写入） |
| AkShare 同步慢/失败 | 容器需出网；可暂设 `DATA_PROVIDER=mock` |
| 免费额度用尽 | 升级 Hobby 或改用 [方案 A Docker VPS](./DEPLOY.md#方案-adocker-一键部署推荐) |

---

## 与方案 A 对比

| | Railway (B) | VPS Docker (A) |
|--|-------------|----------------|
| 运维 | 几乎为零 | 自己管服务器 |
| 费用 | 免费额度后按量 | 固定 VPS 月费 |
| 域名 | `*.up.railway.app` | 自己 IP:8080 / 反代 |
| 数据 | Postgres 插件 | Docker volume |

---

## 配置文件索引

| 文件 | 用途 |
|------|------|
| `railway.api.toml` | API 构建/健康检查/监听路径 |
| `railway.web.toml` | Web 构建/健康检查 |
| `Dockerfile.api` / `Dockerfile.web` | 镜像定义 |
| `deploy/railway.*.vars.example` | 变量模板 |
