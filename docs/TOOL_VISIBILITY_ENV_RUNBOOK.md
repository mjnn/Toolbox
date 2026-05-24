# 内外网工具可见性运维手册

用于管理员按环境（内网/外网）控制可见工具，并说明系统如何识别当前环境。

## 1. 环境识别规则

后端按以下优先级判断当前请求环境：

1. `TOOLBOX_DEPLOY_ENV`（`internal` / `external`）强制指定
2. 请求 Host 命中 `external_hosts`（默认包含 `47.116.180.173`）判定为外网
3. 其余请求默认内网

实现位置：`backend/app/core/tool_visibility.py`。

## 2. 管理入口

管理员页面：Dashboard 侧栏 **其他配置** 中的 **内外网工具可见性** 区块。

可配置项：

- 外网主机/IP 列表（支持逗号或换行）
- 内网可见工具列表
- 外网可见工具列表

配置会持久化到：

- `backend/runtime/tool_visibility.json`

### 2.1 与启动环境变量、容器持久化的关系（避免误解）

- **无配置文件时**：后端启动会读取默认逻辑；其中外网可见工具键会合并环境变量 **`TOOLBOX_VISIBLE_TOOL_KEYS`**（逗号分隔）作为 `external_visible_tool_keys` 的初始值（实现见 `backend/app/core/tool_visibility.py` 的 `_default_config`）。因此 **首次 ECS / compose 仅配 env** 即可得到与外网 Runbook 一致的默认行为。
- **Admin 保存后**：配置写入上述 **JSON 文件**（不是 PostgreSQL 表）。在 **Docker 未挂载卷** 时，该文件位于容器可写层，**重建容器且未挂载同路径卷** 可能丢失 Admin 修改；需要长期保留时应在编排中为 `backend/runtime` 挂卷或把期望配置固化进镜像/部署流程。
- **与 `TOOLBOX_DEPLOY_ENV` 的关系**：若设置 `TOOLBOX_DEPLOY_ENV=internal` 或 `external`，请求环境判定以该变量为准（见第 1 节），此时仍按当前环境从配置中读取对应可见工具列表。

## 3. 后端 API

- `GET /api/v1/admin/system/tool-visibility`
- `PUT /api/v1/admin/system/tool-visibility`

返回数据包含：

- 当前请求判定环境（`current_runtime_env`）
- 判定来源（`runtime_env_source`）
- 主机/IP 配置和内外网工具可见性配置

## 4. 发布默认值建议

外网发布默认建议：

- `TOOLBOX_EXTERNAL_PUBLIC_IP=47.116.180.173`
- `TOOLBOX_VISIBLE_TOOL_KEYS=service-id-registry`
- `BACKEND_CORS_ORIGINS=["http://47.116.180.173","https://47.116.180.173","http://localhost","http://127.0.0.1"]`

## 5. 验证命令

内网（默认 Host）：

```bash
curl 'http://127.0.0.1:3000/api/v1/tools/?skip=0&limit=10'
```

外网（模拟 Host）：

```bash
curl -H 'Host: 47.116.180.173' 'http://127.0.0.1:3000/api/v1/tools/?skip=0&limit=10'
```

若外网配置为单工具，第二条结果应仅含 `service-id-registry`。
