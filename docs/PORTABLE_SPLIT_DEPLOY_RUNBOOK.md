# 内网部署机解耦部署方案（便携包）

目标：在一台 Windows 内网部署机上，把宿主与工具按进程解耦运行，做到单工具维护不影响其他工具。

## 1. 拓扑

- 宿主进程：`toolbox-backend.exe`（端口 `3000`）
  - `TOOLBOX_TOOL_UPSTREAMS=...3001/3002/3003`
- 工具进程（同一个 exe，不同环境变量）：
  - `service-id-registry` -> `3001`
  - `mos-integration-toolbox` -> `3002`
  - `rsa-token-livestream` -> `3003`

所有进程共用同一个 `.env`，同一个 PostgreSQL（RDS）。

## 2. 为什么这样做

- 保持用户入口与前端行为不变（仍访问 `:3000`）。
- 不依赖 Docker，在内网部署机可直接运行。
- 业务解耦：工具进程独立重启/升级（后续可进一步拆为独立包）。
- 可配合 `runtime_status=updating` 在发版期间禁用该工具业务调用。

## 3. 具体实施（已固化）

便携包目录新增：

- `start-split.ps1` / `start-split.cmd`
- `stop-split.ps1` / `stop-split.cmd`
- `tool-control.ps1`（支持 status/start/stop/restart + 指定 tool）
- `restart-tool.cmd <host|service-id|mos|rsa|all>`

### 启动

双击 `start-split.cmd`（或 PowerShell 执行 `.\start-split.ps1`）。

### 停止

双击 `stop-split.cmd`（或 PowerShell 执行 `.\stop-split.ps1`）。

### 单工具重启（发版维护常用）

```powershell
.\restart-tool.cmd mos
```

或：

```powershell
.\tool-control.ps1 -Action restart -Tool service-id
.\tool-control.ps1 -Action status -Tool all
```

## 4. 验证

在部署机执行：

```powershell
Invoke-WebRequest http://127.0.0.1:3000/health -UseBasicParsing
Get-NetTCPConnection -State Listen | ? { $_.LocalPort -in 3000,3001,3002,3003 } | select LocalAddress,LocalPort,OwningProcess
```

并检查日志目录：

- `logs/host-runtime.*.log`
- `logs/tool-service-id-runtime.*.log`
- `logs/tool-mos-runtime.*.log`
- `logs/tool-rsa-runtime.*.log`

## 5. 运维建议

- 升级某工具前，先在管理页把该工具设为 `updating`，避免请求打到升级中实例。
- 单工具故障时可只重启该工具进程（先 `stop-split` 再 `start-split` 是保守路径；后续可加 `restart-tool-*.ps1` 精细脚本）。
- 如果要让工具进程仅监听本机，可在后续版本把工具 `TOOLBOX_HOST` 改成 `127.0.0.1`（当前为统一 `0.0.0.0`，但入口只暴露 3000）。

