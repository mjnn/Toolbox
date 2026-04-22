# 外网发布版（Service ID 单工具）发布说明

本方案用于发布“外网版”，默认仅展示并开放 `service-id-registry` 工具。

## 1. 关键原则（保证内外网联动）

- 内网管理端与外网发布版必须连接同一个 PostgreSQL（同一 `DATABASE_URL`）。
- 外网版通过 `TOOLBOX_VISIBLE_TOOL_KEYS=service-id-registry` 限制可见工具。
- 环境识别默认以外网 IP `47.116.180.173` 为基准（`TOOLBOX_EXTERNAL_PUBLIC_IP` / Admin 可改）。
- 工具负责人/管理员仍在内网管理；外网用户产生的申请、操作日志、反馈会写入同一库并在内网可见。

## 2. 本机构建并推送镜像

镜像名规则：

- `crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/tool_box:<版本号>`

在项目根目录执行（PowerShell）：

```powershell
./scripts/docker-build-push.ps1 -VersionTag <版本号>
```

脚本会自动执行：

1. `docker build`
2. `docker login --username=MjnnAliCloud crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com`
3. `docker push`

## 3. ECS 部署（Ubuntu）

将脚本上传到 ECS 后执行（或直接复制命令）：

```bash
bash scripts/ecs-deploy-public.sh <版本号> 'postgresql+psycopg2://USER:PASSWORD@HOST:5432/DB?sslmode=prefer' 3000
```

该脚本会：

1. 登录阿里云镜像仓库
2. 拉取镜像
3. 检查端口是否占用
4. 启动容器（仅开放 `service-id-registry`）

## 4. 手动部署命令（不使用脚本）

```bash
docker login --username=MjnnAliCloud crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com
docker pull crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/tool_box:<版本号>

# 选择空闲端口（示例 3000）
ss -ltn

docker run -d \
  --name tool-box-public \
  --restart unless-stopped \
  -p 3000:3000 \
  -e DATABASE_URL='postgresql+psycopg2://USER:PASSWORD@HOST:5432/DB?sslmode=prefer' \
  -e TOOLBOX_EXTERNAL_PUBLIC_IP='47.116.180.173' \
  -e TOOLBOX_VISIBLE_TOOL_KEYS='service-id-registry' \
  -e TOOLBOX_WORKERS='1' \
  -e BACKEND_CORS_ORIGINS='["http://47.116.180.173","https://47.116.180.173","http://localhost","http://127.0.0.1"]' \
  crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/tool_box:<版本号>
```

## 5. 验证点

- 外网版“所有工具/我的工具”列表仅显示 Service ID 注册管理。
- 工具负责人在内网管理页修改 Service ID 规则后，外网端刷新可见。
- 外网用户提交的操作、申请、反馈在内网管理端可查询。
- 外网视角校验命令：
  - `curl -H 'Host: 47.116.180.173' http://127.0.0.1:3000/api/v1/tools/?skip=0&limit=10`
  - 结果应仅包含 `service-id-registry`。

## 6. 部署机离线包（可选）

若部署机无法直接访问镜像仓库，可在本机导出：

```bash
docker save -o release/tool_box_<版本号>_ecs.tar \
  crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/tool_box:<版本号>
```

部署机导入并运行：

```bash
docker load -i tool_box_<版本号>_ecs.tar
```

若容器卡在 `Waiting for application startup`，通常是 ECS 无法连通 RDS，请检查：

- RDS 白名单/安全组是否放通 ECS 出口 IP。
- RDS 端口 `5432` 是否可从 ECS 访问。

