# 字段配置能力复用 - Agent 提示词模板

用于任何“字段配置 / 动态表单”相关需求，建议直接复制给 Agent。

```text
你正在维护 MOS 综合工具箱。请复用现有字段配置能力，不要重新造轮子。

必须先阅读并遵守：
- docs/FORM_FIELD_CONFIG_MODULE.md
- backend/app/services/dynamic_form_fields.py
- backend/app/services/service_id_dynamic_fields.py
- frontend/src/components/form-config/DynamicFieldInputs.vue
- frontend/src/components/form-config/FieldConfigManagerTable.vue

需求识别：
- 只要涉及新增/删除字段、字段类型（单选/多选/填空/长文本）、字段校验规则、动态表单渲染，都按字段配置能力实现。

实现约束：
1) 后端采用“路由层 -> 工具薄封装层 -> 通用核心层”的结构。
2) 通用逻辑必须复用 dynamic_form_fields.py，避免在 routes.py 写重复校验和字段存储逻辑。
3) 前端必须优先复用 form-config 通用组件，不允许复制粘贴同类模板实现。
4) 类型优先复用 FormField* 与 DynamicFormValues。
5) 用户可见文案与错误提示必须中文。

反例约束（禁止）：
- 禁止在 routes.py 新增大段字段校验与动态字段值读写实现。
- 禁止在工具页面手写一套新的动态字段渲染模板。
- 禁止在工具管理页手写一套新的字段配置表格模板。
- 禁止新建平行类型替代 FormField* / DynamicFormValues。

输出要求：
1) 先说明任务归类（A/B/C/D）和改动边界。
2) 再按“后端 / 前端 / 文档”分组实现。
3) 明确列出复用了哪些既有模块。
4) 完成后执行并汇报：
   - powershell -File scripts/run-ci-tool-checks.ps1
   - frontend 下 npm run build
```
