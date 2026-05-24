---
title: MOS综合工具箱 — 可移植打包 Agent 作业手册
description: >-
  面向 Agent 的标准打包流程文档：将项目打包为无需 Python/Node 的 Windows 可运行包，
  包含一键启动/停止、生产 PostgreSQL 配置约束、前后端日志，以及验证与排障步骤。
version: 1.1
target: Windows x64
---

# MOS综合工具箱 · 可移植打包 Agent 作业手册

## 1. 打包目标（硬约束）

产物必须满足以下要求：

1. 目标机器无需安装 Python / Node.js。
2. 提供一键启动与一键停止脚本。
3. 启动时**不**自动创建演示账号（`admin/owner/user`）。
4. 发布包面向部署机直连 PostgreSQL（RDS），不使用 SQLite。
5. 前后端日志明确分离并可追踪：
   - `logs/backend-runtime.out.log`
   - `logs/backend-runtime.err.log`
   - `logs/backend-access.log`
   - `logs/frontend-access.log`
   - `logs/app.log`
6. 服务需绑定 `0.0.0.0:3000`，可通过本机局域网 IP 访问（不只环回地址）。
7. 启动后访问 `http://127.0.0.1:3000/` 与 `http://<LAN-IP>:3000/` 均应返回前端 HTML（`<!DOCTYPE html>`），不是 API fallback JSON。
8. 打包前必须先判定本次发布范围是“仅宿主 / 单工具 / 混合”，并按最小耦合颗粒生成产物；版本与变更记录模板见 `docs/RELEASE_RUNBOOK.md` §0.2。

---

## 2. 关键文件（当前实现）

**产物位置**：标准打包完成后生成 `release/toolbox-portable/`（内含 `toolbox-backend.exe`、启动脚本、嵌入的前端 `dist` 等）。该目录由 `scripts/build-release.ps1` 产出；仓库根 `.gitignore` 已忽略整个 `release/`。

### 2.1 打包与启动脚本

- `scripts/build-release.ps1`
- `scripts/portable-start.ps1` / `portable-start.cmd`
- `scripts/portable-stop.ps1` / `portable-stop.cmd`
- `scripts/PORTABLE_README.md`（复制为发布根 `README.md`）
- 可选性能验收：`scripts/run-perf-k6.ps1`、`run-perf-suite.ps1`、`report-perf-k6.ps1`、`perf/k6-api.js`（默认打进包；`-MinimalIntranetPackage` 时省略；k6 使用 PATH 或自建 `ops\k6.exe`）

### 2.2 后端打包入口与运行逻辑

- `backend/run_server.py`（PyInstaller 入口）
- `backend/main.py`（静态资源加载 + 访问日志 + SPA fallback）
- `backend/app/database.py`（启动时仅系统种子与可选首个超管逻辑）
- `backend/app/core/logging_config.py`（日志配置）
- `backend/app/tools/plugins/*`（工具源码目录，可用于独立工具进程）

**可选：分进程解耦运行工具** — 宿主进程通过 `TOOLBOX_TOOL_UPSTREAMS`（`tool.name -> upstream`）转发工具能力；单一便携包内若需多进程隔离（实验性），可为不同工具进程使用不同端口，并在宿主 `.env` 中维护映射。生产环境需在入口统一访问宿主，再由宿主转发到工具进程，与 `docs/ECS_TOOL_RUNTIME_TOPOLOGY.md` 一致。

---

## 3. 标准打包步骤（Agent 执行顺序）

### 3.0 术语：两种「并发」不要混淆

| 含义 | 说明 |
|------|------|
| **打包脚本是否并行** | 仅影响**打包机**上是否同时跑前端 build 与 pip。若需缩短耗时，可加 `-ParallelPrereqs`。 |
| **运行时 Uvicorn worker** | 指**后端进程数**（`backend/run_server.py`），与打包并行无关。 |

### Step 1：构建前端静态资源

在 `frontend` 目录：`pnpm install --frozen-lockfile` → `pnpm run build`，产物 `frontend/dist`。

### Step 2：一键打包（推荐）

