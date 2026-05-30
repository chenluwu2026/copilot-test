#!/usr/bin/env bash
# 在服务器上执行：拉取 main 并重建容器（GitHub Actions 也会调用此脚本）
set -euo pipefail

ROOT="${AIMS_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
BRANCH="${AIMS_BRANCH:-main}"
COMPOSE_FILE="${AIMS_COMPOSE_FILE:-docker-compose.prod.yml}"

cd "$ROOT"
echo "==> AIMS deploy @ $ROOT (branch $BRANCH)"

if ! command -v docker >/dev/null 2>&1; then
  echo "错误: 未安装 Docker，请先运行 scripts/bootstrap-vps.sh" >&2
  exit 1
fi

if [[ -d .git ]]; then
  git fetch origin "$BRANCH"
  git checkout "$BRANCH"
  git reset --hard "origin/$BRANCH"
else
  echo "警告: 非 git 目录，跳过 git pull" >&2
fi

docker compose -f "$COMPOSE_FILE" up -d --build --remove-orphans

# 等待入口就绪
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${AIMS_PORT:-8080}/health" >/dev/null 2>&1; then
    echo "==> 健康检查通过"
    docker compose -f "$COMPOSE_FILE" ps
    exit 0
  fi
  sleep 2
done

echo "警告: /health 未在预期时间内响应，请检查日志: docker compose -f $COMPOSE_FILE logs" >&2
docker compose -f "$COMPOSE_FILE" ps
exit 1
