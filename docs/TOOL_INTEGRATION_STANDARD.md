---
title: MOS综合工具箱 — 工具标准接入规范
description: >-
  供 Agent / 人工在「不展开完整仓库上下文」的前提下，按统一约束实现新工具或改造管理页。
  与基底职责、路由、审计、UI 规范对齐。
version: 1.7
stack: Vue3 + Element Plus + TypeScript（前端）; FastAPI + SQLModel + PostgreSQL（`backend/.env` 的 `DATABASE_URL`，见 `docs/PROJECT_AND_AGENT_GUIDE.md` §1.3）
---

# MOS综合工具箱 · 工具标准接入规范

> **文档定位**：本文是「单文件上下文包」—— Agent 或开发者实现新工具时，**优先只携带本文件 + 具体工具需求**，无需默认加载整个仓库；实现时再按需打开对应路径。仓库级总览与文档索引见 `docs/PROJECT_AND_AGENT_GUIDE.md`、`docs/README.md`。

---

## 0. 给 Agent 的阅读顺序（提示词最佳实践）

按顺序执行，减少歧义与返工：

1. **先读「1～3」**：确认基底做什么、工具不做什么。
2. **再读「4～5」**：锁定管理页结构（选项卡）与视觉约束（必须一致）。
3. **然后读「6～7」**：后端路由、权限、审计与功能路径约定。
4. **再读「8」**：**主导航菜单**与 **`tool_user` / `tool_owner` / 超管** 分工（避免接工具时搞混入口与能力）。
5. **最后读「9」**：用提示词模板生成任务清单与验收项。

**约束写法**：文中 **必须 / 禁止** 为硬约束；**建议** 为推荐做法。

---

## 1. 审查结论（基底健康度）

| 项 | 状态 |
|----|------|
| 后端 `app` + `main` 全量语法检查 | 通过（`compileall`） |
| 前端 `vue-tsc` + 生产构建 | 通过 |
| 自动化测试 | 仓库内**无**独立测试套件；变更后至少本地构建 + 手工冒烟 |

**说明**：逻辑层面当前实现自洽；后续工具增多时建议为「权限 + 功能路径」补集成测试。

---

## 2. 架构原则：基底 vs 工具

### 2.1 基底（本仓库）承担的职责

- **身份与会话**：注册 / 登录、JWT；当前用户 **`/api/v1/users/me`**。注册需 **姓名、部门** 等字段，新账号需 **管理员审核** 后方可登录（工具业务逻辑无需感知，仅需知会「未登录 / 未审核用户进不来」）。
- **用户资料与账号生命周期**：个人资料（含部门等）、头像、改密；用户可 **注销本人账号**；**超级用户**可管理用户列表及注销非超管账号（**超管账号不可通过管理接口删除**）。实现新工具时不必调用这些接口，除非产品明确要求。
- **工具目录与元数据**：`Tool` 表；列表、详情只读信息。
- **授权与审批流**：申请、审批、`UserToolPermission`、到期时间。
- **工具负责人**：`ToolOwner`；负责人与管理员可操作管理类接口。
- **治理与可观测**：工具启用/停用、通知、**按工具维度的访问日志**（`APIAccessLog`：关联 `tool_id`、路径中的功能段 `feature_name`，并解析为 **中文行为说明** `behavior_label`，依据各工具的 **行为目录** `Tool.behavior_catalog_json`）。
- **管理端聚合 API**：`/api/v1/admin/tools/...`（状态、授权用户、使用记录、按工具维度的用户反馈等）。

### 2.2 单个「工具」应承担的职责

- **相对完整的业务能力**：领域模型、算法、外部集成、工具专属配置等。
- **通过受控 API 暴露**：在鉴权通过后，以统一风格提供「功能端点」。
- **不在基底重复实现**：与业务无关的账号体系、全局权限表结构等。

**一句话**：基底 = **门禁 + 目录 + 治理 + 观测**；工具 = **在门禁之内的业务系统**。

---

## 3. 路由与用户可见入口（约定）

