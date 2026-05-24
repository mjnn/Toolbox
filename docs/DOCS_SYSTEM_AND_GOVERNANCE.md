# 文档系统与治理规范

## 1. 目标

解决当前文档“分散、重复、冲突、难维护”的问题，建立可持续的文档系统：

- 有清晰层级：先读什么、以谁为准
- 有统一入口：新成员不迷路
- 有冲突处理规则：出现不一致时可快速判定
- 有维护流程：每次改代码后知道该改哪些文档

---

## 2. 文档分层（单一事实源）

按优先级从高到低：

1. **L0 实现事实层（最高）**
   - 仓库代码、API 路由、Schema（如 `contracts/tool.manifest.schema.json`）
   - 当文档与代码冲突时，以此层为准
2. **L1 核心规范层（强约束）**
   - `docs/PROJECT_AND_AGENT_GUIDE.md`
   - `docs/TOOL_INTEGRATION_STANDARD.md`
3. **L2 运行手册层（流程约束）**
   - 发布、打包、ECS、性能、可见性等 runbook
4. **L3 模板与沉淀层（参考）**
   - `docs/templates/*`
   - 历史基线/草稿/过程记录

---

## 3. 冲突处理规则

当两个文档描述不一致时，按以下顺序处理：

1. 先对照 L0（代码/Schema）确认真实行为
2. 更新 L1（核心规范）使其与实现一致
3. 再更新受影响的 L2/L3 文档
4. 在 PR 描述中注明“冲突来源与修复范围”

---

## 4. 文档状态标记

每份文档应标记状态（在标题附近或 README 索引中）：

- `active`：当前有效，可作为执行依据
- `reference`：背景参考，不是硬约束
- `draft`：草稿，禁止作为实现依据
- `deprecated`：已废弃，仅保留历史

---

## 5. 文档目录收敛规则

- `docs/README.md` 作为唯一入口导航
- 新增文档必须归类到既有分区（核心规范/运行手册/模板）
- 禁止创建“临时说明”长期漂移；临时文档在任务结束后要么合并入主文档，要么标记 `deprecated`
- 对同一主题只保留一个“主文档”，其余文档改为“链接到主文档”

---

## 6. 维护责任与触发条件

以下代码变更必须同步文档：

- 路由/权限/分页/UI 规范变更 -> 更新 `TOOL_INTEGRATION_STANDARD.md`
- 运行方式/部署流程变更 -> 更新对应 runbook
- Agent 协作流程变化 -> 更新 `PROJECT_AND_AGENT_GUIDE.md` 或 `AGENT_CONTINUOUS_DELIVERY_AND_OPS_GUIDE.md`

建议在 PR 模板中增加勾选项：

- [ ] 已检查并更新受影响文档
- [ ] 无文档变更原因已说明

---

## 7. 当前建议的主文档映射

- 平台总览与 Agent 协作：`PROJECT_AND_AGENT_GUIDE.md`（active）
- 工具接入硬约束：`TOOL_INTEGRATION_STANDARD.md`（active）
- 持续开发/CI/Ops（人读）：`AGENT_CONTINUOUS_DELIVERY_AND_OPS_GUIDE.md`（active）
- Admin API 拆分说明：`ADMIN_API_MODULE_SPLIT_GUIDE.md`（active）
- Admin 子模块新增模板：`ADMIN_API_NEW_MODULE_TEMPLATE.md`（active）

其余主题以 `docs/README.md` 的“运行手册/模板”分区为准。
