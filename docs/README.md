# 文档索引

面向人工与 Agent 的规范与流程说明；实现细节以**当前仓库代码**与 `contracts/tool.manifest.schema.json` 为准。

## 建议阅读顺序

1. **`PROJECT_AND_AGENT_GUIDE.md`** — 仓库是什么、目录职责、本地端口、质量闸门、给 Agent 的上下文与提示词骨架。
2. **`TOOL_INTEGRATION_STANDARD.md`** — 接入新工具或改管理页的硬约束（路由、权限、审计、UI、分页、角色）。
3. **`templates/NEW_TOOL_AGENT_TEMPLATE.md`** — 需求表模板；复制为新文件后填写再 @ 给 Agent。
4. **`MOS_TOOLBOX_REBUILD_BASELINE.md`** — 自旧 `ref/toolboxweb` 迁入时的**能力范围**与接口草案（单工具 + UAT/LIVE 切换等）。
5. **`PORTABLE_PACKAGING_AGENT_RUNBOOK.md`** — Windows 可移植包（无 Python/Node）的打包、验收与排障；产物目录为 `release/toolbox-portable`（由 `scripts/build-release.ps1` 生成，默认不纳入版本库）。打包时若存在 **`backend/.env`**，会一并复制到产物根目录 **`.env`**。
6. **`RELEASE_RUNBOOK.md`** — 发布前闸门、生产环境变量、部署形态、冒烟顺序、回滚与 DB 约束（面向 Agent 与运维）。

## 文档一览

| 文档 | 用途 |
|------|------|
| `PROJECT_AND_AGENT_GUIDE.md` | 总览、架构、Agent 协作流程 |
| `TOOL_INTEGRATION_STANDARD.md` | 工具接入规范（主规范） |
| `templates/NEW_TOOL_AGENT_TEMPLATE.md` | 新工具需求模板 |
| `MOS_TOOLBOX_REBUILD_BASELINE.md` | MOS 单工具重构范围与契约草案 |
| `PORTABLE_PACKAGING_AGENT_RUNBOOK.md` | 便携打包作业手册 |
| `RELEASE_RUNBOOK.md` | 生产/预发布发布流程、环境检查与冒烟 |
| `REMOTE.md` | Git 远程仓库地址与推送 / 克隆命令 |

## 环境与数据库（避免歧义）

- **首次配置**：复制 **`backend/.env.example`** → **`backend/.env`**，填写 **`DATABASE_URL=postgresql+psycopg2://...`** 与密钥（`.env` 不提交）。
- **仅 PostgreSQL**：应用**只**认 `DATABASE_URL` 中的 PostgreSQL 连接串；未配置或误配为 SQLite 时**启动失败**（见 `app/core/config_simple.py`）。
- **历史 `backend/app.db`**：若仍存在，仅为本地备份或遗留，应用不会读取。

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
