#!/usr/bin/env bash
# 云服务器首次安装：Docker + 克隆仓库 + 启动 AIMS
# 用法（在 VPS 上）:
#   curl -fsSL https://raw.githubusercontent.com/chenluwu2026/copilot-test/main/scripts/bootstrap-vps.sh | bash
# 或克隆后: sudo bash scripts/bootstrap-vps.sh
set -euo pipefail

REPO_URL="${AIMS_REPO_URL:-https://github.com/chenluwu2026/copilot-test.git}"
INSTALL_DIR="${AIMS_INSTALL_DIR:-/opt/aims/copilot-test}"
BRANCH="${AIMS_BRANCH:-main}"
PORT="${AIMS_PORT:-8080}"

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    echo "==> Docker 已安装: $(docker --version)"
    return
  fi
  echo "==> 安装 Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker 2>/dev/null || true
}

clone_or_update() {
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    echo "==> 仓库已存在，更新..."
    git -C "$INSTALL_DIR" fetch origin "$BRANCH"
    git -C "$INSTALL_DIR" checkout "$BRANCH"
    git -C "$INSTALL_DIR" reset --hard "origin/$BRANCH"
  else
    echo "==> 克隆到 $INSTALL_DIR ..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR"
  fi
}

write_env_if_missing() {
  local env_file="$INSTALL_DIR/.env"
  if [[ -f "$env_file" ]]; then
    return
  fi
  local origin="http://127.0.0.1:${PORT}"
  if [[ -n "${AIMS_PUBLIC_HOST:-}" ]]; then
    origin="http://${AIMS_PUBLIC_HOST}:${PORT}"
  fi
  cat >"$env_file" <<EOF
# 服务器本地配置（勿提交 git）
CORS_ORIGINS=${origin},http://127.0.0.1:${PORT}
RUN_SEED=true
DATA_PROVIDER=akshare
AIMS_PORT=${PORT}
EOF
  echo "==> 已生成 $env_file（有数据后请将 RUN_SEED=false）"
}

main() {
  if [[ "$(id -u)" -ne 0 ]] && ! groups | grep -q docker; then
    echo "建议 root 运行，或将当前用户加入 docker 组后重新登录" >&2
  fi

  install_docker
  clone_or_update
  write_env_if_missing

  export AIMS_ROOT="$INSTALL_DIR"
  export AIMS_PORT="$PORT"
  bash "$INSTALL_DIR/scripts/deploy.sh"

  echo ""
  echo "=============================================="
  echo " AIM S 已启动"
  echo " 访问: http://<你的公网IP>:${PORT}"
  echo " 目录: ${INSTALL_DIR}"
  echo ""
  echo " 配置 GitHub 自动部署见 docs/DEPLOY.md § 自动部署"
  echo "=============================================="
}

main "$@"
