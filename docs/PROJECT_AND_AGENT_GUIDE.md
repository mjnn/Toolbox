---
title: MOS综合工具箱 — 项目介绍与 Agent 开发指导书
description: 仓库级架构说明、本地运行约定、以及使用 Cursor Agent 进行调整与扩展的标准流程。
version: 1.0
---

# MOS综合工具箱 — 项目介绍与 Agent 开发指导书

本文档面向**人工开发者**与 **Cursor / 其他 Agent**：说明本仓库是什么、如何本地运行、基底与工具插件如何分工，以及如何让 Agent **稳定、可验收**地完成改造与扩展。

**配套规范（实现细节以二者为准）**

| 文档 | 用途 |
|------|------|
| `docs/README.md` | **文档索引**与推荐阅读顺序（本文档为总览入口）。 |
| `docs/TOOL_INTEGRATION_STANDARD.md` | 工具接入硬约束：路由、权限、审计路径、UI、分页、角色与侧栏。 |
| `docs/templates/NEW_TOOL_AGENT_TEMPLATE.md` | 新工具需求表 + 与 Agent 多轮对齐的写法。 |
| `.cursor/rules/tool-plugins.mdc` | Cursor 规则：优先改插件与 registry，合并前跑检查脚本。 |

---

## 第一部分：完整项目介绍

### 1.1 项目定位

本仓库是 **「MOS综合工具箱」Web 平台**：在统一壳层内提供**多工具**的目录、授权、治理与使用记录；每个工具以**插件**形式挂载业务 API 与前端面板，避免把领域逻辑散落在「宿主」页面里。

**一句话**：宿主 = **门禁 + 工具目录 + 权限与审批 + 管理端聚合 + 访问观测**；工具 = **门禁内的业务能力**（API + 可选 UI）。

### 1.2 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3、TypeScript、Vite、Pinia、Element Plus、Vue Router |
| 后端 | FastAPI、SQLModel、**PostgreSQL**（部署与发布标准数据库；本地 `start-dev` 支持 SQLite 快捷模式）。JWT（python-jose） |
| 契约 | `contracts/tool.manifest.schema.json`（各插件 `tool.manifest.json` 校验） |
| 打包 | 可选：`scripts/build-release.ps1`（前端 build + PyInstaller 便携后端等） |

### 1.3 仓库顶层结构（维护时最常碰到的部分）

```
Toolbox_Project/
├── README.md                # 根目录快速入口（指向 docs）
├── .gitignore               # 单仓忽略：venv、node_modules、构建产物、本地 DB 等
├── backend/                 # FastAPI 应用（main.py 为入口）
├── frontend/                # Vue SPA
├── contracts/               # JSON Schema 等跨端契约
├── docs/                    # 规范、模板、本文档（见 docs/README.md 索引）
├── scripts/                 # 开发启动、CI 检查、发布脚本、历史 SQLite→PG 一次性迁移脚本等
├── ref/                     # 参考/归档：旧 toolboxweb 源码等（见 ref/README.md）
├── start-dev.cmd            # 根目录一键开发（调用 scripts）
```

**不必手改**：`frontend/dist/`、`backend/dist/`、`backend/build/`、`release/`、`node_modules/`、`backend/.venv/` 等为构建或依赖产物；便携包用 `scripts/build-release.ps1` 重新生成即可。

### 1.3.1 开发机与部署机（能力边界与关系）

| 角色 | 典型能力 | 在本项目中的职责 |
|------|----------|------------------|
| 开发机 | 权限较高，可安装 Node/Python、构建依赖 | 代码开发、`start-dev.cmd` 本地联调、构建便携包 |
| 部署机 | 权限受限，通常不能安装新软件 | 接收并运行已打包产物（`release/toolbox-portable`），按 `.env` 连 PostgreSQL |

**关系**：开发机负责“构建与验证”，部署机负责“运行与使用”。部署机不应承担源码构建或安装开发依赖的任务。

**便携打包与 `.env`**：执行 `scripts/build-release.ps1` 时，若存在 **`backend/.env`**，会**自动复制**到 `release/toolbox-portable/.env`（与 exe 同级），便于解压后可直接启动；若本机未配置 `backend/.env`，产物中不含 `.env`，需自行放置。复制内容含密钥，**外传安装包前请脱敏**。详见 **`docs/PORTABLE_PACKAGING_AGENT_RUNBOOK.md`** Step 2。

