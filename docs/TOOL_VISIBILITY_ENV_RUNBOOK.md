# 内外网工具可见性运维手册

用于管理员按环境（内网/外网）控制可见工具，并说明系统如何识别当前环境。

## 1. 环境识别规则

后端按以下优先级判断当前请求环境：

1. `TOOLBOX_DEPLOY_ENV`（`internal` / `external`）强制指定
2. 请求 Host 命中 `external_hosts`（默认包含 `47.116.180.173`）判定为外网
3. 其余请求默认内网

实现位置：`backend/app/core/tool_visibility.py`。

## 2. 管理入口

管理员页面：`数据库优化` 页面下的 **内外网工具可见性** 区块。

可配置项：

- 外网主机/IP 列表（支持逗号或换行）
- 内网可见工具列表
- 外网可见工具列表

配置会持久化到：

- `backend/runtime/tool_visibility.json`

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
