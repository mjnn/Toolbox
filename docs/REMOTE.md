# 远程仓库（Git）

本文档为**权威记录**：本仓库默认对应的 GitHub 地址与常用推送命令。若更换托管平台或仓库名，请同步更新本文件与根目录 `README.md` 中的「远程仓库」小节。

## 地址

| 项 | 值 |
|----|-----|
| **HTTPS** | `https://github.com/mjnn/Toolbox.git` |
| **Web** | [https://github.com/mjnn/Toolbox](https://github.com/mjnn/Toolbox) |
| **默认分支** | `main` |
| **远程名** | `origin`（本地克隆后通常已存在） |

## 本机已有仓库时（日常推送）

在仓库根目录执行：

```powershell
git status
git add -A
git commit -m "你的提交说明"
git push origin main
```

若当前分支已设置上游（首次 push 时用过 `git push -u origin main`），可直接：

```powershell
git push
```

## 新机器首次克隆

```powershell
git clone https://github.com/mjnn/Toolbox.git
cd Toolbox
```

复制 `backend/.env.example` 为 `backend/.env` 并配置后再开发（见 `README.md`）。

## 若本机未配置 `origin`

在仓库根目录执行一次：

```powershell
git remote add origin https://github.com/mjnn/Toolbox.git
git branch -M main
git push -u origin main
```

若已存在同名远程但地址错误：

```powershell
git remote set-url origin https://github.com/mjnn/Toolbox.git
```

## SSH（可选）

若使用 SSH 密钥与 GitHub 关联：

```text
git@github.com:mjnn/Toolbox.git
```

配置方式：`git remote set-url origin git@github.com:mjnn/Toolbox.git`
