# 外网发布版发布说明（固定流程）

本方案用于发布“外网版”。

## 当前固定流程（默认）

- 默认采用 **分拆发布**：`tool_box_host` + `tool_box_tools`（1 Host + 3 Tools）。
- 仅当明确回滚历史架构时，才使用旧的单镜像 `tool_box` 流程。
- 工具展示统一走“可见性策略”控制（Admin API / `tool_visibility.json` / 运行时环境变量），不再以“单工具默认展示”作为发布前提。
- 发布前必须先完成“范围判定（宿主/工具/混合）”并按最小耦合颗粒发布，版本与变更记录填写模板见 `docs/RELEASE_RUNBOOK.md` §0.2。
- 版本号统一规则：`vYYYY.MM.DD-<channel>`，其中 `<channel>` 固定为：
  - `baseline`：基线版本（示例：`v2026.04.24-baseline1.0`）
  - `devdrop`：开发投放版本

代理与负载均衡优化流程见：`docs/ECS_PROXY_LB_RUNBOOK.md`。

## 1. 关键原则（保证内外网联动）

- **交付边界**：本页描述 **ECS + Docker 镜像** 外网版；**不包含** Windows 内网便携包（由 `scripts/build-release.ps1` 在打包机生成）。外网发布步骤勿把便携包目录打进镜像。
- 内网管理端与外网发布版必须连接同一个 PostgreSQL（同一 `DATABASE_URL`）。
- 外网版通过 `TOOLBOX_VISIBLE_TOOL_KEYS=service-id-registry` 限制可见工具。
- 工具发版/维护时可在内网将目标工具 `runtime_status` 置为 `updating`（或后续自动化），外网/内网该工具业务 API 将统一 503，直至恢复为 `active`；详见 `docs/ECS_TOOL_RUNTIME_TOPOLOGY.md`。
- 可选分进程：通过宿主 `TOOLBOX_TOOL_UPSTREAMS` 将工具流量转发到独立工具容器，便于多容器拆分；需配合网关/代理路由，见同文档。
- 环境识别默认以外网 IP `47.116.180.173` 为基准（`TOOLBOX_EXTERNAL_PUBLIC_IP` / Admin 可改）。
- 工具负责人/管理员仍在内网管理；外网用户产生的申请、操作日志、反馈会写入同一库并在内网可见。

## 2. 本机构建并推送镜像（固定：split）

镜像名规则（固定）：

- `crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/tool_box_host:<版本号>`
- `crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/tool_box_tools:service-id-registry-<版本号>`
- `crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/tool_box_tools:mos-integration-toolbox-<版本号>`
- `crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/tool_box_tools:rsa-token-livestream-<版本号>`

在项目根目录执行（PowerShell）：

```powershell
./scripts/docker-build-push-split.ps1 -HostVersion <版本号>
```

脚本会自动执行：`docker build`、四标签打标、`docker login`、四镜像推送。

## 3. ECS 部署（Ubuntu，固定：split）

将脚本上传到 ECS 后执行（或直接复制命令）：

```bash
bash scripts/ecs-deploy-split.sh <版本号> '<DATABASE_URL>' 47.116.180.173 3000
```

该脚本会：

1. 登录阿里云镜像仓库并拉取 4 个 split 镜像
2. 在 `/srv/apps/tool-box-split` 生成 `compose.yaml` 与 `.env.runtime`
3. 以 Host 统一入口 + Tool 独立容器方式启动/替换服务
4. 保持外部访问路径不变（`/toolbox/`、`/api/v1/`、`/health`）

配套：

- 验证：`bash scripts/ecs-verify-split.sh`
- 回滚：`bash scripts/ecs-rollback-split.sh`
- 详细说明：`docs/ECS_SPLIT_DEPLOY_RUNBOOK.md`

## 4. 手动部署命令（不使用脚本）

```bash
docker login --username=MjnnAliCloud crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com
docker pull crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/tool_box:<版本号>

mkdir -p /srv/apps/tool-box-public
cd /srv/apps/tool-box-public

cat > .env.runtime <<'EOF'
SERVICE_NAME=tool-box-public
IMAGE=crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/tool_box:<版本号>
HOST_PORT=3000
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DB?sslmode=prefer
EXTERNAL_PUBLIC_IP=47.116.180.173
BACKEND_CORS_ORIGINS=["http://47.116.180.173","https://47.116.180.173","http://localhost","http://127.0.0.1"]
EOF

cat > compose.yaml <<'EOF'
services:
  toolbox-public:
    container_name: ${SERVICE_NAME}
    image: ${IMAGE}
    restart: unless-stopped
    ports:
      - "${HOST_PORT}:3000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      TOOLBOX_EXTERNAL_PUBLIC_IP: ${EXTERNAL_PUBLIC_IP}
      TOOLBOX_VISIBLE_TOOL_KEYS: service-id-registry
      TOOLBOX_WORKERS: "2"
      SQLALCHEMY_POOL_SIZE: "12"
      SQLALCHEMY_MAX_OVERFLOW: "8"
      SQLALCHEMY_POOL_TIMEOUT: "45"
      SQLALCHEMY_POOL_RECYCLE: "1800"
      SQLALCHEMY_STATEMENT_TIMEOUT_MS: "15000"
      BACKEND_CORS_ORIGINS: ${BACKEND_CORS_ORIGINS}
EOF

docker compose --project-name tool-box-public --env-file .env.runtime -f compose.yaml up -d
```

## 5. 验证点

- 外网版“所有工具/我的工具”列表仅显示 Service ID 注册管理。
- 工具负责人在内网管理页修改 Service ID 规则后，外网端刷新可见。
- 外网用户提交的操作、申请、反馈在内网管理端可查询。
- 外网视角校验命令：
  - `curl -H 'Host: 47.116.180.173' http://127.0.0.1:3000/api/v1/tools/?skip=0&limit=10`
  - 结果应仅包含 `service-id-registry`。

## 6. ECS / 镜像导入机离线包（可选）

> 本节「导入机」指能执行 `docker load` / `docker compose` 的 **Linux 主机（通常为 ECS 或跳板机）**，与内网 **Windows 便携包部署机**（`release/toolbox-portable`）不是同一套流程。

若导入机无法直接访问镜像仓库，可在本机导出：

```bash
docker save -o release/tool_box_<版本号>_ecs.tar \
  crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/tool_box:<版本号>
```

在目标主机导入并运行：

```bash
docker load -i tool_box_<版本号>_ecs.tar
```

若容器卡在 `Waiting for application startup`，通常是 ECS 无法连通 RDS，请检查：

- RDS 白名单/安全组是否放通 ECS 出口 IP。
- RDS 端口 `5432` 是否可从 ECS 访问。