| 路径 | 含义 |
|------|------|
| `/login`、`/register` | 登录、注册（未登录可访问） |
| `/` | 首页（MOS综合工具箱） |
| `/profile` | 个人资料 |
| `/tools` | 所有工具列表 |
| `/my-tools` | 我的工具（同组件 `Tools.vue`，`meta.toolsView === 'my'`） |
| `/tools/:toolId` | 工具使用页（面向最终用户的功能 UI） |
| `/tools/:toolId/manage` | 工具管理页（负责人/超管；通用治理 + 可扩展） |
| `/tools/:toolId/usage-logs` | **重定向**到 `/tools/:toolId/manage`（兼容旧链接） |
| `/permissions` | 权限申请与审批 |
| `/notifications` | 通知（点击项可跳转到关联页面） |
| `/users` | 用户管理（**仅超管**，`meta.requiresAdmin`） |
| `/audit-logs` | 审计日志（**仅超管**） |
| `/feedback-admin` | 反馈管理（**仅超管**） |

**本地开发端口（与仓库脚本、Vite 配置一致）**：前端 Vite `http://127.0.0.1:3000`；浏览器访问的 **`/api/v1`** 与 **`/static`** 由 `frontend/vite.config.ts` 代理到 **`http://127.0.0.1:3001`**（后端 Uvicorn，见根目录 `start-dev.cmd` / `scripts/start-dev.ps1`）。若你自行把后端绑到其他端口，请同步修改 Vite 的 `server.proxy` 目标。

侧栏有哪些项、谁看得见，见 **§8**。

通知点击跳转约定（宿主）：

- `permission` 通知：跳转到 `/permissions`
- `tool` / `tool_release` 通知：优先跳转到 `/tools/{related_id}`，无 `related_id` 时回退到 `/tools`
- 其他通知类型：仅标记已读，不强制跳转

---

## 4. 工具管理页：选项卡结构（标准目标）

**当前实现**：`ToolManage.vue` 已使用 **`el-tabs`**，顺序为：**工具专属管理 Tab 在前、通用管理（`name="general"`）在后**。通用管理内部再用二级 `el-tabs` 承载 **工具状态、版本发版与更新记录、已授权用户、工具使用记录、用户反馈**，便于快速定位配置。

### 4.1 固定选项卡：**通用管理**（与基底强绑定，所有工具一致）

必须包含（建议以二级 tab 拆分，而非长页面堆叠）：

1. **工具状态**：可用 / 暂不可用；与 `Tool.is_active` 及通知策略一致。
2. **已授权用户**：列表、筛选、取消授权（行为以现有 `admin` API 为准）。
3. **工具使用记录**：基于 `APIAccessLog`，列表以 **用户行为（中文）** 为主展示，不再以接口路径为主；关键词可检索行为说明或路径片段。**必须分页展示**。每个工具需在 `behavior_catalog_json`（与 manifest 中 `behavior_catalog`、种子数据保持一致）中穷举可调功能路径段与展示名；插件新增/变更路由时须同步更新目录。
4. **用户反馈**：本工具相关反馈列表（数据来自现有 admin 反馈接口；只读展示即可）。

**禁止**：在该选项卡内实现纯业务配置（例如某 OCR 引擎的阈值），除非该配置属于「运维级」且团队明确约定。

### 4.2 前置选项卡：**工具专属管理**

- 每个工具可有 **0～N** 个专属选项卡（例如「参数模板」「批处理队列」「对接凭证（脱敏展示）」）。
- **排序约定**：专属管理 tab **显示在通用管理前**；通用管理固定为最后一个顶层 tab。
- **必须**独立命名，不与「通用管理」混在同一卡片内堆叠过长页面（避免用户找不到基底能力）。
- 若某个工具专属 tab 内仍有多个模块（如规则/配置/日志），**必须继续使用二级 tab 分组**，避免在单页长卡片堆叠。

### 4.3 实现提示

- 使用 `el-tabs`：`通用管理` 固定 `name="general"`；工具扩展 `name` 用可读英文 slug。
- `ToolManage` 顶层 tab 与通用管理二级 tab 推荐与 URL query 同步（刷新后恢复），与现网行为保持一致。
- 路由仍为 **`/tools/:toolId/manage`**，**不**为每个工具新增顶层路由，除非有独立子应用嵌入方案。
- **工具使用页**：`ToolDetail.vue` 作为工具能力页容器，按工具类型渲染对应业务子组件，与基底卡片风格一致。

---

## 5. 视觉与交互：与基底一致（硬约束）

基底技术栈：**Element Plus** + 现有页面布局习惯（`el-page-header`、`el-card`、页面 `padding: 20px` 等）。

### 5.1 必须遵守

