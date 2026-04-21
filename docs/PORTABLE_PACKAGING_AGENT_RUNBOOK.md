---
title: MOS综合工具箱 — 可移植打包 Agent 作业手册
description: >-
  面向 Agent 的标准打包流程文档：将项目打包为无需 Python/Node 的 Windows 可运行包，
  包含一键启动/停止、默认账号初始化、前后端日志，以及验证与排障步骤。
version: 1.0
target: Windows x64
---

# MOS综合工具箱 · 可移植打包 Agent 作业手册

## 1. 打包目标（硬约束）

产物必须满足以下要求：

1. 目标机器无需安装 Python / Node.js。
2. 提供一键启动与一键停止脚本。
3. 启动时自动创建/补齐默认账号：
   - `admin / admin123`（管理员）
   - `owner / owner123`（功能负责人）
   - `user / user12345`（普通用户）
4. 前后端日志明确分离并可追踪：
   - `logs/backend-runtime.out.log`
   - `logs/backend-runtime.err.log`
   - `logs/backend-access.log`
   - `logs/frontend-access.log`
   - `logs/app.log`
5. 服务需绑定 `0.0.0.0:3000`，可通过本机局域网 IP 访问（不只环回地址）。
6. 启动后访问 `http://127.0.0.1:3000/` 与 `http://<LAN-IP>:3000/` 均应返回前端 HTML（`<!DOCTYPE html>`），不是 API fallback JSON。

---

## 2. 关键文件（当前实现）

**产物位置**：标准打包完成后生成 `release/toolbox-portable/`（内含 `toolbox-backend.exe`、启动脚本、嵌入的前端 `dist` 等）。该目录由 `scripts/build-release.ps1` 产出，体积较大；仓库根 `.gitignore` 已忽略整个 `release/`，需要交付时在本地或 CI 中重新构建。

### 2.1 打包与启动脚本

- `scripts/build-release.ps1`
- `scripts/portable-start.ps1`
- `scripts/portable-start.cmd`
- `scripts/portable-stop.ps1`
- `scripts/portable-stop.cmd`
- `scripts/PORTABLE_README.md`

### 2.2 后端打包入口与运行逻辑

- `backend/run_server.py`（PyInstaller 入口）
- `backend/main.py`（静态资源加载 + 访问日志 + SPA fallback）
- `backend/app/database.py`（启动时默认账号初始化）
- `backend/app/core/logging_config.py`（日志配置）
- `backend/app/tools/plugins/*`（按工具拆分的 feature 路由与 `tool.manifest.json`，随源码一并打进包内，无额外拷贝步骤）

---

## 3. 标准打包步骤（Agent 执行顺序）

> 建议 Agent 严格按顺序执行，不要跳步。

### 3.0 术语：两种「并发」不要混淆

| 含义 | 说明 |
|------|------|
| **打包脚本是否并行** | 仅影响**打包机**上是否同时跑 `npm run build` 与 `pip install`。**默认顺序执行**（先前端 build，再 pip），与运行时性能无关。若需缩短打包机耗时，可加 `-ParallelPrereqs`。 |
| **运行时 Uvicorn worker** | 指**后端进程数**（`backend/run_server.py` → `uvicorn.run(..., workers=N)`），用于支撑多用户并发访问；规划见下文 **§3.1**。 |

### Step 1：构建前端静态资源

在仅手动拆分步骤时，在 `frontend` 目录执行：

```powershell
npm run build
```

产物应位于 `frontend/dist`。

### Step 2：构建后端可执行程序（推荐用脚本一次性完成）

