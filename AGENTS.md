# AGENTS.md

## 项目概览

AIMS（`copilot-test`）：AI 投资组合**模拟**决策系统。Monorepo：`apps/api`（FastAPI）、`apps/web`（Next.js）、`schemas/`、`docs/`。

## 常用命令

| 任务 | 命令 |
|------|------|
| 生产一键启动 | `docker compose -f docker-compose.prod.yml up -d --build` |
| API 测试 | `cd apps/api && python3 -m pytest tests/ -q` |
| 本地 API | `cd apps/api && uvicorn app.main:app --reload --port 8000` |
| 本地 Web | `cd apps/web && npm run dev` |

用户使用说明见 [`docs/USAGE.md`](docs/USAGE.md)。

## Cursor Cloud specific instructions

- **依赖安装**：Docker 生产路径无需在 VM 单独 `pip install`；开发 API 时 `pip install -r apps/api/requirements.txt`。
- **必须运行的服务**：`docker compose -f docker-compose.prod.yml` 启动 `db`、`api`、`web`、`caddy`（对外 8080）。
- **验证环境**：`curl http://localhost:8080/api/v1/health`（经 Caddy）；或 `docker compose -f docker-compose.prod.yml ps`。
- **改 `.env`**：重建 `api`/`web` 容器后生效；改导航等前端务必 `build --no-cache web`。
- **Schema 路径**：`apps/api/app/config.py` 向上查找含 `schemas` 的目录；容器内 `SCHEMAS_DIR=/schemas`。
