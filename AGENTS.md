# AGENTS.md

## 项目概览

`copilot-test`（AIMS）为 Agentic 投资管理 MVP：FastAPI + Next.js + PostgreSQL，支持 Docker 一键部署。

## 常用命令

| 任务 | 命令 |
|------|------|
| API 测试 | `cd apps/api && pip install -r requirements.txt && pytest -q` |
| 生产部署 | `docker compose -f docker-compose.prod.yml up -d --build` |
| 前端无缓存重建 | `docker compose -f docker-compose.prod.yml build --no-cache web && docker compose -f docker-compose.prod.yml up -d web` |

详见 `docs/DEPLOY.md`、`docs/USAGE.md`、`docs/CAPABILITY_ROADMAP.md`。

## Cursor Cloud specific instructions

- **依赖安装**：`pip install -r apps/api/requirements.txt`；Web 需 `cd apps/web && npm ci`（若改前端）。
- **必须运行的服务**：本地开发需 PostgreSQL 或 `docker compose -f docker-compose.prod.yml up`；验证用 `curl http://localhost:8080/health`（经 Caddy）。
- **验证环境**：`cd apps/api && pytest -q`；`git status` 确认分支。
- **能力路线图 PR**：分支 `cursor/capability-roadmap-162c` 含 A–D（文档/复盘 Cron/资讯同步/登录与指标）。