在项目根执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/build-release.ps1"
```

该脚本会：

1. **（默认）顺序**：`npm run build` → `pip install` / `pyinstaller` → `PyInstaller` 打包 → 组装 `release/toolbox-portable`
2. 可选 **仅缩短打包机耗时**：`scripts/build-release.ps1 -ParallelPrereqs`（并行执行前端 build 与 pip 两作业，与运行时 worker **无关**）
3. 用 `PyInstaller` 打包后端（`backend/run_server.py`）
4. 组装发布目录 `release/toolbox-portable`
5. **环境文件**：若打包机存在 **`backend/.env`**，会**自动复制**为 **`release/toolbox-portable/.env`**（与 `toolbox-backend.exe` 同级），运行时 `run_server.py` 会从当前工作目录加载该文件；若不存在则产物中无 `.env`，需自行放置或打包前补好 `backend/.env`。**外传压缩包前请检查是否含数据库密码/密钥，必要时脱敏。**

### 3.1 运行时 Uvicorn worker 与 PostgreSQL 连接池

本节回答：**在约 20～50 名用户、峰值约 10 人同时访问、PostgreSQL 为 1 vCPU / 2GB 时，应设几个 worker、连接池如何取**。

**规划结论（默认值与代码一致）**：

| 项 | 建议 |
|----|------|
| **Uvicorn workers** | **2**（源码直接运行、未设置 `TOOLBOX_WORKERS` 时）。**PyInstaller 便携 exe 固定为 1**：多 worker 子进程无法正确导入打包后的 `main:app`，会导致启动失败（见 `backend/run_server.py`）。 |
| **理由** | FastAPI/Starlette 单进程内异步可处理大量并发 I/O；**2 进程**可缓解少量**同步/阻塞**路径卡住事件循环；在 **1 核 RDS** 上继续加 worker 对吞吐收益有限，且增加 PG 连接与 CPU 争抢。 |
| **不建议** | 在该 PG 规格下将 worker **长期开到 4 以上**（除非同步调高应用机与 RDS 规格并压测）。 |

**连接数粗算**：`app/database.py` 对 PostgreSQL 默认 `SQLALCHEMY_POOL_SIZE=4`、`SQLALCHEMY_MAX_OVERFLOW=2`（每进程最多约 6 条连接）。**2 workers × 6 ≈ 12** 条应用连接，对 2GB 实例通常可接受；若 RDS `max_connections` 或内存紧张，可略降 `SQLALCHEMY_POOL_SIZE` / `max_overflow`。

**环境变量**（`backend/.env` 或便携包工作目录下的 `.env`）：

- `TOOLBOX_WORKERS`：显式覆盖 worker 数（默认 2）。
- `SQLALCHEMY_POOL_SIZE`、`SQLALCHEMY_MAX_OVERFLOW`：每 worker 连接池（仅 PostgreSQL）。

### Step 3：启动冒烟验证

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "release/toolbox-portable/start.ps1"
```

成功标志：

- 控制台出现 `Toolbox started successfully.`
- 打印默认账号信息
- 打印 `LAN URL(s)` 列表
- `http://127.0.0.1:3000/health` 为 200

### Step 4：登录验证（3 个账号）

依次验证 `admin/owner/user` 可登录：

```powershell
$h=@{'Content-Type'='application/x-www-form-urlencoded'}
Invoke-RestMethod -Uri 'http://127.0.0.1:3000/api/v1/auth/login' -Method Post -Headers $h -Body 'username=admin&password=admin123&grant_type=password'
Invoke-RestMethod -Uri 'http://127.0.0.1:3000/api/v1/auth/login' -Method Post -Headers $h -Body 'username=owner&password=owner123&grant_type=password'
Invoke-RestMethod -Uri 'http://127.0.0.1:3000/api/v1/auth/login' -Method Post -Headers $h -Body 'username=user&password=user12345&grant_type=password'
```

### Step 5：静态资源验证（防回归）

```powershell
$resp = Invoke-WebRequest -Uri "http://127.0.0.1:3000/" -UseBasicParsing
($resp.Content -split "`n")[0]
```

首行应为：

```text
<!DOCTYPE html>
```

若返回 `{"message":"Tools Platform API","status":"running"}`，说明前端 dist 路径未生效。

### Step 5.1：局域网地址绑定验证

```powershell
netstat -ano -p tcp | Select-String -Pattern ":3000"
```

至少应包含 `0.0.0.0:3000` 的 `LISTENING` 记录（不是仅 `127.0.0.1:3000`）。

### Step 6：停止服务

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "release/toolbox-portable/stop.ps1"
```

---

## 4. 本项目已知坑位与防错规则

### 4.1 PyInstaller 缺少 passlib bcrypt handler

**现象**：

`ModuleNotFoundError: No module named 'passlib.handlers.bcrypt'`

**处理**：

在 `scripts/build-release.ps1` 的 PyInstaller 参数中保留：

```text
--hidden-import "passlib.handlers.bcrypt"
```

