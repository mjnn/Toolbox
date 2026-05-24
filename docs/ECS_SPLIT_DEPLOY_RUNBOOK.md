# ECS 分拆部署 Runbook（1 Host + N Tools）

本文用于把当前项目部署为：

- `toolbox-host`（统一入口，负责宿主 API + 工具 API 转发）
- `toolbox-tool-<tool-key>`

Host + 多个工具容器共用同一个 PostgreSQL（RDS）数据库。

> 工具可见性说明：split 架构只负责运行时拓扑（Host 转发 + Tool 分拆），最终对外展示哪些工具由“可见性策略”统一控制（Admin API / 配置文件 / 环境变量），不把“单工具默认展示”作为固定规则。

## 0) 版本号规范（固定）

- 统一格式：`vYYYY.MM.DD-<channel>`
- `channel=baseline`：基线版本（示例：`v2026.04.24-baseline1.0`）
- `channel=devdrop`：开发投放版本
- 本 runbook 默认 `HostVersion` 与三工具版本一致；如需差异化再单独传 `ServiceIdVersion/MosVersion/RsaVersion`

## 1) 构建与推送镜像（本机）

```powershell
./scripts/docker-build-push-split.ps1 -HostVersion <版本号>
```

默认 `docker-build-push-split.ps1` 仍会推送 Host + 3 个基线工具标签；新增工具可额外打同仓库标签：

- `mirror_ns/tool_box_host:<版本号>`
- `mirror_ns/tool_box_tools:service-id-registry-<版本号>`
- `mirror_ns/tool_box_tools:mos-integration-toolbox-<版本号>`
- `mirror_ns/tool_box_tools:rsa-token-livestream-<版本号>`

如需工具独立版本：

```powershell
./scripts/docker-build-push-split.ps1 `
  -HostVersion 2026.04.24-h1 `
  -ServiceIdVersion 2026.04.24-s1 `
  -MosVersion 2026.04.24-m1 `
  -RsaVersion 2026.04.24-r1
```

## 2) ECS 部署

```bash
bash scripts/ecs-deploy-split.sh <host-version> '<DATABASE_URL>' <external-ip> 3000

# 可选：配置工具列表（避免每次手工改 compose）
export TOOLBOX_SPLIT_TOOLS="service-id-registry,mos-integration-toolbox,rsa-token-livestream,data-secure-manage"
# 可选：单工具版本覆盖（不配则默认跟 host-version 一致）
export TOOLBOX_SPLIT_TOOL_DATA_SECURE_MANAGE_VERSION="<版本号>"
bash scripts/ecs-deploy-split.sh <host-version> '<DATABASE_URL>' <external-ip> 3000
```

脚本会在 `/srv/apps/tool-box-split` 生成：

- `.env.runtime`
- `compose.yaml`

并启动 4 个容器。

## 2.1) 部署后验证（推荐）

```bash
bash scripts/ecs-verify-split.sh
```

会输出：

- 四容器状态
- `/health`
- `/api/v1/tools`
- 三个工具特征路由烟测状态码（不应是 host 层 404）

### 2.2) 日常巡检（建议）

```bash
bash scripts/ecs-audit-split.sh
```

巡检内容包括：

- compose 状态
- host `/health`
- `/api/v1/tools`
- 三条工具 feature 路由烟测（应为 401/403 或业务码，不应是 host 转发缺失导致的 404）
- 备份与回滚提示

## 3) 关键机制

- Host 配置：
  - `TOOLBOX_TOOL_UPSTREAMS=service-id-registry=http://toolbox-tool-service-id:3000,mos-integration-toolbox=http://toolbox-tool-mos:3000,rsa-token-livestream=http://toolbox-tool-rsa:3000`
- Tool 配置：
  - 每个工具容器对外提供 `/api/v1/tools/{tool_id}/features/*` 能力

这样外部入口与既有 API 路径不变，功能通过宿主按 `tool_id -> tool.name` 查库后转发到对应工具容器。

## 4) 回滚

若需快速回滚到旧单容器：

```bash
bash scripts/ecs-rollback-split.sh
```

等价于：

1. 停止分拆栈：`tool-box-split`
2. 启动旧栈：`tool-box-public`

## 5) 排障：`KeyError: 'ContainerConfig'`（docker-compose 1.29）

**现象**：ECS 上若只有 Ubuntu `docker.io` 自带的 `/usr/bin/docker-compose`（常见为 **1.29.x**），在 `up` 重建容器时可能对较新镜像报错 `KeyError: 'ContainerConfig'`。

**应急（不升级 compose，先恢复服务）**：在 `/srv/apps/tool-box-split` 下对当前 `compose.yaml` + `.env.runtime` 做一次干净重建：

```bash
cd /srv/apps/tool-box-split
docker-compose -p tool-box-split --env-file .env.runtime -f compose.yaml down --remove-orphans
docker-compose -p tool-box-split --env-file .env.runtime -f compose.yaml up -d --remove-orphans
```

**根治（推荐）**：安装 **Docker Compose v2**（二选一即可）。

1. **独立二进制（适合仅 docker.io、无官方 Docker apt 源的主机）**  
   将仓库中的 `scripts/ecs-install-compose-v2-bin.sh` 拷到 ECS 后执行（需能稳定访问 GitHub 下载约 62MiB，勿中断）：

   ```bash
   sudo bash ecs-install-compose-v2-bin.sh
   ```

   成功后 `/usr/local/bin/docker-compose` 在 PATH 中优先于 `/usr/bin/docker-compose`，`ecs-deploy-split.sh` / `ecs-deploy-public.sh` 会自动选用 v2。

2. **Docker 官方 apt 源 + `docker-compose-plugin`**  
   按 Docker 文档为 Ubuntu 配置 `download.docker.com` 源后：`apt-get install -y docker-compose-plugin`，使 `docker compose version` 可用。

**手工指定 compose 命令**（调试）：部署前可导出：

```bash
export TOOLBOX_COMPOSE_CMD="/usr/local/bin/docker-compose"
bash scripts/ecs-deploy-split.sh ...
```

