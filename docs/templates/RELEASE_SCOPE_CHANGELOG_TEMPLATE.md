# 发布范围与版本变更模板（Host / Tool / Mixed）

> 用途：ECS 发布与内网便携包发布前，统一填写“发布范围、版本、变更记录、回滚边界”。
> 关联规范：`docs/RELEASE_RUNBOOK.md` §0.2。

---

## 1) 基本信息

- 发布单号：
- 发布日期：
- 发布负责人：
- 发布渠道：`ecs` / `portable` / `ecs+portable`
- 发布类型：`host` / `tool` / `mixed`

## 2) 发布范围（最小颗粒）

- host：
  - [ ] 发布
  - [ ] 不发布
- tools（仅填写受影响工具 `tool_key`）：
  - [ ] `service-id-registry`
  - [ ] `mos-integration-toolbox`
  - [ ] `rsa-token-livestream`
  - [ ] 其他：`<tool_key>`

> 若本次仅改某个工具，不得把无关工具一并发版。

## 3) 版本信息（宿主与工具分开）

- host_version：`<x.y.z 或 vYYYY.MM.DD-channel>`
- tool_versions：
  - `<tool_key_1>`：`<version>`
  - `<tool_key_2>`：`<version>`

## 4) 变更记录（宿主与工具分栏）

- host_changelog（无则填 `N/A`）：
  - 新增：
  - 修复：
  - 兼容性影响：

- tool_changelog（逐工具填写，无则填 `N/A`）：
  - `<tool_key_1>`：
    - 新增：
    - 修复：
    - 兼容性影响：
  - `<tool_key_2>`：
    - 新增：
    - 修复：
    - 兼容性影响：

## 5) 验证清单

- [ ] `powershell -File scripts/run-ci-tool-checks.ps1`
- [ ] `frontend` 下 `pnpm install --frozen-lockfile`（如需）与 `pnpm run build`
- [ ] 健康检查 `/health`
- [ ] 关键功能冒烟（按受影响宿主/工具）
- [ ] 外网视角工具可见性校验（ECS 场景）：`Host: 47.116.180.173`
- [ ] 版本接口校验：`/api/v1/meta/version`

## 6) 回滚边界

- host_rollback_to：`<version/tag>`
- tool_rollback_to：
  - `<tool_key_1>`：`<version/tag>`
  - `<tool_key_2>`：`<version/tag>`

## 7) 扩大发布说明（可选）

当无法按最小颗粒发布时必须填写：

- 扩大发布原因：
- 影响范围：
- 风险控制：
- 预计回滚时长：