**数据库（开发与部署分场景）**

- **开发机（`start-dev.cmd`）默认 SQLite**：脚本会以参数 `-Database sqlite` 启动后端（默认值），数据库为 `backend/app.db`，用于快速联调。
- **开发机切 PostgreSQL**：执行 `start-dev.cmd -Database postgres`；后端按 `backend/.env` 的 `DATABASE_URL` 启动。
- **部署/发布机统一 PostgreSQL**：便携包与生产运行都应配置 `DATABASE_URL=postgresql+psycopg2://...`。
- **版本库约束**：根 `.gitignore` 忽略 `*.db`，避免误提交本地 SQLite 文件。

### 1.4 后端宿主职责（关键文件）

| 路径 | 职责摘要 |
|------|----------|
| `backend/main.py` | FastAPI 应用、CORS、静态资源、`/api/v1` 路由挂载、**访问日志中间件**（解析 `/api/v1/tools/{id}/features/...`）、SPA fallback、`/health`。 |
| `backend/app/api/v1/api.py` | 聚合 `auth`、`users`、`tools`、`permissions`、`admin`。 |
| `backend/app/api/v1/tools.py` | 工具列表/详情/发布记录；**必须在此 `include_router` 注册各工具插件路由**。 |
| `backend/app/api/v1/tools_common.py` | `ensure_tool_access`、工具不可用/过期、按工具名校验、管理权限辅助。 |
| `backend/app/api/v1/admin.py` | 超管/工具负责人侧治理 API。 |
| `backend/app/database.py` | 建表、轻量迁移、种子数据（系统角色、内置 `Tool`、行为目录同步等）。 |
| `backend/app/models.py` / `schemas.py` | 数据模型与 API 模型。 |
| `backend/app/services/tool_behavior_catalog.py` | 从 `Tool.behavior_catalog_json` 解析使用记录中的**中文行为名**。 |

### 1.5 工具插件（扩展时的主战场）

每个工具一个目录，例如：

- `backend/app/tools/plugins/service_id_registry/`
- `backend/app/tools/plugins/mos_integration_toolbox/`

内含 **`routes.py`**（业务路由，须满足统一功能路径前缀以便审计）与 **`tool.manifest.json`**（与 Schema 对齐的元数据与行为目录声明）。

### 1.6 前端宿主与注册表

| 路径 | 职责摘要 |
|------|----------|
| `frontend/src/views/Dashboard.vue` | 壳：侧栏、顶栏、主内容区。 |
| `frontend/src/views/ToolDetail.vue` | 工具**使用页**容器；通过注册表挂载各工具面板。 |
| `frontend/src/views/ToolManage.vue` | 工具**管理页**；首 Tab「通用管理」+ 注册表驱动的扩展 Tab。 |
| `frontend/src/tools/registry.ts` | **`Tool.name`（tool_key）→ 详情组件 / 管理 Tab 组件**。新工具**必须**在此注册；**禁止**在 `ToolDetail.vue` / `ToolManage.vue` 写 `tool.name === '...'` 分支。 |
| `frontend/src/api/*.ts` | 对后端 REST 的封装。 |
| `frontend/vite.config.ts` | 开发服务器端口与 **API 代理目标**（须与后端监听端口一致）。 |

### 1.7 本地开发端口（权威约定）

与 **`scripts/start-dev.ps1`**、**`frontend/vite.config.ts`** 保持一致：

| 服务 | 地址 |
|------|------|
| 前端（Vite） | `http://127.0.0.1:3000` |
| 后端（Uvicorn） | `http://127.0.0.1:3001` |
| 浏览器调 API | 仍走相对路径 `/api/v1/...`（由 Vite 代理到 3001） |

修改后端端口时，**必须**同步修改 `vite.config.ts` 中的 `server.proxy`，否则前端联调失败。

**开发启动参数（`start-dev.cmd`）**：

- 默认（SQLite 快捷模式）：`start-dev.cmd`
- 指定 PostgreSQL（读取 `backend/.env`）：`start-dev.cmd -Database postgres`

### 1.8 功能 URL 与审计（必须一致）

可被中间件识别并写入 `APIAccessLog` 的路径形态为：

```text
/api/v1/tools/{tool_id}/features/{feature}
```