在项目根：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/build-release.ps1"
```

该脚本会：

1. （默认顺序）前端 build → pip / PyInstaller → 组装 `release/toolbox-portable`
2. 可选 `-ParallelPrereqs` 并行缩短打包机时间
3. 默认复制 `backend/.env.example` → 发布目录 `.env.example`；默认**不**复制 `backend/.env`；需要时用 `-IncludeBackendEnv`
4. 默认附带性能脚本与 `perf/`；内网极简目录可用 `-MinimalIntranetPackage`（跳过 `.env.example`、perf、相关子目录）
5. 默认打包结束后执行便携包冒烟：`start.ps1`（不自动开浏览器）→ 校验 `/health` + `/` 返回 HTML（`<!DOCTYPE html>`）→ `stop.ps1` 自动停服；如 CI 仅需产物可传 `-SkipPortableSmokeTest`。

### 3.1 运行时 Uvicorn worker 与 PostgreSQL 连接池

| 项 | 建议 |
|----|------|
| **Uvicorn workers** | **2**（可用 `TOOLBOX_WORKERS` 覆盖，见 `backend/run_server.py`）。 |
| **连接池** | `SQLALCHEMY_POOL_SIZE=12`、`SQLALCHEMY_MAX_OVERFLOW=8` 等与 RDS `max_connections` 协同。 |

环境变量见 `backend/.env.example`。

### Step 3～6：启动、登录、静态页、LAN、停止、性能验收

与 v1.0 一致：使用 `release/toolbox-portable/start.ps1` 冒烟；`/api/v1/auth/login` 生产账号；`/` 首行 `<!DOCTYPE html>`；`netstat` 确认 `0.0.0.0:3000`；`stop.ps1`；可选 `scripts/run-perf-suite.ps1`（需本机 k6 或 `ops\k6.exe`）。

### Step 6.1（可选）：内网部署机解耦运行（Host + Tools）

在便携目录可直接使用：

- `start-split.ps1` / `start-split.cmd`
- `stop-split.ps1` / `stop-split.cmd`

运行形态：

- Host 进程监听 `0.0.0.0:3000`，对用户保持单入口。
- 三个 Tool 进程分别监听 `3001/3002/3003`，仅本机内部使用。
- 四进程共用同一 `.env`（同一 PostgreSQL / RDS）。
- Host 使用 `TOOLBOX_TOOL_UPSTREAMS` 将 `tools/{id}/features/*` 转发到对应 Tool 进程，前端与外部 API 路径保持不变。

### Step 6.2：版本治理（ECS / 便携统一）

为支持“宿主读取工具版本并记录历史”，每个工具运行实例需暴露：

- `GET /api/v1/meta/version`

返回结构：

```json
{
  "version": "1.2.0",
  "spec_revision": "v0.3",
  "title": "版本更新",
  "changelog": "新增 xx；修复 yy"
}
```

当前工具实现默认从环境变量生成该响应：

- `TOOLBOX_VERSION`
- `TOOLBOX_SPEC_REVISION`（可选）
- `TOOLBOX_VERSION_TITLE`（可选）
- `TOOLBOX_CHANGELOG`（必填建议；支持多行文本或 JSON 数组字符串）

宿主管理员在“工具管理 → 版本管理”中点击“从工具接口同步版本”后，系统将：

1. 从工具接口拉取版本元数据；
2. 更新工具当前版本（`Tool.version/spec_revision`）；
3. 写入版本历史记录；
4. 按开关通知授权用户与负责人。

---

## 4. 本项目已知坑位与防错规则

（PyInstaller `passlib.handlers.bcrypt`、前端 dist 在 `_internal`、`$PID` 冲突、`TOOLBOX_HOST`、防火墙等 —— 与此前版本相同，见团队历史记录或 `backend/main.py` / `portable-stop.ps1`。）

---

## 5. 发布产物验收清单（交付前）

- [ ] `start.cmd` / `stop.cmd` 可用
- [ ] `toolbox-backend.exe` 存在
- [ ] `0.0.0.0:3000` 监听且 `/` 为 HTML
- [ ] 无演示账号自动注入
- [ ] 日志文件可写
- [ ] 部署机已配置 `.env`（非精简包时由 `.env.example` 派生）

---

## 6. Agent 提示词模板（节选）

```text
Use scripts/build-release.ps1. No Python/Node on target. One-click start/stop. Bind 0.0.0.0:3000. No demo users. Verify /health, login, and "/" is HTML. Optional: -MinimalIntranetPackage for smallest folder.
```

---

## 7. 变更后快速复打包指令

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/build-release.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "release/toolbox-portable/start.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "release/toolbox-portable/stop.ps1"
```

文档用途：供后续 Agent 在最小上下文下稳定重复打包流程。