- **组件库**：组件来自 **Element Plus**；禁止引入第二套 UI 框架（除非项目层面统一升级）。
- **色彩与语义**：`type="primary"` 用于主操作；`success` / `warning` / `danger` / `info` 与现有列表、标签语义一致。
- **用户可见语言**：工具中面向最终用户的文案（按钮、标题、说明、提示、表单标签、弹窗、Toast、空状态、错误提示等）**必须使用中文**。后端返回给前端直接展示的 `detail/message` 也必须为中文。仅在工具本身的专有字段、协议字段、API 字段名、代码标识符等不可本地化场景下保留原文。
- **标题与正文**：页面标题参考现有 `.page-header-title`（加粗、字号约 18px）；辅助说明使用中性灰（如 `#909399`），与 `section-hint` 一类风格一致。
- **间距**：卡片间距、表单项与现有 `ToolManage` / `ToolDetail` 保持同级；**禁止**随机大圆角、渐变背景等与当前壳层冲突的视觉。
- **状态展示**：工具可用性使用 `el-tag`（成功/警告）与现有一致。

### 5.2 禁止

- 自定义「另一套」主色按钮色板覆盖全局。
- 在工具页使用与壳层冲突的字体层级（例如超大 H1 铺满屏）。
- 在管理页隐藏或弱化基底提供的「停用工具」「授权」等安全相关能力。

---

## 6. 后端接入清单

### 6.1 注册工具实体

- 在数据库中新增 `Tool` 记录（`name` **唯一**；`description`、`version`、`is_active`）。
- 种子数据可放在 `app/database.py` 的 seed 逻辑或迁移脚本中（团队任选其一，保持一致）。

### 6.2 工具功能 API（业务端点）

- 在 `app/api/v1/tools.py`（或按模块拆分的路由，再 `include_router`）增加端点。
- **必须**在处理器内调用现有 **`ensure_tool_access`**（或等价校验），并在 **`tool.is_active`** 为 false 时拒绝普通用户（`is_superuser` 可豁免）。
- 请求/响应模型放在 `app/schemas.py`，命名清晰。

### 6.3 工具功能与审计日志（重要）

全局中间件（`main.py`）对路径匹配以下模式时，会解析 **`tool_id`**、**`feature`（`/features/` 之后整段路径，可含子路径）** 并写入 `APIAccessLog`（含解析后的 **`behavior_label`**）：

```text
^/api/v1/tools/(?P<tool_id>\d+)/features/(?P<feature>[a-zA-Z0-9_/-]+)$
```

**必须**：业务功能 URL 满足：

- 前缀：`/api/v1/tools/{tool_id}/features/`
- `feature` 段的字符集为 `[a-zA-Z0-9_/-]`（可包含 `/` 表示子路径，如 `mos-manage/vehicle-rules`）。

示例：`POST /api/v1/tools/1/features/my-feature`

否则「工具使用记录」中可能无法正确关联 `tool_id` / `feature_name`。

### 6.4 管理类 API

- 复用 **`/api/v1/admin/tools/...`** 已有能力；新增的管理接口 **必须**校验 **`ensure_permission_reviewer`**（超管或工具负责人），与现有 `admin.py` 一致。

---

## 7. 前端接入清单

### 7.1 工具使用页（`/tools/:toolId`）

- 扩展 `ToolDetail.vue` 或按工具拆子组件并在该页组合。
- 调用 `toolsApi` 中对应方法（在 `frontend/src/api/tools.ts` 增加函数）。
- **必须**处理：`403`（无权限）、工具不可用时的提示（与现网 `el-alert` 行为一致）。

### 7.2 工具管理页（`/tools/:toolId/manage`）

- 「通用管理」选项卡已落地；新增工具时在本页 **`v-if` + 新 `el-tab-pane`** 或独立子组件。
- 顶层 tab 顺序：**工具专属管理在前，通用管理在后**。
- 通用管理内部模块（状态/发版/授权/使用记录/反馈）建议用二级 tab。
- 推荐将 tab 状态与分页状态写入 URL query（例如 `manageTab`、`manageGeneralTab`、`sidEntriesPage` 等），保证刷新后可恢复。
- **返回（全局约束）**：所有页面头部「返回」按钮都应优先使用 **浏览器历史** 回到上一次进入页面；若无站内上一页则按页面语义回退到默认路由（例如工具管理回退 `/tools`）。

### 7.3 通知页（`/notifications`）

- 通知项点击后应优先执行“标记已读”，再按通知类型执行跳转（见 §3）。
- 跳转规则应集中在统一的前端工具函数中维护，避免在多个页面复制分支逻辑。
- 新增通知类型时，需同步更新该规则函数与本节文档。

