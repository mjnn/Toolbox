---
title: 新工具接入 — Agent 执行模板
description: 人工填写需求表与功能描述后 @ 本文件；Feature/API 由 Agent 据描述自行设计并可多轮对齐。规范以 docs/TOOL_INTEGRATION_STANDARD.md 为准。
version: 1.3
---

# 新工具接入（人工填写 + Agent 执行）

## 你怎么用

仓库整体介绍、本地端口约定、以及用 Cursor Agent 做日常开发与扩展的**总流程**，见 **`docs/PROJECT_AND_AGENT_GUIDE.md`**（可与本文一起 @ 给 Agent）。**全部文档索引**见 **`docs/README.md`**。

1. **复制本文件**到新文件（推荐）：`docs/templates/my-tool-<简称>.md`，避免多人共改一份模板。
2. 填写 **「一、需求表」**与 **「二、功能描述」**；需求变化时**更新描述**并在 **「二.3 修订记录」**追加一条，方便与 Agent 同一份文档上反复对齐。
3. 新开 Agent 会话，**@ 你保存的那份 md**，说明当前阶段，例如：
   - 第一次：「按该模板做**需求分析与 API/UI 设计草案**，先不改代码」或「按描述直接实现」；
   - 后续：「我已更新 §二 与修订记录，请按新版本调整实现 / 仅更新设计说明」。

**原则**：**不要求**你一次性写清所有接口；只要把业务说清楚（能补「修订记录」迭代即可）。**Feature 拆解、路径命名、请求体/响应体**由 Agent 结合 `TOOL_INTEGRATION_STANDARD` 与现有插件惯例给出**可执行方案**；有异议时在对话里改描述或让 Agent 改草案，再写回本文档。

---

## 一、需求表（人工必填）

| 字段 | 填写说明 | 你的值 |
|------|----------|--------|
| `tool_key` | 与数据库 `Tool.name` 一致；小写、短横线、无空格，如 `my-new-tool` | data-secure-manage |
| `plugin_folder` | 后端目录名，建议 snake_case，如 `my_new_tool` | data_secure_manage |
| 工具中文名（列表/详情展示） | 短标题即可 | 数据安全治理工具 |
| 工具说明 `description` | 一句话描述，进种子数据/DB | 用于数据安全相关治理工作 |
| 是否需要**工具使用页** UI | 是 / 否；否则仅 API，前端详情区显示「暂无可视化」 | 是 |
| 是否需要**管理页扩展 Tab**（除「通用管理」外） | 是 / 否 |
| 管理 Tab（若需要） | 用业务语言写清「第二个 Tab 做什么」即可（英文 slug/标签可由 Agent 建议后再填） | 见 §二 |
| 种子数据 | 是否写入 `database.py` 的 `seed_initial_data`，保证新库自动有该 `Tool` 行 | _REPLACE_NEED_SEED_ |

---

## 二、功能描述（人工填写，可多次修改）

> 用自然语言写即可：**给谁用、要解决什么问题、典型怎么用、边界与例外**。不要求第一版就完备。  
> 技术约束见规范文档；**不要将本节写成接口清单**——接口由 Agent 设计后在对话或「修订记录」里与你对齐。

### 2.1 业务与场景（当前有效版本）

（在此书写或粘贴；可分段：背景 / 主流程 / 例外 / 与旧系统关系等）

_REPLACE_FUNCTIONAL_DESCRIPTION_

### 2.2 约束与假设（可选）

（非目标、合规、仅内网、账号由谁提供、必须中文文案、性能大致预期等；无则写「无」）

_REPLACE_CONSTRAINTS_

### 2.3 修订记录（对齐机制：每次改需求请追加一行）

多人协作时也可在 PR/会话里引用本条版本号。

| 版本 | 日期 | 变更摘要 | 备注（与 Agent 已确认的设计点可记此处） |
|------|------|----------|----------------------------------------|
| v0.1 | _YYYY-MM-DD_ | 初稿 | |
| | | （后续修订继续追加行） | |

### 2.4 与系统内「发版 / 规格修订」的衔接（无需在此写发版号）

本仓库在 **工具管理 → 通用管理** 中提供 **「版本发版与更新记录」**：负责人填写**发版版本号**（如 `1.2.0`）、可选 **规格修订**（建议与本表 **§2.3 修订记录** 中的版本号一致，如 `v0.2`），保存后：

