# 可复用字段配置模块（Service ID 实现沉淀）

本文档沉淀 Service ID 注册工具中的「字段配置」能力，目标是让后续任意工具在做表单时，直接复用同一套模式：  
**字段定义（新增/删除） + 字段展示形式（单选/多选/填空/长文本） + 统一校验 + 动态渲染**。

## 1. 能力范围

- 支持在工具管理页新增字段、删除字段（内置字段不可删，自定义字段可删）。
- 支持字段展示形式：`text`、`textarea`、`single_select`、`multi_select`。
- 支持字段规则：必填、最小/最大长度、正则、可选值。
- 支持将动态字段值与业务主记录解耦存储（独立值表），避免频繁改主表结构。
- 支持使用页按字段定义自动渲染输入控件。

## 2. 后端实现参考

### 2.1 数据模型

- 字段定义：`backend/app/models.py` 中 `ServiceIdFormFieldDefinition`
  - 记录 `field_key`、`label`、`input_type`、`sort_order`、`is_builtin/is_active`。
- 字段值：`backend/app/models.py` 中 `ServiceIdEntryCustomFieldValue`
  - 通过 `entry_id + field_key` 存储每条业务记录的动态字段值（JSON 字符串）。
- 字段约束：沿用 `ServiceIdFieldConfig`（必填/长度/正则/可选值等）。

### 2.2 API 约定（Service ID 当前实现）

- `GET /api/v1/tools/{tool_id}/features/service-id-field-config`
  - 返回字段列表（内置 + 自定义），包含类型与校验规则。
- `POST /api/v1/tools/{tool_id}/features/service-id-field-config`
  - 新增自定义字段定义。
- `PUT /api/v1/tools/{tool_id}/features/service-id-field-config`
  - 批量更新字段规则（自定义字段也可更新 label/input_type/sort_order）。
- `DELETE /api/v1/tools/{tool_id}/features/service-id-field-config`
  - 删除自定义字段（同步清理该字段的历史值）。

### 2.3 动态字段校验与落库

- 动态字段核心逻辑已下沉到 `backend/app/services/service_id_dynamic_fields.py`：
  - `get_field_constraint_map()`：合并内置字段 + 自定义字段定义 + 约束配置。
  - `validate_custom_field_constraints()`：按 `input_type` 做值类型与规则校验。
  - `save_entry_custom_fields()` / `load_entry_custom_fields()`：动态字段值读写。
  - `create_field_config()` / `update_field_configs()` / `delete_field_config()`：字段定义管理。
- 其中通用能力进一步抽到 `backend/app/services/dynamic_form_fields.py`（工具无关）：
  - 输入类型归一化、允许值去重、通用字段校验、动态字段值读写等基础能力。
- `backend/app/tools/plugins/service_id_registry/routes.py` 仅保留路由编排与权限门禁，更便于后续复用到其他工具。

## 3. 前端实现参考

### 3.1 通用类型

- `frontend/src/api/types.ts`
  - `FormFieldInputType`
  - `FormFieldConfigItem`（含 `input_type`、`is_builtin`、`sort_order`）
  - `DynamicFormValues`（动态字段值）
  - `ServiceId*` 类型仍保留为兼容别名，避免旧代码一次性改动过大

### 3.2 API 封装

- `frontend/src/api/tools.ts`
  - `getServiceIdFieldConfigs`
  - `createServiceIdFieldConfig`
  - `updateServiceIdFieldConfigs`
  - `deleteServiceIdFieldConfig`

### 3.3 管理页（字段定义侧）

- `frontend/src/components/tool-manage/ServiceIdRegistryManageTab.vue`
  - 字段配置 Tab 支持新增字段、删除字段、编辑展示形式与校验规则。
  - 表格渲染已抽为通用组件：`frontend/src/components/form-config/FieldConfigManagerTable.vue`。

### 3.4 使用页（表单渲染侧）

- `frontend/src/components/tool-detail/ServiceIdRegistryPanel.vue`
  - 根据字段配置动态渲染自定义字段控件。
  - 提交时将动态字段统一写入 `extra_fields`。
