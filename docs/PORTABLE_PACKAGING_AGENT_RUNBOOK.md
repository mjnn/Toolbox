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

### 并发打包（`build-release.ps1` 默认）

为缩短总耗时，脚本在第一阶段用 **两个 PowerShell 后台作业**（`Start-Job`，独立进程）并行执行互不阻塞的工作：

| 作业 | 内容 |
| --- | --- |
| `toolbox_pack_frontend` | 在 `frontend` 执行 `npm run build`，产出 `frontend/dist` |
| `toolbox_pack_pip` | 在 `backend\.venv` 中执行 `pip install -r requirements.txt` 与 `pip install pyinstaller` |

子作业会合并 **Machine** 与 **User** 的 `Path`，避免后台作业找不到 `npm` 或未安装的用户级 Node。

随后仍 **顺序** 执行：`PyInstaller` 打包 `backend/run_server.py`（依赖上一步的 `frontend/dist`），再拷贝脚本与资源到 `release/toolbox-portable`。并行只覆盖「前端构建 + 依赖安装」，不改变产物布局与运行手册中的验收项。

需要严格顺序、方便对齐日志时，关掉并行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/build-release.ps1" -Sequential
```

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

1. **（默认）并行**：前端 `npm run build` + 后端 venv 依赖与 PyInstaller 安装；**或** `-Sequential` 时按旧版顺序执行这两步
2. 用 `PyInstaller` 打包后端（`backend/run_server.py`）
3. 组装发布目录 `release/toolbox-portable`

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
- Use scripts/build-release.ps1 for packaging (default parallel frontend build + pip install; use -Sequential only when debugging logging order).
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
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/build-release.ps1"
# Optional: sequential single-threaded prereqs — .\scripts\build-release.ps1 -Sequential
powershell -NoProfile -ExecutionPolicy Bypass -File "release/toolbox-portable/start.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "release/toolbox-portable/stop.ps1"
```

---

文档用途：供后续 Agent 在最小上下文下稳定重复打包流程，减少“能打包但不能跑”类回归问题。
