---
title: MOS综合工具箱 — 发布 Runbook（Agent 可读）
description: >-
  面向 Cursor / Agent 与人工运维：发布前闸门、环境变量、两种典型交付形态、部署后冒烟、回滚与常见故障。
  实现细节以当前仓库代码为准；与工具接入规范互补，不重复描述 /api/v1/tools/{id}/features/... 等开发约束。
version: 1.0
stack: Vue3 + FastAPI + PostgreSQL（仅 DATABASE_URL）
---

# MOS综合工具箱 · 发布 Runbook

> **何时读本文**：准备合并到 `main` / 打标签 / 向生产或预发布环境交付前。  
> **与谁搭配**：`docs/PROJECT_AND_AGENT_GUIDE.md`（架构与端口）、`docs/TOOL_INTEGRATION_STANDARD.md` §10（工具侧验收）、`docs/PORTABLE_PACKAGING_AGENT_RUNBOOK.md`（Windows 便携包细则）。

---

## 0. Agent 阅读顺序（最短路径）

1. **§1 发布闸门**：合并或出包前必须绿的命令。  
2. **§2 环境变量清单**：生产 `.env` 不得踩的坑（bootstrap、密钥、CORS）。  
3. **§3 交付形态**：二选一或同时维护——源码 + Uvicorn / Windows 便携包。  
4. **§4 部署后冒烟**：顺序固定，便于脚本化或逐项勾选。  
5. **§5 回滚与数据**：当前仓库无 Alembic 时的诚实说明。  
6. **§6 排障索引**：日志与常见问题跳转。

---

## 0.1 环境角色（开发机 vs 部署机）

| 角色 | 能力边界 | 推荐职责 |
|------|----------|----------|
| 开发机 | 可安装开发依赖、可运行构建脚本 | 代码开发、`start-dev.cmd` 联调、产物构建与验收 |
| 部署机 | 权限受限，通常不可安装开发工具 | 接收并运行打包产物、配置 `.env`、执行运行与运维检查 |

**关系约束**：开发机负责“构建”，部署机负责“运行”。部署机不承担源码构建或依赖安装，以保证流程可重复与可审计。

---

## 1. 发布前闸门（硬约束）

在**目标发布 commit** 上，于**仓库根目录**执行：

| 步骤 | 命令 | 通过标准 |
|------|------|----------|
| 工具契约与边界 | `powershell -NoProfile -File scripts/run-ci-tool-checks.ps1` | 退出码 0；与 CI 中 Python 两步等价（见 `.github/workflows/ci.yml`） |
| 前端生产构建 | 在 `frontend` 目录：`pnpm install`（如需）后 `pnpm run build` | 无错误；产物在 `frontend/dist` |
| （建议）后端语法 | `python -m compileall backend/app backend/main.py` | 无语法错误 |

**说明**：仓库**无**独立自动化测试套件（见 `TOOL_INTEGRATION_STANDARD.md` §1）；闸门通过后仍需 **§4 手工冒烟**。新工具或改插件时另遵守 `docs/TOOL_INTEGRATION_STANDARD.md` §10 与 `.cursor/rules/tool-plugins.mdc`。

---

## 2. 环境变量清单（生产）

模板：**`backend/.env.example`** → 复制为 **`backend/.env`**（永不提交真实密钥）。

| 变量 | 生产要求 |
|------|----------|
| `DATABASE_URL` | **必填**。仅 `postgresql+psycopg2://...`（见 `app/core/config_simple.py`）；SQLite 会拒绝启动。 |
| `SECRET_KEY` | **必须**改为高强度随机字符串；用于 JWT 签名。 |
| `BACKEND_CORS_ORIGINS` | JSON 数组字符串，**与浏览器访问前端的 Origin 完全一致**（含协议与端口）。未配时默认仅含本地开发 Origin，**生产易因 CORS 失败**。 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | 按安全策略调整；默认见 `.env.example`。 |
| `FIRST_SUPERUSER` / `FIRST_SUPERUSER_PASSWORD` / `FIRST_SUPERUSER_USERNAME` | 仅在**空库且库中无任何超管**时用于创建首个超管；生产应强密码，创建后轮换。 |
| `TOOLBOX_BOOTSTRAP_USERS` | **生产必须保持关闭**：不设或设为 `0`。设为 `1` 会写入演示账号（见 `app/database.py`）。 |
| `TOOLBOX_WORKERS` | Uvicorn 进程数；未设置时便携入口默认 2（见 `backend/run_server.py`）。与 PG `max_connections` 联动，参见 `PROJECT_AND_AGENT_GUIDE.md` §1.9.1。 |
| `SQLALCHEMY_POOL_SIZE` / `SQLALCHEMY_MAX_OVERFLOW` | 每 worker 连接池；总连接 ≈ workers × (pool + overflow)。 |
| `TOOLBOX_HOST` / `TOOLBOX_PORT` | 监听地址与端口（便携/生产脚本常用）。 |
| `TOOLBOX_FRONTEND_DIST` | 可选；覆盖前端静态目录解析（`main.py` 中非 frozen 模式）。 |
| `TOOLBOX_STATIC_DIR` | 可选；静态资源根路径，默认 `backend/static`；头像等在 `static/avatars`。 |
| `TOOLBOX_LOG_DIR` | 若项目日志配置使用（以 `app/core/logging_config.py` 为准）。 |
| `SQL_ECHO` | 生产保持关闭。 |

