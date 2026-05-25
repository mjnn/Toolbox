# Agent Skills（本仓库）

跨项目交付能力使用**个人 Skill**（不放在本仓库内）：

| Skill | 路径 |
|-------|------|
| `ecs-github-delivery-ops` | `%USERPROFILE%\.cursor\skills\ecs-github-delivery-ops\` |

用法（任意 Cursor 工作区）：

```text
@ecs-github-delivery-ops 连接 ECS / 部署服务 / push GitHub
```

- Git 远程与分支：以当前仓库 `git remote`、`git branch` 为准。
- 部署步骤：优先当前仓库自带的 `scripts/*deploy*`、`deploy/**`、部署文档；无则走 Skill 中的通用 Compose 流程。
- **镜像推送 / ECS 部署前**：Skill 会要求用户确认阿里云 ACR 对应命名空间与镜像仓库已创建，确认后才 `docker push`。

新机器：复制整个 `ecs-github-delivery-ops` 文件夹到上述个人 Skills 目录即可。
