# 项目 Agent Skills

## 全项目通用（推荐）

个人 Skill **`ecs-github-delivery-ops`** 已安装在：

- Windows：`%USERPROFILE%\.cursor\skills\ecs-github-delivery-ops\`
- macOS/Linux：`~/.cursor/skills/ecs-github-delivery-ops/`

**任意 Cursor 工作区**均可使用：

```text
@ecs-github-delivery-ops 连接 ECS 并 docker ps
@ecs-github-delivery-ops 部署服务 xxx 到 ECS
@ecs-github-delivery-ops 提交并 push 当前仓库到 GitHub
```

- GitHub 地址以当前仓库 `git remote get-url origin` 为准（不限 Toolbox）。
- 打开 **Toolbox_Project** 时，Agent 会自动识别 Toolbox 脚本（split 部署等）；其他仓库走通用 Compose 流程。

## 本目录遗留

| Skill | 说明 |
|-------|------|
| `toolbox-delivery-ops/` | 兼容别名，内容已迁移到个人 `ecs-github-delivery-ops` |

新机器只需复制个人 Skills 目录，无需每个仓库各拷一份。