### 4.2 前端 dist 在 `_internal` 目录导致 fallback JSON

**现象**：

根路径返回 API JSON（`Tools Platform API`），不是前端页面。

**原因**：

打包后前端常在 `release/toolbox-portable/_internal/frontend/dist`，而不是 `release/toolbox-portable/frontend/dist`。

**处理**：

1. `portable-start.ps1` 自动探测两个候选目录。
2. `backend/main.py` 在 frozen 模式自动尝试多候选路径（含 `_internal`）。

### 4.3 PowerShell 变量名冲突（`$PID`）

**现象**：

停止脚本报“变量只读”。

**处理**：

`portable-stop.ps1` 不要使用 `$pid`（会与系统 `$PID` 冲突）；使用 `$targetPid`。

### 4.4 服务仅监听环回地址，LAN 无法访问

**现象**：

本机可打开 `127.0.0.1:3000`，但同网段其他设备打不开。

**处理**：

1. 启动时设置 `TOOLBOX_HOST=0.0.0.0`。
2. `run_server.py` 默认 host 保持 `0.0.0.0`（避免漏传环境变量时回退到环回）。
3. 检查 Windows 防火墙是否允许 TCP 3000 入站。

---

## 5. 发布产物验收清单（交付前）

- [ ] `release/toolbox-portable/start.cmd` 可一键启动
- [ ] `release/toolbox-portable/stop.cmd` 可一键停止
- [ ] `toolbox-backend.exe` 存在
- [ ] 服务监听地址为 `0.0.0.0:3000`
- [ ] `frontend dist` 能被根路径 `/` 正确加载
- [ ] 局域网 IP 访问 `http://<LAN-IP>:3000/` 可打开页面
- [ ] 三个默认账号可登录
- [ ] 五类日志文件均能生成并追加内容
- [ ] `README.md` 在发布目录内存在
- [ ] 若需开箱即连数据库：打包前存在 **`backend/.env`**，产物中应有 **`release/toolbox-portable/.env`**

---

## 6. Agent 提示词最佳实践（模板）

以下模板可直接用于后续 Agent 打包任务：

```text
You are packaging this project into a Windows portable release.

Goals:
1) No Python/Node required on target machine.
2) One-click start/stop scripts.
3) Bind to 0.0.0.0 so LAN clients can access.
   - Must print LAN URL(s) at startup.
4) Bootstrap users on startup:
   - admin/admin123
   - owner/owner123
   - user/user12345
5) Clear logs:
   - logs/backend-runtime.out.log
   - logs/backend-runtime.err.log
   - logs/backend-access.log
   - logs/frontend-access.log
   - logs/app.log
6) Root path "/" must serve frontend HTML, not API fallback JSON.
7) Both localhost and LAN IP URL should be reachable.

Process requirements:
- Use scripts/build-release.ps1 for packaging (default sequential npm build then pip; optional -ParallelPrereqs only to speed up the build machine). If backend/.env exists, it is copied to release/toolbox-portable/.env next to the exe.
- Verify with release/toolbox-portable/start.ps1 then stop.ps1.
- Validate all three accounts by calling /api/v1/auth/login.
- Confirm "/" response starts with "<!DOCTYPE html>".
- Confirm port 3000 listens on 0.0.0.0 (not only 127.0.0.1).
- If "/" returns JSON fallback, fix frontend dist path resolution in both startup script and backend runtime logic.
- If packaged app errors with passlib bcrypt module missing, ensure PyInstaller includes hidden import: passlib.handlers.bcrypt.

Deliverables:
- Updated scripts/code if needed
- Rebuilt release/toolbox-portable
- Brief verification report with command outcomes
```

---

## 7. 变更后快速复打包指令

```powershell
# 建议先维护好 backend/.env（含 DATABASE_URL 等），打包时会自动带入 release/toolbox-portable/.env
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/build-release.ps1"
# Optional: parallel prereqs on build machine only — .\scripts\build-release.ps1 -ParallelPrereqs
powershell -NoProfile -ExecutionPolicy Bypass -File "release/toolbox-portable/start.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "release/toolbox-portable/stop.ps1"
```

---

文档用途：供后续 Agent 在最小上下文下稳定重复打包流程，减少“能打包但不能跑”类回归问题。
