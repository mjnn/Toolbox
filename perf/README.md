# API P95/P99 压测说明（k6）

本目录提供一套可直接执行的接口压测模板，用于观察 `P95/P99`。

## 1. 前置条件

- 已安装 [k6](https://k6.io/docs/get-started/installation/)
- 已拿到可用 `access_token`
- 后端服务可访问（默认 `http://127.0.0.1:3001`）

## 2. 快速执行

在仓库根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-perf-k6.ps1 -Token "<你的token>" -Profile stress
```

若要同时测某个工具管理接口（`usage-logs`），再加 `ToolId`：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-perf-k6.ps1 -Token "<你的token>" -ToolId "2" -Profile stress
```

若要导出 JSON 汇总：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-perf-k6.ps1 -Token "<你的token>" -ToolId "2" -Profile baseline -OutJson ".\perf\k6-summary.json"
```

### 档位说明

- `baseline`：轻载（默认 3 VU 稳态）  
- `stress`：压力（默认 10 VU 稳态）  
- `custom`：完全自定义（配合 `-StartVus/-SteadyTargetVus/-RampDuration/-SteadyDuration/-RampDownDuration`）

## 3. 一键跑整套（baseline + stress + report）

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-perf-suite.ps1 -BaseUrl "http://127.0.0.1:3003" -Token "<你的token>" -Label "postgres"
```

会生成：

- baseline 结果 JSON
- stress 结果 JSON
- 汇总报告 Markdown（含是否通过阈值）

快速验收模式（更短时长）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-perf-suite.ps1 -BaseUrl "http://127.0.0.1:3003" -Token "<你的token>" -Label "postgres" -Quick
```

## 4. 当前压测覆盖

脚本 `perf/k6-api.js` 默认会打：

- `GET /api/v1/tools/?skip=0&limit=20`
- 若传入 `TOOL_ID`，追加：
  - `GET /api/v1/admin/tools/{tool_id}/usage-logs?skip=0&limit=20`

并发模型：

- 30 秒升到 5 VU
- 2 分钟稳态 10 VU
- 30 秒降到 0

## 5. 如何看 P95/P99

关注输出里的 `http_req_duration`：

- `p(95)` -> P95
- `p(99)` -> P99

经验参考（仅供初筛）：

- P95 < 300ms：很好
- P95 300~800ms：可接受
- P95 > 800ms：用户会明显感知慢
- P99 > 1500~2000ms：通常需要专项优化

## 6. 注意事项

- 压测前先预热，避免首次连接影响结果。
- 线上压测要先评估风险，建议从低并发开始。
- 压测时同步观察数据库慢 SQL、连接池占用、锁等待，结论更准确。