### 7.4 API 层

- `frontend/src/api/tools.ts`：工具功能调用。
- `frontend/src/api/admin.ts`：治理与工具管理侧已有接口（含授权用户、使用记录、反馈等）。
- `frontend/src/api/auth.ts`：登录、注册、当前用户等与工具无强耦合时一般无需改动。
- 新管理接口若属工具专属，**建议**仍走 `tools` 或独立 `admin` 前缀并在文档注明。

### 7.5 列表分页（新增硬约束）

- **所有列表展示的数据都必须分页展示**（包含工具使用页、工具管理页、系统管理页中的任意列表）。
- 后端列表接口必须支持 `skip/limit`（或等价参数）并返回 `total + items`（或等价分页结构）。
- 前端列表必须提供分页控件，并在筛选条件变化时重置到第一页再查询。
- 对于多 tab 管理页，建议将「当前 tab + 分页参数」写入 URL query，避免刷新丢失上下文。
- 如确有「全量数据」场景（例如导出），应通过专用导出接口实现，不得替代页面列表分页。

---

## 8. 主导航与角色

实现位置：`frontend/src/views/Dashboard.vue`（`el-header` + `el-aside` 侧栏 + `router` 菜单）。

### 8.1 侧栏菜单（自上而下）

| 菜单文案 | 路由 | 可见条件 |
|----------|------|----------|
| 用户管理 | `/users` | **仅** `userInfo.is_superuser` |
| 我的工具 | `/my-tools` | 全员 |
| 所有工具 | `/tools` | 全员 |
| 通知 | `/notifications` | 全员 |
| 个人资料 | `/profile` | 全员 |
| 权限管理 | `/permissions` | 全员 |
| 行为日志 | `/audit-logs` | **仅**超管 |
| 反馈管理 | `/feedback-admin` | **仅**超管 |

顶栏右侧为头像与下拉：**个人资料**、**退出登录**。首页欢迎区另有 **系统反馈** 等入口（与工具无强耦合）。

### 8.2 角色与能力（摘要）

基底同时使用 **`User.is_superuser`**、**全局角色表**（`Role` + `UserRole`，名称为字符串）与 **按工具指派**（`ToolOwner`）。实现新工具时只需理解分工，不必改表结构。

| 概念 | 含义 |
|------|------|
| **超级用户** | `User.is_superuser === true`：用户管理、行为日志、反馈管理、全局工具治理等；路由上对应 `meta.requiresAdmin`。 |
| **`tool_user`** | `Role.name === "tool_user"`：具备**申请工具使用权限**等能力（如 `permissions` 申请流程）；具体以接口内 `has_role(..., "tool_user")` 为准。 |
| **`tool_owner`** | `Role.name === "tool_owner"`：具备**工具负责人相关**能力；**是否**能管**某一具体工具**，还须看该工具是否在 `ToolOwner` 中有指派。 |
| **`ToolOwner`** | 表 `ToolOwner`：某用户被指派为**某一工具**的负责人；可审批该工具权限、进入该工具的 **工具管理** 等（以 `admin` / `permissions` 内校验为准）。 |
| **普通使用某工具** | 对该工具存在 **已通过** 且未过期的 `UserToolPermission`；与「能否进管理页」是不同维度。 |

**一句话**：超管 = 全局；`tool_user` / `tool_owner` = 角色能力标签；**真正管哪个工具**还要看 `ToolOwner` 指派与权限记录。

---

## 9. Agent 提示词模板（可直接粘贴）

以下为 **English 骨架 + 中文需求占位**，便于 LLM 稳定输出结构化解耦。