- 工具列表/详情卡片会显示当前 **发版版本** 与 **规格修订**（若有）；
- 每次发版写入一条 **更新记录**，有权限用户可在 **工具详情 → 更新记录** 查看；
- 可选 **推送通知** 给已授权用户与负责人，通知类型为「工具发版」。

模板里的 **修订记录版本（v0.1…）** 表示需求文档迭代；**系统里的发版** 由负责人在上线后在管理页操作。两者建议在「规格修订」字段对齐，便于用户理解。

---

## 三、Agent 执行说明（勿删）

收到本模板后：

1. **以 §一、§二的最新内容为准**；若存在「修订记录」，优先理解相对上一版的**增量**。
2. **设计与实现分工**
   - 根据功能描述，自行拆解 **feature slug**、HTTP 方法、路由形态（须满足 `/api/v1/tools/{tool_id}/features/...` 及 `backend/main.py` 访问日志约定）、Pydantic 模型与前端 Tab/面板划分；参考现有插件与 `contracts/tool.manifest.schema.json`。
   - 若描述模糊或存在多种合理方案，先输出**简短设计说明**（接口列表 + 取舍理由）供人类确认，再动代码（除非用户明确要求直接实现）。
   - **每轮人类修改 §二 后**：重新阅读全文，更新 manifest、`routes.py`、registry、文档中的不一致处，使实现与「当前有效版本」一致。
3. **必读**：[功能/安全/UI 规范 `docs/TOOL_INTEGRATION_STANDARD.md`](../TOOL_INTEGRATION_STANDARD.md)、契约 [`contracts/tool.manifest.schema.json`](../../contracts/tool.manifest.schema.json)。
4. **后端**（实现阶段）
   - 新建 `backend/app/tools/plugins/<plugin_folder>/tool.manifest.json`（`feature_slugs` 与实现一致）。
   - 新建 `backend/app/tools/plugins/<plugin_folder>/routes.py` 并在 [`backend/app/api/v1/tools.py`](../../backend/app/api/v1/tools.py) `include_router`。
   - 鉴权与工具名校验同其它插件；新模型放在 [`backend/app/schemas.py`](../../backend/app/schemas.py)（或项目约定的拆分位置）。
   - 若 §一要求种子数据：扩展 [`backend/app/database.py`](../../backend/app/database.py)。
5. **前端**（当 §一需要 UI 时）：组件 + [`frontend/src/tools/registry.ts`](../../frontend/src/tools/registry.ts)；API 封装 [`frontend/src/api/tools.ts`](../../frontend/src/api/tools.ts)。**禁止**在 `ToolDetail.vue` / `ToolManage.vue` 写死 `tool.name ===`。
6. **验收**：仓库根 `powershell -NoProfile -File scripts/run-ci-tool-checks.ps1`；`frontend` 下 `npm run build`；后端可执行 `python -m compileall app` 或冒烟。
   - 管理页遵循：**工具专属 tab 在前，通用管理 tab 在后**；通用管理内部建议二级 tab。
   - 若工具专属 tab 内还有多个模块（如规则/配置/日志），也应继续使用二级 tab。
   - 涉及列表时必须后端分页（`skip/limit + total/items`）；建议将 tab/分页状态同步 URL query，刷新后可恢复。
   - 所有用户可见文案必须中文（含后端返回给前端直接展示的错误 `detail/message`），仅协议/字段名等不可本地化项可保留原文。
7. **上线发版**不由模板流程单独完成：工具负责人在 **工具管理 → 版本发版与更新记录** 填写版本号与更新说明并（可选）通知用户，参见 §2.4。

---

## 四、附录：命名与目录对照

| 概念 | 说明 |
|------|------|
| `tool_key` | = `Tool.name` = manifest `tool_key` = 前端 registry 的键 |
| `plugin_folder` | 仅后端目录名，便于仓库分层，与 `tool_key` 无强制同名 |

参考插件：

- [`backend/app/tools/plugins/service_id_registry/`](../../backend/app/tools/plugins/service_id_registry/)
- [`backend/app/tools/plugins/mos_integration_toolbox/`](../../backend/app/tools/plugins/mos_integration_toolbox/)

---

## 五、完成后 Agent 勾选

- [ ] `tool.manifest.json` 与实现一致且通过 `scripts/validate_tool_manifests.py`
- [ ] `tools.py` 已 `include_router`
- [ ] `registry.ts` 已注册（若需 UI）
- [ ] 列表/日志等分页符合规范
- [ ] 已运行 `scripts/run-ci-tool-checks.ps1` 与前端 `npm run build`
