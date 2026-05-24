# ECS 当前结构与影响说明（2026-04）

## 1) 当前结构（已生效）

### 1.1 服务编排层

- 统一目录：`/srv/apps`
- 标准形态：每个服务使用 `compose.yaml + .env.runtime`
- 已迁移服务：
  - `/srv/apps/tool-box-public`（工具箱外网服务）
  - `/srv/apps/sim_api`
  - `/srv/apps/file_server`
  - `/srv/apps/fund_value_em`

### 1.2 运行中的容器

- `tool-box-public`（`3000`）
- `tool-box-public-r2`（`3001`，用于工具箱负载均衡）
- `sim_api`（`5000`）
- `file_server`（`8888`）
- `fund_value_em`（`8001 -> 8000`）
- `srs-server`（直播相关，暂未迁移）

### 1.3 历史容器治理

- 已完成 stale 容器清理（`Created/Exited`）。
- 当前白名单保留：
  - `get_dp_data`
  - `srs`
- 清理审计快照位于：`/srv/apps/_inventory/`

### 1.4 代理与负载均衡

- 入口仍是宿主机 Nginx（80 端口）。
- 工具箱新增并已生效：
  - `/toolbox/`
  - `/api/v1/`
  - `/health`
- 工具箱 upstream 负载均衡池：
  - `127.0.0.1:3000`
  - `127.0.0.1:3001`
- 旧入口继续保留：
  - `/FileServer/`（301 到 `:8888`）
  - `/FundEm/`（反代到 `:8001`）
  - `/TokenLiveStream`、`/GetSIMInfo/`、`/AccessRepo/`

## 2) 对客户端调用的影响

## 2.1 不影响（兼容保留）

- 既有 `FileServer/FundEm/TokenLiveStream/GetSIMInfo` 路径仍可按原方式调用。
- `tool-box` 的核心 API 路径 `/api/v1/*` 未改契约，仅上游变为 Nginx -> upstream。
- 外网工具可见性策略仍生效：`Host: 47.116.180.173` 仅返回 `service-id-registry`。

## 2.2 可能观察到的变化（非破坏性）

- `tool-box` 由单实例变为双实例，响应来源实例不固定（负载均衡正常现象）。
- 某些路径对 `HEAD` 请求返回 `405`（服务仅支持 `GET`），对浏览器和常规 GET 客户端无影响。
- `FileServer` 路径仍是 301 跳转，如客户端不跟随重定向需保持原端口直连逻辑。

## 2.3 风险边界与建议

- 仍建议客户端优先走 Nginx 入口，不要直连容器端口。
- 若有严格健康检查器，请用 `GET` 方式请求 `/health`，避免 `HEAD` 误判。
- 扩容 `tool-box` 副本时，确保 Nginx upstream 与实际副本端口一致。

## 3) 可复用运维逻辑

- 白名单清理 stale：
  - `scripts/ecs-clean-stale-containers.sh`
- 迁移 legacy 容器到 compose：
  - `scripts/ecs-migrate-legacy-services.sh`
- 外网工具箱发布：
  - `scripts/ecs-deploy-public.sh`
- 工具箱代理启用：
  - `scripts/ecs-nginx-enable-toolbox.sh`
- 工具箱副本扩容：
  - `scripts/ecs-scale-toolbox-replicas.sh`

## 4) 未来改造建议

- 把 `srs-server` 与 `get_dp_data` 也纳入 `/srv/apps/<service>/compose.yaml`。
- 给 Nginx 增加域名与 TLS，减少 IP 直连和明文 HTTP。
- 将 `/srv/apps/_inventory` 快照纳入定时巡检任务（周级别）。
