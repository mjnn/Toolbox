# 文档中心（统一入口）

实现细节以**代码与 Schema**为准；文档治理规则见 `DOCS_SYSTEM_AND_GOVERNANCE.md`。

## 快速入口（先读这 5 份）

1. `PROJECT_AND_AGENT_GUIDE.md`（active）  
2. `TOOL_INTEGRATION_STANDARD.md`（active）  
3. `HOST_TOOL_API_DEVELOPMENT_AND_CAPABILITIES.md`（active）  
4. `AGENT_CONTINUOUS_DELIVERY_AND_OPS_GUIDE.md`（active）  
5. `ADMIN_API_MODULE_SPLIT_GUIDE.md`（active）  
6. `DOCS_SYSTEM_AND_GOVERNANCE.md`（active）  

## 文档分区

### A. 核心规范（强约束）

- `PROJECT_AND_AGENT_GUIDE.md`
- `TOOL_INTEGRATION_STANDARD.md`
- `HOST_TOOL_API_DEVELOPMENT_AND_CAPABILITIES.md`
- `DOCS_SYSTEM_AND_GOVERNANCE.md`

### B. 开发与交付（面向人/Agent）

- `AGENT_CONTINUOUS_DELIVERY_AND_OPS_GUIDE.md`
- `ADMIN_API_MODULE_SPLIT_GUIDE.md`
- `ADMIN_API_NEW_MODULE_TEMPLATE.md`
- `FINAL_CLOSURE_PR_CHECKLIST.md`

### C. 运行与发布手册（Runbook）

- `PORTABLE_PACKAGING_AGENT_RUNBOOK.md`
- `RELEASE_RUNBOOK.md`
- `EXTERNAL_PUBLIC_RELEASE.md`
- `ECS_SPLIT_DEPLOY_RUNBOOK.md`
- `PORTABLE_SPLIT_DEPLOY_RUNBOOK.md`
- `ECS_TOOL_RUNTIME_TOPOLOGY.md`
- `ECS_PROXY_LB_RUNBOOK.md`
- `TOOL_VISIBILITY_ENV_RUNBOOK.md`
- `PERF_AND_DB_OPTIMIZATION_RUNBOOK.md`

### D. 能力专题

- `FORM_FIELD_CONFIG_MODULE.md`
- `MOS_TOOLBOX_REBUILD_BASELINE.md`（reference）

### E. 模板

- `templates/NEW_TOOL_AGENT_TEMPLATE.md`
- `templates/FORM_FIELD_CAPABILITY_AGENT_TEMPLATE.md`
- `templates/RELEASE_SCOPE_CHANGELOG_TEMPLATE.md`（ECS/便携统一发布范围与版本变更模板）
- `templates/RSA_Token_Livestream.md`
- `templates/Data_Secure_Manage（编辑中，请勿参考）.md`（draft，禁止作为实现依据）

### F. 仓库与协作辅助

- `REMOTE.md`
- `PROJECT_ARCHITECTURE_OVERVIEW.html`（总体架构图，配合文档阅读）
- `PROJECT_ARCHITECTURE_ABSTRACT.html`（抽象运行逻辑图，突出职责与解耦）

## 冲突处理（简版）

1. 先看代码与 Schema（L0）  
2. 再更新核心规范（L1）  
3. 最后同步 runbook 与模板（L2/L3）  

## 本地验证（文档改动后建议）

- `powershell -File scripts/run-ci-tool-checks.ps1`
- `frontend` 下 `pnpm run build`