- 动态字段输入已抽为通用组件：`frontend/src/components/form-config/DynamicFieldInputs.vue`。
- 该组件同样可用于管理页“编辑记录”弹窗，保证新增字段在管理侧和使用侧一致可见。

## 4. 新工具复用步骤（建议直接照搬）

1. 在新工具插件中新增两张表（或等价模型）：
   - 字段定义表（结构参考 `ServiceIdFormFieldDefinition`）
   - 字段值表（结构参考 `ServiceIdEntryCustomFieldValue`）
2. 复用本实现的 4 个字段配置接口（GET/POST/PUT/DELETE）。
3. 业务提交接口增加 `extra_fields` 入参与返回值。
4. 在前端工具管理页接入字段配置面板，在工具使用页接入动态字段渲染。
   - 推荐直接复用：
     - `FieldConfigManagerTable.vue`（字段配置列表）
     - `DynamicFieldInputs.vue`（动态字段输入区）
5. 若工具存在内置字段，保持「内置字段不可删，自定义字段可删」策略，降低风险。

## 5. 设计注意事项

- 建议统一 `field_key` 规则：小写字母开头，后续仅小写/数字/下划线。
- `single_select/multi_select` 必须维护可选值集合，避免前后端展示和校验不一致。
- 删除字段时建议级联清理历史值，避免脏数据长期堆积。
- 字段值使用 JSON 存储时，要在读写层统一做类型归一化（字符串 vs 字符串数组）。

## 6. 后端复用入口（推荐）

- 工具专属服务层：`backend/app/services/service_id_dynamic_fields.py`
  - 负责“业务字段 + 动态字段”拼装和具体模型绑定。
- 通用核心层：`backend/app/services/dynamic_form_fields.py`
  - 负责输入类型归一化、字段值校验、动态值读写等共性逻辑。

后续新工具建议做法：

1. 在 `backend/app/services/` 新建一个 `<tool>_dynamic_fields.py`（薄封装层）。
2. 在薄封装层内调用 `dynamic_form_fields.py` 的通用函数。
3. 路由层只做鉴权、参数转发与响应拼装，避免把校验/存储细节留在 `routes.py`。

## 7. Agent 自动复用入口

- 对话内直接复用模板：`docs/templates/FORM_FIELD_CAPABILITY_AGENT_TEMPLATE.md`
- 自动触发规则：`.cursor/rules/form-field-capability-reuse.mdc`
  - 当需求中出现“新增/删除字段、字段类型、动态表单、字段校验”等语义时，Agent 应默认走本模块方案。
- 文件范围增强规则：`.cursor/rules/form-field-capability-reuse-scoped.mdc`
  - 当编辑插件路由、服务层、工具页组件、form-config 组件、`api/types.ts`、`api/tools.ts` 时强化复用约束。

## 8. 防跑偏约束（建议固定执行）

- 不在 `routes.py` 堆叠动态字段校验与持久化细节，统一下沉到服务层。
- 不复制粘贴动态字段渲染与字段配置表格模板，统一复用 `form-config` 组件。
- 不创建平行字段类型定义，统一复用 `FormField*` 与 `DynamicFormValues`。

## 9. 规则触发矩阵

| 规则文件 | 触发方式 | 适用场景 | 目的 |
|---|---|---|---|
| `.cursor/rules/form-field-capability-reuse.mdc` | `alwaysApply: true` | 对话中出现字段配置/动态表单语义（新增字段、删除字段、字段类型、字段校验） | 全局兜底，确保 Agent 默认走复用链路 |
| `.cursor/rules/form-field-capability-reuse-scoped.mdc` | `globs` 命中相关文件 | 正在编辑插件路由、服务层、工具页组件、form-config 组件、`api/types.ts`、`api/tools.ts` | 文件级增强，防止实现跑偏和模板复制 |

推荐协作方式：

1. 需求沟通阶段：依赖 `alwaysApply` 规则识别“字段配置能力”诉求。
2. 进入实现阶段：在相关文件内由 `scoped` 规则强化实现约束。
3. 关键任务可叠加模板：`docs/templates/FORM_FIELD_CAPABILITY_AGENT_TEMPLATE.md`。
