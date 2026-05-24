# ECS 服务目录规范

建议在 ECS 上将服务统一收敛到 `/srv/apps`：

```text
/srv/apps/
  tool-box-public/
    compose.yaml
    .env.runtime
  sim_api/
    compose.yaml
    .env.runtime
  file_server/
    compose.yaml
    .env.runtime
  fund_value_em/
    compose.yaml
    .env.runtime
```

## 目标

- 使用固定服务名，避免默认随机容器名导致排障困难。
- 每个服务用 `compose.yaml + .env.runtime` 双文件管理，便于复盘与回滚。
- 服务配置与运行命令标准化，减少手工 `docker run` 漂移。

## 推荐操作命令

```bash
cd /srv/apps/tool-box-public
docker compose --project-name tool-box-public --env-file .env.runtime -f compose.yaml up -d
docker compose --project-name tool-box-public --env-file .env.runtime -f compose.yaml ps
docker compose --project-name tool-box-public --env-file .env.runtime -f compose.yaml logs --tail=100
```

> 若 ECS 仅安装 `docker-compose`（v1），将命令等价替换为 `docker-compose -p tool-box-public ...`。

## 与当前仓库的关系

- `scripts/ecs-deploy-public.sh` 会自动在 `/srv/apps/tool-box-public` 生成上述文件并执行部署。
- `deploy/ecs/tool-box-public/` 保留模板，便于人工审阅、复制到其他服务。
- `scripts/ecs-clean-stale-containers.sh` 按白名单清理 `Created/Exited` 容器，并写入 `_inventory` 快照。
- 版本治理推荐：部署脚本会写入 `TOOLBOX_VERSION/TOOLBOX_SPEC_REVISION/TOOLBOX_CHANGELOG`，供 `/api/v1/meta/version` 返回，宿主可在“工具管理 → 版本管理”一键同步记录。
- 其他迁移模板位于：
  - `deploy/ecs/sim_api/`
  - `deploy/ecs/file_server/`
  - `deploy/ecs/fund_value_em/`
- `scripts/ecs-migrate-legacy-services.sh` 用于把旧的 `docker run` 容器迁移到 `/srv/apps/<service>/compose.yaml` 管理。