`{feature}` 为 **`/features/` 之后的整段**，正则 **`[a-zA-Z0-9_/-]+`**（允许 `/` 表示子路径）。实现、manifest、`behavior_catalog` 与数据库中的 `Tool.behavior_catalog_json` **须同源**，否则使用记录中的中文行为名可能对不齐。

### 1.9 行为目录与数据库的注意事项

**数据库与连接**：与 §1.3 一致，**仅 PostgreSQL**。若仍持有**历史 SQLite 备份**（例如 `ref/app.db`），可一次性导入当前库（目标以 `.env` 中 `DATABASE_URL` 为准）：

```powershell
backend\.venv\Scripts\python.exe scripts/migrate_sqlite_to_postgres.py --sqlite ref/app.db
```

（脚本会 `TRUNCATE` 目标库相关表后再复制数据；执行前请确认目标库已备份。）

`database.py` 在 `Tool.behavior_catalog_json` **为空**时会用 `default_behavior_catalogs()` 填充。若你已落库后**再改**行为 key，需要**迁移或手工更新**对应行，否则历史日志或新日志的标签可能不符合预期。

### 1.9.1 生产运行：Uvicorn worker 与 PostgreSQL 连接池

**与打包脚本无关**：`scripts/build-release.ps1` 默认**顺序**构建；运行时并发由 **`backend/run_server.py`** 的 Uvicorn `workers` 控制（环境变量 `TOOLBOX_WORKERS`，未设置时默认 **2**）。在约 **20～50** 用户、峰值约 **10** 人同时访问、RDS **1 vCPU / 2GB** 的假设下，**2 个 worker** 为推荐起点；连接池默认 `SQLALCHEMY_POOL_SIZE=4`、`SQLALCHEMY_MAX_OVERFLOW=2`（每进程），详见 **`docs/PORTABLE_PACKAGING_AGENT_RUNBOOK.md` §3.1**。

### 1.10 质量闸门（合并前建议）

在仓库根目录执行：

```powershell
powershell -File scripts/run-ci-tool-checks.ps1
```

包含：manifest 与 `contracts/tool.manifest.schema.json` 校验、插件禁止直接 import `app.api.v1.admin` 的边界检查。

前端生产构建：`frontend` 目录下 `npm run build`。详细验收项见 `TOOL_INTEGRATION_STANDARD.md` §10。

---

## 第二部分：使用 Agent 进行调整与扩展

### 2.1 何时用 Agent、目标是什么

适合交给 Agent 的任务示例：新增工具插件、为现有工具加 API/管理 Tab、调整权限相关调用、对齐行为目录与路由、修分页与列表、按规范做小范围重构。

**不适合**在未读规范的情况下让 Agent「大改架构」或同时改宿主与多工具；应拆任务并分次提交。

### 2.2 给 Agent 的上下文打包（推荐最小集）

按任务类型选择附件（`@` 文件或粘贴摘要）：

| 任务 | 建议 @ 的文件 |
|------|----------------|
| 新工具全流程 | `docs/TOOL_INTEGRATION_STANDARD.md` + 你填好的 `docs/templates/my-tool-*.md` + `contracts/tool.manifest.schema.json` |
| 只改某一已有工具 | 该工具 `plugins/<name>/routes.py` + 对应前端组件 + `frontend/src/tools/registry.ts` |
| 改宿主行为（谨慎） | `backend/main.py`、`backend/app/api/v1/tools.py`、`ToolManage.vue` / `ToolDetail.vue` 中与任务直接相关的片段 |

**始终建议**附带 `.cursor/rules/tool-plugins.mdc` 所强调的边界：少动宿主、用 registry 扩展 UI。

### 2.3 Agent 执行顺序（减少返工）

1. 读 `TOOL_INTEGRATION_STANDARD.md` §0 建议顺序（基底 vs 工具 → 管理页 → 后端路径与审计 → 角色 → 提示词模板）。
2. 确认 `tool_key` 与数据库 `Tool.name`、前端 registry 键**三者一致**。
3. 后端：在插件中实现路由；在 `tools.py` 注册 router；种子与行为目录按 `database.py` / `tool_behavior_catalog.py` 约定更新。
4. 前端：API 方法、`registry.ts`、详情/管理子组件；列表**分页**与 §7.4 对齐。
5. 跑 `run-ci-tool-checks.ps1` 与 `npm run build`，并按 §10 做手工冒烟。

