# 文档索引

面向人工与 Agent 的规范与流程说明；实现细节以**当前仓库代码**与 `contracts/tool.manifest.schema.json` 为准。

## 建议阅读顺序

1. **`PROJECT_AND_AGENT_GUIDE.md`** — 仓库是什么、目录职责、本地端口、质量闸门、给 Agent 的上下文与提示词骨架。
2. **`TOOL_INTEGRATION_STANDARD.md`** — 接入新工具或改管理页的硬约束（路由、权限、审计、UI、分页、角色）。
3. **`templates/NEW_TOOL_AGENT_TEMPLATE.md`** — 需求表模板；复制为新文件后填写再 @ 给 Agent。
4. **`MOS_TOOLBOX_REBUILD_BASELINE.md`** — 自旧 `ref/toolboxweb` 迁入时的**能力范围**与接口草案（单工具 + UAT/LIVE 切换等）。
5. **`PORTABLE_PACKAGING_AGENT_RUNBOOK.md`** — Windows 可移植包（无 Python/Node）的打包、验收与排障；产物目录为 `release/toolbox-portable`（由 `scripts/build-release.ps1` 生成，默认不纳入版本库）。

## 文档一览

| 文档 | 用途 |
|------|------|
| `PROJECT_AND_AGENT_GUIDE.md` | 总览、架构、Agent 协作流程 |
| `TOOL_INTEGRATION_STANDARD.md` | 工具接入规范（主规范） |
| `templates/NEW_TOOL_AGENT_TEMPLATE.md` | 新工具需求模板 |
| `MOS_TOOLBOX_REBUILD_BASELINE.md` | MOS 单工具重构范围与契约草案 |
| `PORTABLE_PACKAGING_AGENT_RUNBOOK.md` | 便携打包作业手册 |
| `REMOTE.md` | Git 远程仓库地址与推送 / 克隆命令 |

## 环境与数据库（避免歧义）

- **首次配置**：复制 **`backend/.env.example`** → **`backend/.env`**，再填写真实连接串与密钥（`.env` 不提交）。
- **连哪个库**：只由 **`backend/.env` 的 `DATABASE_URL`** 决定（见 `app/core/config_simple.py`）。
- **PostgreSQL**：`DATABASE_URL` 为 `postgresql+...` 时，应用**不**使用仓库里的 `backend/app.db`；该文件若存在多为历史文件，可自行处理。
- **SQLite**：仅当 `DATABASE_URL` 为 `sqlite:///./app.db` 或未配置（代码默认）时，才使用 **`backend/app.db`**。

更完整的说明见 **`PROJECT_AND_AGENT_GUIDE.md`** §1.3、§1.9。

## 持续集成

- **GitHub Actions**：`.github/workflows/ci.yml`（`main` / `master` 的 push 与 PR）：工具 manifest 校验、插件边界检查、`frontend` 生产构建。
- **本地对齐**：根目录 `powershell -File scripts/run-ci-tool-checks.ps1` + `frontend` 下 `pnpm run build`。

## 远程仓库（Git）

- **HTTPS**：`https://github.com/mjnn/Toolbox.git` · **默认分支**：`main`
- **说明与常用命令**（克隆、推送、`remote` 补配）：**`REMOTE.md`**（本目录）

## 相关非 docs 路径

| 路径 | 说明 |
|------|------|
| `.cursor/rules/tool-plugins.mdc` | Cursor：优先改插件与 `registry.ts`、合并前跑 CI 脚本 |
| `contracts/tool.manifest.schema.json` | 各插件 `tool.manifest.json` 的 JSON Schema |
| `scripts/run-ci-tool-checks.ps1` | Manifest 校验与插件边界检查 |
| `scripts/start-dev.ps1` / 根目录 `start-dev.cmd` | 本地并发启动前后端 |
| `ref/README.md` | `ref/` 目录说明（旧版源码与归档） |