**前端 API 根路径**：当前 axios 使用 **`baseURL: '/api/v1'`**（`frontend/src/api/auth.ts`）。生产部署应保证 **浏览器中页面与 API 同源或由反向代理把 `/api` 转到后端**；若前后端不同源且无反代，需另行改造（本 Runbook 不假设该形态）。

---

## 3. 交付形态（二选一或组合）

### 3.1 形态 A：源码 + PostgreSQL（Linux / 通用）

1. 检出发布 commit，配置 `backend/.env`。  
2. 安装后端依赖：`backend/requirements.txt`（建议在 venv 中）。  
3. 构建前端：`frontend` 下 `pnpm run build`。  
4. 运行方式二选一：  
   - **开发同名策略**：后端 Uvicorn 指向含 `index.html` 的 `frontend/dist`（见 `main.py` 中 `TOOLBOX_FRONTEND_DIST` / 默认相对路径）。  
   - **反代**：Nginx/Caddy 将 `/` 指向前端静态目录，`/api` 指到 Uvicorn；此时须把 `BACKEND_CORS_ORIGINS` 配成前端页面的 Origin（若不同源）。  
5. 进程守护：systemd、Windows 服务或编排平台由运维选择，本仓库**不**内置单元文件。

**健康检查**：HTTP `GET /health` → JSON 含 `"status": "healthy"`（`backend/main.py`）。

### 3.2 形态 B：Windows 便携包

- **细则**以 **`docs/PORTABLE_PACKAGING_AGENT_RUNBOOK.md`** 为准（`scripts/build-release.ps1` → `release/toolbox-portable`）。  
- 运行依赖仍含 **PostgreSQL**（连接串在 `.env`）；包内为后端可执行文件 + 嵌入 `dist`，**不是**「无数据库单机 demo」。

---

## 4. 部署后冒烟（建议顺序）

以下为**最小集**；可按环境增加业务用例。

| # | 动作 | 期望 |
|---|------|------|
| 1 | `GET /health` | 200，`status` 为 healthy |
| 2 | 浏览器打开首页 | 返回 SPA HTML（`DOCTYPE`），非仅 JSON API 占位（若已放 `frontend/dist`） |
| 3 | 登录 | 已知账号可登录；新注册流程符合「需审批」产品设计时，未审批用户无法使用需权限功能 |
| 4 | 侧栏与路由 | `Dashboard.vue` 约定路由可访问（超管与普通用户可见性差异见 `TOOL_INTEGRATION_STANDARD.md` §8） |
| 5 | 任一端点：`/api/v1/tools/{id}/features/...` | 带有效 JWT 调用成功路径；随后在**工具管理 → 使用记录**能看到记录，且 **行为中文名**与 `behavior_catalog` 一致（见主规范 §6.3） |

**工具专属**：按 `TOOL_INTEGRATION_STANDARD.md` §10 勾选；涉及插件时核对 `contracts/tool.manifest.schema.json` 与各插件 `tool.manifest.json`。

---

## 5. 回滚与数据库变更（当前约束）

- **应用回滚**：恢复到上一发布 commit / 上一便携包目录；**同时**确保向后端进程注入的 `.env` 与版本说明一致。  
- **数据库**：应用使用 SQLModel `create_all` + 种子逻辑（`app/database.py`），**仓库内无 Alembic 迁移链**。  
  - **含义**：小步发布可依赖「兼容旧表」的代码；**删改列/复杂迁移**需要人工 SQL 或外部迁移工具，**必须**先在预发布验证并备份。  
- **备份**：发布前应对 PostgreSQL 做快照或逻辑备份；若使用头像等上传文件，备份 `TOOLBOX_STATIC_DIR` 下相关目录。

---

## 6. 排障索引

| 现象 | 优先检查 |
|------|----------|
| 启动报错 DATABASE_URL / SQLite | `app/core/config_simple.py`；仅允许 PostgreSQL。 |
| 浏览器跨域、登录后 API 失败 | `BACKEND_CORS_ORIGINS` 是否包含当前页面 Origin；反代是否转发 `Authorization`。 |
| 前端空白或 404 | `frontend/dist` 是否已构建并被 `main.py` 解析到；便携包是否按 `PORTABLE_PACKAGING_AGENT_RUNBOOK.md` 汇编。 |
| 使用记录无中文行为名 | `Tool.behavior_catalog_json` / manifest `behavior_catalog` 与真实路径 `feature` 段是否一致（主规范 §6.3）。 |
| 多 worker 下数据库连接过多 | 降低 `TOOLBOX_WORKERS` 或连接池参数，对照 RDS `max_connections`。 |

**日志**：访问与后端日志由 `app/core/logging_config.py` 及 `main.py` 中 access logger 输出；便携包路径见 `PORTABLE_PACKAGING_AGENT_RUNBOOK.md`。

---

## 7. 发布清单（可复制为 Issue / PR 勾选）

- [ ] 发布 commit 已跑：`run-ci-tool-checks.ps1` + `pnpm run build`  
- [ ] 生产 `SECRET_KEY`、`DATABASE_URL`、`BACKEND_CORS_ORIGINS` 已确认  
- [ ] `TOOLBOX_BOOTSTRAP_USERS` 未在生产开启  
- [ ] 数据库已备份（及静态文件若需要）  
- [ ] `/health` 与 §4 冒烟通过  
- [ ] （若涉及 schema）迁移/变更已在预发布验证并有回滚预案  

---

**文档结束。** 若任务仅为「改某一工具插件」，通常只需 §1 闸门 + 主规范 §10；全量发布时通读 §2～§5。
