# 宿主-工具接口开发要求与宿主能力接口文档

> 适用范围：MOS 综合工具箱宿主（FastAPI）与各工具插件/独立工具服务的对接。  
> 目标读者：工具开发者、宿主开发者、测试与运维同学。

---

## 1. 总体约定

- 宿主 API 前缀：`/api/v1`
- 工具业务接口统一前缀：`/api/v1/tools/{tool_id}/features/{feature}`
- 业务接口 `feature` 字符集必须满足：`[a-zA-Z0-9_/-]+`
- 用户可见文案与错误提示使用中文（协议字段名、标识符除外）
- 列表接口必须支持分页（`skip/limit`），响应应返回 `total + items`（或等价结构）

---

## 2. 工具接入开发要求（对工具方）

## 2.1 路由与日志可观测要求（硬约束）

工具业务接口必须走如下路径规范，否则宿主无法正确记录工具行为日志：

```text
/api/v1/tools/{tool_id}/features/{feature}
```

宿主在中间件中使用如下正则解析 `tool_id` 和 `feature_name`，并写入 `APIAccessLog`：

```text
^/api/v1/tools/(?P<tool_id>\d+)/features/(?P<feature>[a-zA-Z0-9_/-]+)$
```

要求：

- `feature` 可为单段：`query`
- `feature` 也可为多段：`rules/item-detail`
- 不得绕过 `/features/` 前缀直挂业务 API

## 2.2 访问控制要求（硬约束）

工具服务处理器必须复用宿主鉴权与权限校验：

- 使用 `ensure_tool_access` 校验用户是否有该工具权限（或为超管/工具负责人）
- 使用工具状态校验（`is_active` 与 `runtime_status`）保证停用/更新中策略生效
- 禁止在工具服务内重复实现一套平行权限表与鉴权逻辑

## 2.3 分布式/分进程接入要求（当前唯一接入模式）

当前宿主默认不加载本地工具插件，工具能力统一通过上游服务转发：

- 宿主读取环境变量 `TOOLBOX_TOOL_UPSTREAMS`
- 映射格式：`tool_name=http://host:port,tool_b=http://host:port`
- 请求转发规则：
  - `/{tool_id}/features/{feature_path}` -> `upstream/api/v1/tools/{tool_id}/features/{feature_path}`
- 若 `Tool.name` 未配置到 `TOOLBOX_TOOL_UPSTREAMS`，宿主返回 `404 功能不存在`

## 2.4 本地插件加载（可选：仅用于工具专用进程）

当工具以独立进程运行时，可通过 `TOOLBOX_LOAD_TOOL_PLUGINS` 显式加载对应 `Tool.name` 的本地路由（用于同镜像拆分进程）。

- 默认（未设置 / `none` / `-` / `0`）：不加载任何本地插件
- `all` / `*`：加载全部内置插件（不推荐用于宿主入口）
- `a,b,c`：按名单加载

宿主入口仍应优先走 `TOOLBOX_TOOL_UPSTREAMS` 转发，避免宿主进程与工具进程职责混叠。

## 2.5 版本治理对接要求

每个工具应实现版本自描述接口（供宿主管理端同步）：

- `GET /api/v1/meta/version`

返回字段约定：

- `version`：必填，版本号
- `spec_revision`：可选，规格修订
- `title`：可选，版本标题
- `changelog`：必填，变更说明（字符串或可转字符串列表）

## 2.6 代码模块化边界（硬约束）

无论工具以「独立服务」还是「仓库内插件目录」交付，工具侧代码都必须遵守：

- **允许依赖**：`app.database`、`app.models`、`app.schemas`、`app.services.*`、`app.api.v1.users`（`get_current_active_user`）、`app.api.v1.tools_common`（门禁/工具名校验/管理辅助）
- **禁止依赖**：`app.api.v1.admin*`、`app.api.v1.admin_common`、`app.api.v1.rbac`、`app.core.config_simple`
- **共享逻辑**：必须下沉到 `app/services/*`（示例：`app/services/db_optimization_runtime.py`），禁止在工具路由与宿主管理接口中复制粘贴两套实现
- **MOS 遗留适配层**：`app.services.mos_legacy_toolbox_adapter` **仅允许** `mos-integration-toolbox` 依赖；其他工具禁止 import（CI 脚本 `scripts/check_tool_plugin_boundaries.py` 会拦截）
- **密钥读取**：优先使用 `app.services.secret_key` 读取 `SECRET_KEY`；工具插件仍**禁止**直接 `import app.core.config_simple`，也**禁止**在插件内 `os.getenv("SECRET_KEY")` 直读

---

## 3. 宿主提供能力接口（给工具侧/前端侧调用）

说明：以下路径均为完整路径（含 `/api/v1` 前缀）。

## 3.1 认证与用户上下文

- `POST /api/v1/auth/login`：登录获取 token
- `POST /api/v1/auth/refresh`：刷新 token
- `POST /api/v1/auth/logout`：登出
- `GET /api/v1/users/me`：获取当前用户信息

