# Admin API 模块拆分说明（给维护者）

## 目标

将历史巨石文件 `backend/app/api/v1/admin.py` 按职责拆分，降低耦合和回归风险，便于持续开发。

## 当前模块划分

- `backend/app/api/v1/admin.py`
  - 保留系统级与综合管理逻辑（未拆分部分）。
- `backend/app/api/v1/admin_feedback.py`
  - 反馈列表与反馈统计：
  - `/api/v1/admin/tools/{tool_id}/feedback`
  - `/api/v1/admin/feedback`
  - `/api/v1/admin/feedback/counts`
- `backend/app/api/v1/admin_audit.py`
  - 使用日志与审计日志：
  - `/api/v1/admin/tools/{tool_id}/usage-logs`
  - `/api/v1/admin/audit-logs`
  - `/api/v1/admin/audit-logs/export`
- `backend/app/api/v1/admin_permissions.py`
  - 工具权限审核流：
  - `/api/v1/admin/permissions/pending`
  - `/api/v1/admin/permissions/{permission_id}/approve`
  - `/api/v1/admin/permissions/{permission_id}/reject`
- `backend/app/api/v1/admin_tool_access.py`
  - 工具负责人和授权用户管理：
  - `/api/v1/admin/tools/{tool_id}/owners`（含增删）
  - `/api/v1/admin/my-owner-tools`
  - `/api/v1/admin/tools/{tool_id}/license-users`（含撤销）
- `backend/app/api/v1/admin_releases.py`
  - 工具版本同步与发版记录写入：
  - `/api/v1/admin/tools/{tool_id}/version-records/sync`
- `backend/app/api/v1/admin_users.py`
  - 用户管理与批量导入：
  - `/api/v1/admin/users/{user_id}/roles`
  - `/api/v1/admin/users/{user_id}/approve`
  - `/api/v1/admin/users/{user_id}/transfer-super-admin`
  - `/api/v1/admin/users/{user_id}/allowed_tools`（含别名）
  - `/api/v1/admin/users/{user_id}/reset-password`
  - `/api/v1/admin/users/import-excel`（含模板下载）
  - `/api/v1/admin/users/{user_id}`（删除）
  - `/api/v1/admin/tool_assignment/options`（含别名）

## 共享能力

为避免子模块复制粘贴，通用治理 helper 统一在：

- `backend/app/api/v1/admin_common.py`
  - `get_role_by_name`
  - `user_is_tool_owner`
  - `ensure_tool_governance`
  - `ensure_permission_reviewer`
  - `recipient_user_ids_for_tool`

新增 admin 子模块时，优先复用以上 helper。

## 路由聚合位置

统一在 `backend/app/api/v1/api.py` 注册，全部走：

- `prefix="/admin"`
- `tags=["admin"]`

## 开发约定

- 拆分以“搬家不改行为”为优先：先保持 URL、请求参数、返回结构不变。
- 先提取通用 helper，再做跨模块复用，避免出现多个版本的权限判断逻辑。
- 每次拆分后至少执行：
  - `python -m compileall backend/app/api/v1/*.py`
  - `powershell -File scripts/run-ci-tool-checks.ps1`
