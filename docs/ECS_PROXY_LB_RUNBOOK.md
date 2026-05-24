# ECS 代理与负载均衡 Runbook

本文用于优化 ECS 上 `tool-box-public` 的入口代理与负载均衡能力。

## 1. 目标

- 保留现有业务路径不变（如 `/GetSIMInfo/`、`/FundEm/`）。
- 为工具箱新增统一入口：
  - `http://<ecs-ip>/toolbox/`
  - `http://<ecs-ip>/api/v1/...`
  - `http://<ecs-ip>/health`
- 使用 Nginx `upstream` 统一后端池，为横向扩容预留能力。

## 2. 配置文件

- `deploy/ecs/nginx/toolbox-upstream.conf`
  - `least_conn`
  - `keepalive 64`
  - 默认后端 `127.0.0.1:3000`
  - 可选副本 `127.0.0.1:3001`
- `deploy/ecs/nginx/toolbox-locations.conf`
  - `/toolbox/` 代理到后端根路径
  - `/api/v1/` 代理到后端 API
  - `/health` 代理到后端健康检查

## 3. 一键启用

在 ECS 执行：

```bash
bash scripts/ecs-nginx-enable-toolbox.sh
```

脚本会自动：

1. 写入 `/etc/nginx/conf.d/toolbox-upstream.conf`
2. 写入 `/etc/nginx/snippets/toolbox-locations.conf`
3. 在 `/etc/nginx/sites-enabled/default` 中注入 include
4. `nginx -t` 检查并 `systemctl reload nginx`

## 4. 扩容为多副本

在 ECS 执行：

```bash
bash scripts/ecs-scale-toolbox-replicas.sh 2
```

> 说明：ECS 若未安装 `docker compose` 子命令，可使用 `docker-compose`（v1）执行等价命令。

说明：

- 将新增 `tool-box-public-r2`，默认映射到 `3001`。
- 若继续扩容到 3，则新增 `tool-box-public-r3` 映射到 `3002`，以此类推。
- 脚本会自动重写 `toolbox-upstream.conf` 的后端池并 reload nginx。

## 5. 验证

```bash
curl -sS http://127.0.0.1/health
curl -sS http://127.0.0.1/api/v1/tools/?skip=0&limit=10
curl -sS http://127.0.0.1/toolbox/
```

建议同时检查：

- `sudo nginx -t`
- `sudo systemctl status nginx`
- `docker ps --filter name=tool-box-public`