## 3.2 工具目录与元信息

- `GET /api/v1/tools/`：工具列表（支持 `skip`/`limit`/`search`）
- `GET /api/v1/tools/{tool_id}`：工具详情（含权限校验）
- `GET /api/v1/tools/{tool_id}/releases`：工具版本记录（分页）
- `GET /api/v1/tools/meta/version`：宿主运行版本元信息（环境变量注入）

## 3.3 工具业务能力入口（统一门面）

- `GET|POST|PUT|PATCH|DELETE /api/v1/tools/{tool_id}/features/{feature_path}`

用途：

- 工具业务 API 的统一入口
- 宿主可基于该路径统一鉴权、停用策略、行为日志、路由转发

## 3.4 权限申请与审批流

用户侧：

- `POST /api/v1/permissions/apply/{tool_id}`：申请工具权限
- `GET /api/v1/permissions/my-permissions`：我的权限记录

审核侧（超管或工具负责人）：

- `GET /api/v1/admin/permissions/pending`：待审核列表
- `POST /api/v1/admin/permissions/{permission_id}/approve`：批准
- `POST /api/v1/admin/permissions/{permission_id}/reject`：拒绝

## 3.5 工具治理能力（管理端）

工具状态与展示：

- `PATCH /api/v1/admin/tools/{tool_id}/status`：更新可用状态与运行状态
- `PUT /api/v1/admin/tools/{tool_id}/display-config`：更新工具展示名/展示描述

工具负责人：

- `GET /api/v1/admin/tools/{tool_id}/owners`：查询负责人
- `POST /api/v1/admin/tools/{tool_id}/owners/{user_id}`：指派负责人
- `DELETE /api/v1/admin/tools/{tool_id}/owners/{user_id}`：移除负责人
- `GET /api/v1/admin/my-owner-tools`：当前用户负责的工具 ID 列表

已授权用户治理：

- `GET /api/v1/admin/tools/{tool_id}/license-users`：已授权用户分页列表
- `DELETE /api/v1/admin/tools/{tool_id}/license-users/{user_id}`：撤销授权

工具访问日志：

- `GET /api/v1/admin/tools/{tool_id}/usage-logs`：工具维度使用记录（分页、可检索）

工具反馈：

- `GET /api/v1/admin/tools/{tool_id}/feedback`：工具维度反馈列表（分页）

## 3.6 版本管理能力（宿主同步工具版本）

- `POST /api/v1/admin/tools/{tool_id}/version-records/sync`

行为：

- 宿主调用工具上游版本接口（优先 `/api/v1/meta/version`）
- 若有变更，写入 `ToolRelease` 并可选通知用户

## 3.7 可见性治理（内外网差异展示）

- `GET /api/v1/admin/system/tool-visibility`：读取工具可见性配置
- `PUT /api/v1/admin/system/tool-visibility`：更新可见性配置

典型配置项：

- `external_hosts`
- `internal_visible_tool_keys`
- `external_visible_tool_keys`

## 3.8 审计与运营辅助

- `GET /api/v1/admin/audit-logs`：全局审计日志（分页）
- `GET /api/v1/admin/audit-logs/export`：导出审计日志 CSV
- `GET /api/v1/admin/analytics/tool-traffic`：工具流量统计（日/周/月）

---

## 4. 推荐联调流程

1. 工具先实现 `GET /api/v1/meta/version` 与 `/features/*` 路径规范。
2. 在宿主注册 `Tool` 记录，完成 `tool_key` 对齐。
3. 前端接入工具详情与工具管理扩展，避免在壳层写硬编码分支。
4. 用普通用户走一遍：申请权限 -> 审批 -> 调用工具功能 -> 管理端查看使用记录。
5. 验证 Host 维度可见性：普通 Host 与外网 Host（`47.116.180.173`）均检查工具列表差异。

---

## 5. 常见错误清单

- 业务 API 未走 `/features/`：导致工具使用记录无法归因到行为目录
- 工具开发绕过 `ensure_tool_access`：出现越权访问
- `tool_key` 与 `Tool.name` / 前端 registry key 不一致：前后端映射错乱
- 列表接口未分页：管理页性能与交互退化
- 未提供版本自描述接口：管理端无法进行“版本同步”治理

---

## 6. 参考实现路径

- `backend/app/api/v1/tools.py`
- `backend/app/api/v1/tools_common.py`
- `backend/app/api/v1/permissions.py`
- `backend/app/api/v1/admin_permissions.py`
- `backend/app/api/v1/admin_tool_access.py`
- `backend/app/api/v1/admin_audit.py`
- `backend/app/api/v1/admin_releases.py`
- `backend/app/api/v1/admin.py`
- `backend/app/services/db_optimization_runtime.py`
- `backend/app/services/mos_legacy_toolbox_adapter.py`
- `backend/app/services/secret_key.py`
- `scripts/check_tool_plugin_boundaries.py`
- `backend/main.py`
