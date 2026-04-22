# 文档索引

面向人工与 Agent 的规范与流程说明；实现细节以**当前仓库代码**与 `contracts/tool.manifest.schema.json` 为准。

## 建议阅读顺序

1. **`PROJECT_AND_AGENT_GUIDE.md`** — 仓库是什么、目录职责、本地端口、质量闸门、给 Agent 的上下文与提示词骨架。
2. **`TOOL_INTEGRATION_STANDARD.md`** — 接入新工具或改管理页的硬约束（路由、权限、审计、UI、分页、角色）。
3. **`templates/NEW_TOOL_AGENT_TEMPLATE.md`** — 需求表模板；复制为新文件后填写再 @ 给 Agent。
4. **`MOS_TOOLBOX_REBUILD_BASELINE.md`** — 自旧 `ref/toolboxweb` 迁入时的**能力范围**与接口草案（单工具 + UAT/LIVE 切换等）。
5. **`PORTABLE_PACKAGING_AGENT_RUNBOOK.md`** — Windows 可移植包（无 Python/Node）的打包、验收与排障；产物目录为 `release/toolbox-portable`（由 `scripts/build-release.ps1` 生成，默认不纳入版本库）。打包默认仅附带 **`.env.example`**，部署机需自行生成 `.env`（可选 `-IncludeBackendEnv` 才会打入 `backend/.env`）。
6. **`RELEASE_RUNBOOK.md`** — 发布前闸门、生产环境变量、部署形态、冒烟顺序、回滚与 DB 约束（面向 Agent 与运维）。
7. **`EXTERNAL_PUBLIC_RELEASE.md`** — 外网版（Service ID 单工具）镜像发布、ECS 部署、连通性与离线包流程。
8. **`TOOL_VISIBILITY_ENV_RUNBOOK.md`** — 内外网环境识别与工具可见性配置（Admin/API/验证）。
9. **`PERF_AND_DB_OPTIMIZATION_RUNBOOK.md`** — 本项目数据库优化与性能验收的会话沉淀：Dashboard「数据库优化」页、后端优化点、k6 压测档位与达标流程。
10. **`FORM_FIELD_CONFIG_MODULE.md`** — 字段配置能力模块化沉淀（新增/删除字段、字段展示形式、动态表单复用实现）。
11. **`templates/FORM_FIELD_CAPABILITY_AGENT_TEMPLATE.md`** — 动态表单/字段配置需求的 Agent 标准提示词模板。

## 文档一览

| 文档 | 用途 |
|------|------|
| `PROJECT_AND_AGENT_GUIDE.md` | 总览、架构、Agent 协作流程 |
| `TOOL_INTEGRATION_STANDARD.md` | 工具接入规范（主规范） |
| `templates/NEW_TOOL_AGENT_TEMPLATE.md` | 新工具需求模板 |
| `MOS_TOOLBOX_REBUILD_BASELINE.md` | MOS 单工具重构范围与契约草案 |
| `PORTABLE_PACKAGING_AGENT_RUNBOOK.md` | 便携打包作业手册 |
| `RELEASE_RUNBOOK.md` | 生产/预发布发布流程、环境检查与冒烟 |
| `EXTERNAL_PUBLIC_RELEASE.md` | 外网版镜像发布、ECS 部署、离线包 |
| `TOOL_VISIBILITY_ENV_RUNBOOK.md` | 内外网环境识别与可见性治理 |
| `PERF_AND_DB_OPTIMIZATION_RUNBOOK.md` | 数据库优化与性能验收手册（含 k6 套件） |
| `FORM_FIELD_CONFIG_MODULE.md` | 字段配置模块复用手册（动态表单） |
| `templates/FORM_FIELD_CAPABILITY_AGENT_TEMPLATE.md` | 字段配置能力复用的 Agent 提示词模板 |
| `REMOTE.md` | Git 远程仓库地址与推送 / 克隆命令 |

## 环境与数据库（避免歧义）

- **开发机快捷启动（`start-dev.cmd`）**：默认使用 SQLite（`backend/app.db`）；如需按部署形态联调 PostgreSQL，请使用 `start-dev.cmd -Database postgres` 并配置 `backend/.env`。
- **部署/发布标准**：使用 PostgreSQL（`DATABASE_URL=postgresql+psycopg2://...`）；便携包与生产流程不使用 SQLite。
- **`backend/.env`**：用于 PostgreSQL 与密钥配置；`.env` 不提交版本库。

更完整的说明见 **`PROJECT_AND_AGENT_GUIDE.md`** §1.3、§1.3.1、§1.9。

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
| `.cursor/rules/ecs-public-release-workflow.mdc` | Cursor：外网版打包/推送/ECS 部署固定流程 |
| `.cursor/rules/tool-visibility-env-governance.mdc` | Cursor：内外网环境识别与工具可见性治理规则 |
| `.cursor/rules/form-field-capability-reuse.mdc` | 字段配置/动态表单需求的自动复用规则 |
| `.cursor/rules/form-field-capability-reuse-scoped.mdc` | 字段配置能力在相关文件上的范围增强规则 |
| `contracts/tool.manifest.schema.json` | 各插件 `tool.manifest.json` 的 JSON Schema |
| `scripts/run-ci-tool-checks.ps1` | Manifest 校验与插件边界检查 |
| `scripts/start-dev.ps1` / 根目录 `start-dev.cmd` | 本地并发启动前后端 |
| `ref/README.md` | `ref/` 目录说明（旧版源码与归档） |
