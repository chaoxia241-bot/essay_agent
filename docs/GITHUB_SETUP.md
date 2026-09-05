# GitHub 推送配置

远程仓库：`git@github.com:chaoxia241-bot/essay_agent.git`

## 1. GitHub 账户设置

在 GitHub 的 `Settings -> SSH and GPG keys -> New SSH key` 中添加公钥。

- Key type 选择 `Authentication Key`
- 工作电脑和个人笔记本建议使用两对不同的 SSH Key
- Title 写清设备，例如 `essay-agent-work-pc`、`essay-agent-personal-laptop`
- 只粘贴 `.pub` 公钥内容；私钥绝不能上传到 GitHub、仓库或聊天

## 2. Windows 本机准备

如果只有 `id_ed25519_github_chaoxia241.pub` 而没有同名无后缀私钥，这对密钥不能用于推送，需要重新生成一对密钥。两台电脑分别生成自己的密钥，不要复制私钥到另一台设备。

已有私钥时，把它放到当前用户的 `.ssh` 目录，并加入 Windows OpenSSH Agent：

```powershell
Get-Service ssh-agent | Set-Service -StartupType Automatic
Start-Service ssh-agent
ssh-add "$env:USERPROFILE\.ssh\id_ed25519_github_chaoxia241"
```

如果文件名不同，把最后一行替换为实际私钥路径。验证 agent 是否持有密钥：

```powershell
ssh-add -l
```

## 3. 建议的 SSH 配置

在 `%USERPROFILE%\.ssh\config` 中为该仓库设置别名，避免两台设备或多个 GitHub 账号串用：

```text
Host github-essay-agent
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github_chaoxia241
    IdentitiesOnly yes
```

然后把仓库 remote 指向别名：

```powershell
git remote set-url origin git@github-essay-agent:chaoxia241-bot/essay_agent.git
ssh -T git@github-essay-agent
```

认证成功时，GitHub 会返回包含用户名的欢迎信息，并说明不提供 shell access；这是正常结果。

## 4. 首次推送

先确认本地没有不应提交的内容：

```powershell
git status
git log -1 --oneline
```

远程仓库为空时：

```powershell
git push -u origin main
```

远程仓库已有 README 或其他提交时，先同步并检查冲突：

```powershell
git fetch origin
git log --oneline --all --decorate -10
git pull --rebase origin main
git push -u origin main
```

不要使用 `--force` 覆盖远程历史。

## 5. 当前检查结论

本地已经完成安全基线提交并配置 `origin`，但当前机器的 `ssh -T`/`push --dry-run` 均因 `Permission denied (publickey)` 失败。下一步只需要在 GitHub 添加对应公钥，并在当前机器加载匹配的私钥，然后重新执行：

```powershell
ssh -T git@github-essay-agent
git push -u origin main
```
