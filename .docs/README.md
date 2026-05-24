# .docs 目录说明

`.docs/` 用于沉淀**运行时现状快照**与**面向运维的补充说明**，和 `docs/` 的通用规范互补。

## 当前文档

- `ECS_CURRENT_STRUCTURE_AND_IMPACT.md`
  - 记录 ECS 当前拓扑、代理结构、容器治理结果
  - 说明对客户端调用的兼容性影响与风险边界
- `FIELD_CONFIG_MANAGER_AND_SERVICE_ID_RULES.md`
  - 固化 `FieldConfigManagerTable` 的列行为、弹窗与 `#selectOptionsEditor` 插槽约定
  - 记录 Service ID 将「规则治理」并入字段配置后的文件清单与 `field_key` → 规则类别映射
  - 通用规范仍以仓库根目录 `docs/FORM_FIELD_CONFIG_MODULE.md` 为准

## 使用约定

- 结构发生变化后（服务迁移、代理改造、LB 策略变更）及时更新此目录。
- 以“现网真实状态”为准，不写规划中的未来态。
- 关键信息必须可验证（容器名、端口、入口路径、白名单）。