```text
You are implementing a new tool in the "MOS综合工具箱" platform described in TOOL_INTEGRATION_STANDARD.md.

Hard constraints:
- Platform provides auth, tool catalog, permissions, notifications, and admin APIs. Implement ONLY the tool's business logic and UI extensions. Read doc §8 for sidebar entries and the distinction between tool_user / tool_owner roles and per-tool ToolOwner assignment.
- Management page MUST use el-tabs: tool-specific tabs come first, and fixed tab "通用管理" (`name="general"`) comes after. Put tool status, releases, licensed users, usage logs, and tool feedback in the "通用管理" tab (prefer nested tabs rather than long stacked cards).
- Visuals MUST match the existing Element Plus shell: same typography, spacing, and tag semantics as ToolDetail/ToolManage. Do not add a second UI framework.
- User-visible copy MUST be Chinese (including backend `detail/message` surfaced to UI); keep original wording only for proper fields like protocol/API field names, schema keys, and identifiers.
- Tool feature HTTP paths MUST match `/api/v1/tools/{tool_id}/features/{feature}` where `{feature}` is the full path segment after `/features/` (regex `[a-zA-Z0-9_/-]+`). Single-segment slugs (e.g. `x509-cert`) and nested paths (e.g. `mos-manage/vehicle-rules/42`) are both valid; they MUST align with `backend/main.py` (`TOOL_FEATURE_REGEX`), `contracts/tool.manifest.schema.json` (`feature_slugs`, `behavior_catalog.key`), and `Tool.behavior_catalog_json` so `APIAccessLog.behavior_label` resolves correctly.

Deliverables:
1) Backend: Tool row seed, Pydantic schemas, routes using ensure_tool_access + is_active checks.
2) Frontend: ToolDetail extension + ToolManage tab(s) + api methods.
3) Short verification steps: build passes, manual smoke paths listed.

Tool-specific requirements:
<在此用中文填写：工具名称、功能说明、API 形状、管理页额外选项卡需要什么>
```

---

## 10. 验收清单（发布前）

- [ ] `npm run build`（前端）无错误。
- [ ] 后端可启动，核心接口无 500。
- [ ] 新工具在「所有工具」列表可见，详情页可访问（有权限用户）。
- [ ] `tool.is_active = false` 时非超管无法使用功能入口。
- [ ] 至少一次功能调用出现在「工具管理 → 使用记录」中，且 **行为**（`behavior_label`）与行为目录一致。
- [ ] 管理页 **通用管理** 内状态 / 授权 / 使用记录 / 用户反馈 仍可用；新选项卡无样式「跳脱」壳层。
- [ ] 所有页面头部「返回」按钮都优先回到上一次进入页面；仅在无历史时回退默认路由。
- [ ] 所有列表页均支持分页（含筛选后分页行为正确）。
- [ ] 管理页/工具页涉及分页与 tab 的关键状态可在刷新后恢复（推荐 URL query 持久化）。
- [ ] 所有用户可见文案与错误提示均为中文（含后端返回到前端直接展示的错误信息）。

---

## 11. 参考路径（实现时按需打开，不必装入提示词）

| 主题 | 路径 |
|------|------|
| **新工具接入（填表 + @ Agent）** | `docs/templates/NEW_TOOL_AGENT_TEMPLATE.md` |
| **仓库总览 + Agent 开发/扩展流程** | `docs/PROJECT_AND_AGENT_GUIDE.md` |
| 注册 / 登录 / JWT | `backend/app/api/v1/auth.py` |
| 当前用户、列表用户、注销本人账号等 | `backend/app/api/v1/users.py` |
| 工具列表与详情、路由聚合 | `backend/app/api/v1/tools.py` |
| 工具 API 共享校验（鉴权、工具名检查） | `backend/app/api/v1/tools_common.py` |
| 单工具后端路由（示例） | `backend/app/tools/plugins/service_id_registry/routes.py`, `backend/app/tools/plugins/mos_integration_toolbox/routes.py` |
| 工具 manifest + JSON Schema | `backend/app/tools/plugins/*/tool.manifest.json`, `contracts/tool.manifest.schema.json` |
| 管理端工具能力 | `backend/app/api/v1/admin.py` |
| 访问日志中间件与路径正则 | `backend/main.py` |
| 前端路由与守卫 | `frontend/src/router/index.ts` |
| 主导航壳（侧栏 / 顶栏） | `frontend/src/views/Dashboard.vue` |
| 工具管理页（壳 + 注册表驱动扩展 Tab） | `frontend/src/views/ToolManage.vue` |
| 工具使用页（壳 + 注册表驱动面板） | `frontend/src/views/ToolDetail.vue` |
| 前端工具面板 / 管理 Tab 注册表 | `frontend/src/tools/registry.ts` |
| 前端 API 封装 | `frontend/src/api/tools.ts`, `frontend/src/api/admin.ts`, `frontend/src/api/auth.ts` |

---

**文档结束。** 若你只给 Agent 一份上下文，可附带 **本节全文**，或改用 **`docs/PROJECT_AND_AGENT_GUIDE.md`**（含仓库总览与 Agent 流程）；具体工具的差异化需求用第 9 节模板中的 `<...>` 替换即可。
