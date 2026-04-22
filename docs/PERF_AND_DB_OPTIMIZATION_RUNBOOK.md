---
title: MOS综合工具箱 — 数据库优化与性能验收 Runbook
description: >-
  沉淀本项目数据库配置优化、性能压测与发布后验收流程。覆盖 Dashboard 管理入口、
  后端关键优化点、k6 脚本与达标阈值。
version: 1.0
---

# MOS综合工具箱 · 数据库优化与性能验收 Runbook

## 1. 文档目的

本文档用于持久化以下上下文：

1. 数据库优化能力已从工具子页上移到系统级管理入口。
2. 项目已建立 k6 压测与报告脚本，并接入发布产物。
3. 当前 PostgreSQL 场景下的已验证性能优化策略与验收标准。

本手册与 `docs/RELEASE_RUNBOOK.md`、`docs/PORTABLE_PACKAGING_AGENT_RUNBOOK.md` 配合使用。

---

## 2. 系统级数据库优化入口（已落地）

### 2.1 前端入口与权限

- Dashboard 左侧栏新增「数据库优化」入口（仅超管可见）。
- 页面路由为系统级页面（不再归属于某个工具管理子页）。
- 访问控制：需要登录且管理员权限。

### 2.2 后端 API（系统级）

数据库优化相关接口统一收敛在 admin 域：

- `GET /api/v1/admin/system/db-optimization`
- `PUT /api/v1/admin/system/db-optimization`
- `POST /api/v1/admin/system/db-optimization/ping`

接口语义：

- 读取当前/推荐/已保存参数与数据库连通状态信息。
- 保存连接池和 SQL 超时参数（可选写入 `.env`，生效通常需重启）。
- 进行数据库连通性延迟探测（ping）。

---

## 3. PostgreSQL 连接参数（项目约定）

后端连接参数由环境变量驱动（PostgreSQL 生效）：

- `SQLALCHEMY_POOL_SIZE`（默认 4）
- `SQLALCHEMY_MAX_OVERFLOW`（默认 2）
- `SQLALCHEMY_POOL_TIMEOUT`（默认 30）
- `SQLALCHEMY_POOL_RECYCLE`（默认 1800）
- `SQLALCHEMY_STATEMENT_TIMEOUT_MS`（默认 15000）

本次会话中用于达标的基线配置（已写入 `backend/.env`）：

- `SQLALCHEMY_POOL_SIZE=12`
- `SQLALCHEMY_MAX_OVERFLOW=8`
- `SQLALCHEMY_POOL_TIMEOUT=60`
- `SQLALCHEMY_POOL_RECYCLE=1800`
- `SQLALCHEMY_STATEMENT_TIMEOUT_MS=15000`

注意：总连接数近似为 `workers × (pool_size + max_overflow)`，需结合 RDS 规格评估。

---

## 4. 本次性能瓶颈与优化沉淀

### 4.1 诊断结论（会话过程）

- 早期重载压测出现 `QueuePool limit ... timeout`，本质是连接池耗尽。
- 仅扩大连接池后，超时显著缓解，但尾延迟仍偏高。
- 通过请求级耗时拆分发现：慢请求不全是 SQL 执行本身，应用层额外开销显著。

### 4.2 已落地优化

1. `/api/v1/tools/` 查询合并为单次 JOIN，减少一次 DB 往返。
2. token 增加 `uid` claim，中间件解析用户时避免每请求额外查库。
3. 高频只读路径（`/api/v1/tools/`、`/health`）跳过 `APIAccessLog` 持久化，降低写放大。
4. 增加请求级可观测性字段：
   - `latency_ms`
   - `db_ms`
   - `app_ms`
   - `db_count`
   - `pool_status`

这些改动叠加后，P95/P99 明显收敛并稳定通过验收阈值。

---

## 5. 性能验收标准与脚本

### 5.1 验收阈值（默认）

- `http_req_duration p(95) < 1200ms`
- `http_req_duration p(99) < 2000ms`
- `http_req_failed rate < 2%`

### 5.2 脚本清单

- `perf/k6-api.js`：压测场景定义（支持环境变量控制档位）
- `scripts/run-perf-k6.ps1`：单次压测（`baseline/stress/custom`）
- `scripts/report-perf-k6.ps1`：读取 summary JSON 并输出汇总/Markdown
- `scripts/run-perf-suite.ps1`：一键执行 baseline + stress + report

### 5.3 常用命令

单次压力档：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-perf-k6.ps1 -BaseUrl "http://127.0.0.1:3003" -Token "<token>" -Profile stress
```

一键验收（推荐）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-perf-suite.ps1 -BaseUrl "http://127.0.0.1:3003" -Token "<token>" -Label "postgres"
```

快速验收（较短时长）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-perf-suite.ps1 -BaseUrl "http://127.0.0.1:3003" -Token "<token>" -Label "postgres" -Quick
```

---

## 6. 发布包与部署机验收（新增约定）

`scripts/build-release.ps1` 已接入性能验收脚本，发布包会包含：

- `scripts/run-perf-k6.ps1`
- `scripts/run-perf-suite.ps1`
- `scripts/report-perf-k6.ps1`
- `perf/k6-api.js`
- `perf/README.md`
- `perf/results/`

部署机可在服务启动后直接执行 `run-perf-suite.ps1` 做交付验收，不再需要手工补脚本。

---

## 7. 防回归注意事项

1. 不要把数据库优化入口重新放回某个工具管理子页。
2. 保持系统级 API 前缀为 `/api/v1/admin/system/db-optimization*`。
3. 若恢复高频接口审计落库，需重新压测确认尾延迟不回退。
4. 若调整 worker 或池参数，务必用 `run-perf-suite.ps1` 复验。
5. 发布脚本必须保证 PyInstaller 失败即中断，禁止“失败后继续组包”。

---

文档用途：确保后续 Agent 在性能优化、回归验收、部署交付时，复用同一套稳定流程与阈值。
