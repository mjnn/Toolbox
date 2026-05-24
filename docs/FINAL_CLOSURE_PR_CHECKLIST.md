# 最终收官 PR 清单（建议按批次执行）

## 目标

将当前“已拆分 + 已收敛”的成果以可审阅、可回滚、可持续维护的方式完成收官。

## PR-1：结构收官（已完成可复核）

- [ ] `admin.py` 巨石拆分完成且路由不重叠  
- [ ] `api.py` 已挂载所有 admin 子模块  
- [ ] 共享 helper 收敛到 `admin_common.py`  
- [ ] `python -m compileall backend/app/api/v1/*.py` 通过  
- [ ] `powershell -File scripts/run-ci-tool-checks.ps1` 通过  

涉及文件（核心）：

- `backend/app/api/v1/admin.py`
- `backend/app/api/v1/admin_common.py`
- `backend/app/api/v1/admin_feedback.py`
- `backend/app/api/v1/admin_audit.py`
- `backend/app/api/v1/admin_permissions.py`
- `backend/app/api/v1/admin_tool_access.py`
- `backend/app/api/v1/admin_releases.py`
- `backend/app/api/v1/admin_users.py`
- `backend/app/api/v1/api.py`

## PR-2：文档收官（本次建议重点）

- [ ] `docs/README.md` 已成为唯一入口导航  
- [ ] `docs/DOCS_SYSTEM_AND_GOVERNANCE.md` 明确分层与冲突处理  
- [ ] `docs/ADMIN_API_MODULE_SPLIT_GUIDE.md` 与代码结构一致  
- [ ] `docs/ADMIN_API_NEW_MODULE_TEMPLATE.md` 可直接复用  
- [ ] `docs/PROJECT_ARCHITECTURE_OVERVIEW.html` 可视化架构图可打开且结构完整  

## PR-3：稳定性与回归清单

- [ ] Admin 关键路径抽样回归：
  - [ ] 反馈列表/统计
  - [ ] 审计日志/导出
  - [ ] 权限审核（pending/approve/reject）
  - [ ] 工具负责人与授权用户管理
  - [ ] 版本同步
  - [ ] 用户管理（审批/角色/导入/重置密码）
- [ ] 前端管理页关键页面可正常加载与请求
- [ ] 关键中文错误提示保持不变

## PR-4：后续优化（可选）

- [ ] 为 admin 子模块补 API 集成测试（优先权限与状态流）
- [ ] 继续减少 `admin.py` 剩余耦合（系统配置/公告等）
- [ ] 在 CI 中加入文档一致性检查（链接、状态标记、主文档唯一性）

## 提交信息建议

- `refactor(admin): split admin domain routes into focused modules`
- `docs(governance): consolidate docs index and ownership rules`
- `docs(architecture): add comprehensive html architecture map`