### 2.4 提示词模板（中文，可直接复制给 Agent）

```text
你在维护「MOS综合工具箱」仓库。请先阅读并已遵守：
- docs/TOOL_INTEGRATION_STANDARD.md（尤其 §6 功能路径 / §7 前端与分页 / §8 角色）
- .cursor/rules/tool-plugins.mdc

约束：
1. 工具业务 API 必须落在 /api/v1/tools/{tool_id}/features/... 下，feature 段允许嵌套斜杠，与 backend/main.py 及 contracts/tool.manifest.schema.json 一致。
2. 处理器内使用 ensure_tool_access（及工具停用时的策略），与现有插件一致。
3. 前端扩展通过 frontend/src/tools/registry.ts，不要在 ToolDetail.vue / ToolManage.vue 增加 tool.name 硬编码分支。
4. 列表必须分页；变更后运行：powershell -File scripts/run-ci-tool-checks.ps1，且 npm run build 通过。

本次任务（用中文写清）：<描述需求、验收标准、是否改数据库字段>
```

英文骨架可与规范文档 **§9** 模板组合使用（二者已对齐同一套路径与字符集约定）。

### 2.5 新工具的标准清单（Checklist）

- [ ] `tool.manifest.json` 通过 Schema；`feature_slugs` / `behavior_catalog` 与路由一致。
- [ ] `backend/app/api/v1/tools.py` 已 `include_router`。
- [ ] `database.py` 种子确保存在对应 `Tool` 行；`default_behavior_catalogs()` 含新工具（若需要默认中文行为名）。
- [ ] `registry.ts` 已映射详情面板与管理 Tab（若需要）。
- [ ] `run-ci-tool-checks.ps1` 与 `npm run build` 通过；§10 冒烟通过。

### 2.6 常见失误（Agent 与人类都需避免）

1. **忘记在 `tools.py` 注册插件**，导致 404 或路由不可达。
2. **功能路径不满足** `/features/...` 约定，使用记录无法关联 `tool_id`。
3. **在宿主页面写工具名分支**，后续工具增多时无法维护。
4. **行为目录未更新**，管理页「使用记录」中文名不准或回退为 slug 拼接。
5. **只改代码未改 Vite 代理**，本地前后端端口不一致。

### 2.7 安全与运维提示（给 Agent 的隐性约束）

- 生产环境勿开启 `TOOLBOX_BOOTSTRAP_USERS` 或依赖默认演示密码；见 `database.py` 中说明。
- 插件内**不要** import `app.api.v1.admin`（边界检查会失败）；管理类能力走既有 admin 约定或工具内受控接口。

---

## 第三部分：文档与规则索引

| 条目 | 路径 |
|------|------|
| 文档索引（阅读顺序） | `docs/README.md` |
| 工具接入规范（主） | `docs/TOOL_INTEGRATION_STANDARD.md` |
| 新工具需求模板 | `docs/templates/NEW_TOOL_AGENT_TEMPLATE.md` |
| 本文（总览 + Agent 流程） | `docs/PROJECT_AND_AGENT_GUIDE.md` |
| 便携打包手册 | `docs/PORTABLE_PACKAGING_AGENT_RUNBOOK.md` |
| MOS 重构范围基线 | `docs/MOS_TOOLBOX_REBUILD_BASELINE.md` |
| Cursor 工具插件规则 | `.cursor/rules/tool-plugins.mdc` |
| Manifest Schema | `contracts/tool.manifest.schema.json` |
| CI 脚本（本地） | `scripts/run-ci-tool-checks.ps1` |
| CI（GitHub） | `.github/workflows/ci.yml`（与上项 Python 检查 + `pnpm build` 对齐） |
| SQLite 备份导入 PostgreSQL | `scripts/migrate_sqlite_to_postgres.py`（见 §1.9） |
| `ref/` 说明 | `ref/README.md` |
| 后端环境变量模板 | `backend/.env.example`（复制为 `backend/.env`） |
| Git 远程说明 | `docs/REMOTE.md`（GitHub 地址与 `git push` 常用命令） |

---

**文档结束。** 若规范与代码出现冲突，以**当前仓库中的实现与 Schema**为准，并应通过 PR 同步修正文档（本文与 `TOOL_INTEGRATION_STANDARD.md` 会随版本迭代维护一致性）。
