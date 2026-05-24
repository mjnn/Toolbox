# ECS：工具运行时状态与分进程部署

## 1. 工具「更新中」状态（`runtime_status`）

- 数据库表 `tool.runtime_status`：`active`（运行中）或 `updating`（更新中）。
- 为 `updating` 时，**所有业务 API**（含工具负责人、平台管理员）均返回 503，**仅系统超级管理员**（`is_superuser`）可继续调用以便排障。
- 与 `is_active`（暂不可用 / 整工具停用）正交；发版流程可在维护窗口内将状态置为 `updating`，完成后置回 `active`。
- 管理入口：**工具管理 → 通用管理 → 工具状态**，可设置「运行中 / 更新中」；会通知已授权用户与工具负责人（与 `is_active` 变更通知同一套接收人逻辑）。

## 2. 分进程解耦转发（`TOOLBOX_TOOL_UPSTREAMS`）

当前宿主不再内置工具插件，`/api/v1/tools/{id}/features/...` 统一走上游转发。

配置方式：

```env
TOOLBOX_TOOL_UPSTREAMS=service-id-registry=http://toolbox-tool-service-id:3000,mos-integration-toolbox=http://toolbox-tool-mos:3000,rsa-token-livestream=http://toolbox-tool-rsa:3000
```

约束：

- 左侧 key 必须与数据库 `Tool.name` 一致。
- 若某 `Tool.name` 缺失映射，宿主对该工具功能返回 `404`。
- 入口层（Nginx/LB）仍统一进宿主；宿主再按映射转发到对应工具容器。

## 3. 与现网 `ecs-deploy-public.sh` 的关系

默认同镜像、单服务 + `TOOLBOX_VISIBLE_TOOL_KEYS` 限制外网**可见**工具；若需分工具进程，需在宿主容器中配置 `TOOLBOX_TOOL_UPSTREAMS`，并保证对应工具容器可达：

详见 `docs/EXTERNAL_PUBLIC_RELEASE.md` 与 `docs/ECS_PROXY_LB_RUNBOOK.md` 中的流量策略。

## 4. 便携包（Windows）

同一环境变量在便携包 `release/toolbox-portable` 的 `.env` 或系统环境中生效；可按工具进程拆分上游并由宿主统一转发（见 `docs/PORTABLE_PACKAGING_AGENT_RUNBOOK.md` 中补充说明）。
