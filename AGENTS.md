# AGENTS.md

## 项目概览

`copilot-test` 当前为**空脚手架仓库**：仅包含 `README.md`（标题）与 MIT `LICENSE`，无应用源码、依赖清单或 CI/容器配置。

## 常用命令

当前仓库**未定义** lint、测试、构建或开发启动命令。添加语言/框架后，请在本节与 `README.md` 中补充真实命令。

| 任务 | 命令 |
|------|------|
| Lint | （未配置） |
| Test | （未配置） |
| Build | （未配置） |
| Dev run | （未配置） |

## Cursor Cloud specific instructions

- **依赖安装**：无需安装；VM 启动时的 `update_script` 为无操作（`true`），在仓库引入 `package.json`、`pyproject.toml` 等之前保持不变。
- **必须运行的服务**：无。无 Docker Compose、数据库或开发服务器配置。
- **验证环境**：在仓库根目录执行 `git status` 与 `ls` 即可确认工作区与 Git 正常；无可运行的应用进程。
- **添加应用后**：在 `update_script` 中仅加入**幂等**的依赖刷新命令（例如 `npm ci`），将服务启动、迁移、测试等步骤写在本节，勿放入 `update_script`。
