# 字段配置表（FieldConfigManagerTable）与 Service ID 规则库 — 实现快照

本文档与 `docs/FORM_FIELD_CONFIG_MODULE.md` 互补：前者为**通用模块规范**，本文档固化 **2026-04 前后** 对 `FieldConfigManagerTable` 的一轮产品化调整及 Service ID 侧落地方式，便于 Agent 与维护者快速对齐。

## 1. 涉及的文件

| 角色 | 路径 |
|------|------|
| 通用字段配置表 | `frontend/src/components/form-config/FieldConfigManagerTable.vue` |
| 静态选项编辑（默认弹窗） | `frontend/src/components/form-config/SelectOptionValuesEditor.vue` |
| Service ID 规则库分页编辑 | `frontend/src/components/tool-manage/ServiceIdRuleCategoryEditor.vue` |
| Service ID 管理（字段 Tab + 插槽接线） | `frontend/src/components/tool-manage/ServiceIdRegistryManageTab.vue` |
| 规范主文档 | `docs/FORM_FIELD_CONFIG_MODULE.md` |

## 2. FieldConfigManagerTable 行为约定

1. **列「允许值 / 选项」**
   - `input_type` 为 `text` / `textarea`：行内 `el-input`，逗号分隔允许值，与历史行为一致。
   - `input_type` 为 `single_select` / `multi_select`：行内仅展示 **「配置选项」**（或「已配置 N 个选项」），点击打开 `el-dialog`（宽度约 800px，`destroy-on-close`）。
2. **弹窗默认内容**：内嵌 `SelectOptionValuesEditor`，双向绑定父级行上的 `allowed_values_text`；父组件在「保存字段配置」时把 `allowed_values_text` 解析为 `allowed_values` 数组提交。
3. **扩展插槽**：`#selectOptionsEditor`，作用域参数 `{ row }`。提供插槽时**完全替换**弹窗默认体；若某工具选项不来自静态列表，必须在此渲染自有编辑器（并自行处理刷新/保存策略）。
4. **导出类型**：`FieldConfigTableRow`（`FormFieldConfigItem & { allowed_values_text: string }`）。

## 3. Service ID：规则治理并入字段配置

1. **已移除**管理页独立 Tab「规则治理」；历史 URL `sidManageTab=rules` 会落到 **「字段配置」** Tab，避免死链。
2. **字段 key → 规则类别**（在 `ServiceIdRegistryManageTab.vue` 中写死映射，勿随意改名）：

   | `field_key` | `ServiceRuleCategory` |
   |-------------|------------------------|
   | `service_type` | `service_type` |
   | `psga_availability` | `psga` |
   | `scope_type` | `scope_type` |
   | `apn_type` | `apn_type` |

3. 对上述四行打开「配置选项」时，插槽内渲染 `ServiceIdRuleCategoryEditor`（`toolId` + `category`），变更后父组件 `loadRules()`，保证「条目治理」编辑弹窗里的下拉与规则表一致。
4. **校验数据源**：主表提交仍由 `backend/app/tools/plugins/service_id_registry/routes.py` 中 `_get_active_rule_values` 与规则表校验；字段配置里的 `allowed_values` 对这四项不是权威来源。

## 4. 维护后建议自测

- `frontend` 目录：`pnpm install --frozen-lockfile`（若需要）与 `pnpm run build`
- 全仓（可选）：`powershell -File scripts/run-ci-tool-checks.ps1`

## 5. 与 `.cursor` 规则的对应关系

- 全局：`/.cursor/rules/form-field-capability-reuse.mdc`（必读列表含本表与 `SelectOptionValuesEditor` / Service ID 接线说明）。
- 按文件：`/.cursor/rules/form-field-capability-reuse-scoped.mdc`（命中 `form-config`、`tool-manage` 等路径时强化复用约束）。
