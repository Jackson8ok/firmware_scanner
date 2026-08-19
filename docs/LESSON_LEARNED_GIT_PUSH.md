# 🚨 Git 推送失败 - 根本原因分析与解决方案

**问题日期**: 2026-08-19  
**问题现象**: `git push origin main` 失败，报错 `Host key verification failed`  
**影响范围**: 所有 PAI-DSW 环境下的 Git 操作

---

## 🔍 问题根因

### 直接原因
```
Host key verification failed
```
SSH 无法验证 GitHub 主机指纹，因为 `known_hosts` 文件不存在。

### 根本原因
**PAI-DSW 环境的持久化规则**：
- ✅ **持久化目录**: `/mnt/workspace/`（实例重启后保留）
- ❌ **临时目录**: `/root/`, `/home/` 等（实例重启后**清除**）

**之前的配置**（不完整）：
```bash
# 8 月 17 日配置
mkdir -p /mnt/workspace/.ssh          # ✅ 持久化 SSH 目录
mv /root/.ssh/* /mnt/workspace/.ssh/  # ✅ 迁移密钥
ln -s /mnt/workspace/.ssh /root/.ssh  # ✅ 创建软链接
```

**问题**：
- `/mnt/workspace/.ssh/` **持久化保存**了 SSH 密钥和 known_hosts ✅
- 但 `/root/.ssh` **软链接本身**存储在 `/root/` 目录下 ❌
- **环境重启后**：`/root/.ssh` 软链接被清除，但 `/mnt/workspace/.ssh/` 内容保留
- **结果**：SSH 客户端找不到 `/root/.ssh`，导致验证失败

### 时间线

| 时间 | 事件 | 状态 |
|------|------|------|
| 8 月 17 日 | 初始配置 SSH 持久化 | ✅ 成功 |
| 8 月 17-18 日 | Git 推送正常 | ✅ 工作 |
| 8 月 19 日 | 环境重启 | ⚠️ 软链接丢失 |
| 8 月 19 日 | Git 推送失败 | ❌ Host key verification failed |

---

## ✅ 解决方案（已封装为 Skill）

### 长期修复（已实现）

**已封装为 GitHub Auto Release Skill**

技能位置：`/mnt/workspace/qwenpaw_workspaces/workspaces/default/skills/github_auto_release/`

**1. 自动初始化脚本**
```bash
bash /mnt/workspace/qwenpaw_workspaces/workspaces/default/skills/github_auto_release/init_ssh.sh
```

**2. Git 推送脚本**
```bash
bash /mnt/workspace/qwenpaw_workspaces/workspaces/default/skills/github_auto_release/git_push.sh /path/to/repo main "commit message"
```

**3. Release 创建脚本**
```bash
bash /mnt/workspace/qwenpaw_workspaces/workspaces/default/skills/github_auto_release/create_release.sh username/repo v2.5.0 "标题" docs/RELEASE_NOTES.md
```

**4. 状态检查脚本**
```bash
bash /mnt/workspace/qwenpaw_workspaces/workspaces/default/skills/github_auto_release/check_status.sh
```

**5. 添加到 .bashrc（每次登录自动执行）**
```bash
# ~/.bashrc
if [ -f /mnt/workspace/qwenpaw_workspaces/workspaces/default/skills/github_auto_release/init_ssh.sh ]; then
    source /mnt/workspace/qwenpaw_workspaces/workspaces/default/skills/github_auto_release/init_ssh.sh
fi
```

**详细文档**: `/mnt/workspace/qwenpaw_workspaces/workspaces/default/skills/github_auto_release/README.md`

---

## 📋 检查清单

### 环境重启后必查

```bash
# 1. 检查软链接是否存在
ls -la /root/.ssh
# 应显示：/root/.ssh -> /mnt/workspace/.ssh

# 2. 检查 SSH 密钥
ls -la /mnt/workspace/.ssh/id_ed25519*
# 应显示私钥和公钥

# 3. 检查 known_hosts
ls -la /mnt/workspace/.ssh/known_hosts
# 应显示包含 github.com 条目

# 4. 测试 SSH 连接
ssh -T git@github.com
# 应显示：Successfully authenticated
```

### 自动化验证

```bash
# 运行初始化脚本
source /mnt/workspace/firmware_scanner/scripts/init_ssh.sh

# 应输出：
# 🔐 初始化 SSH 环境...
# ✅ /root/.ssh 软链接已存在且指向正确
# ✅ known_hosts 存在
# ✅ GitHub SSH 连接成功
```

---

## 🎯 Lesson Learned

### 问题 1: 持久化配置不完整
**教训**: 在 PAI-DSW 等临时环境中，**所有非持久化目录下的配置都需自动化重建**

**改进**:
- ✅ 将 SSH 密钥、known_hosts 等数据存储在 `/mnt/workspace/`
- ✅ 将软链接、环境变量等配置写入**初始化脚本**
- ✅ 在 `.bashrc` 中自动执行初始化脚本

### 问题 2: 缺乏自动化
**教训**: 依赖手动执行的操作**一定会被遗忘**

**改进**:
- ✅ 所有环境配置必须**脚本化**
- ✅ 所有脚本必须**自动化执行**（.bashrc / cron / systemd）
- ✅ 所有自动化必须**有日志输出**（便于调试）

### 问题 3: 文档不足
**教训**: 配置过程未记录，导致问题重现时无法快速定位

**改进**:
- ✅ 创建 `LESSON_LEARNED.md` 记录问题根因
- ✅ 创建 `DEPLOYMENT.md` 记录部署步骤
- ✅ 创建 `TROUBLESHOOTING.md` 记录常见问题

---

## 📁 相关文件

| 文件 | 用途 | 位置 |
|------|------|------|
| `init_ssh.sh` | SSH 环境初始化脚本 | `/mnt/workspace/firmware_scanner/scripts/` |
| `.bashrc` | 自动执行初始化 | `~/.bashrc` |
| `LESSON_LEARNED_GIT_PUSH.md` | 本文档 | `/mnt/workspace/firmware_scanner/docs/` |
| `DEPLOYMENT.md` | 部署指南 | `/mnt/workspace/firmware_scanner/docs/` |

---

## ✅ 验证步骤

```bash
# 1. 新终端登录（或重启环境）
# 应自动看到初始化输出

# 2. 检查软链接
ls -la /root/.ssh
# 输出：lrwxrwxrwx 1 root root ... /root/.ssh -> /mnt/workspace/.ssh

# 3. 测试 Git 推送
cd /mnt/workspace/firmware_scanner
git status
git push origin main
# 应成功推送

# 4. 验证 SSH 连接
ssh -T git@github.com
# 应显示：Hi Jackson8ok! You've successfully authenticated...
```

---

## 🔧 快速修复命令（复制粘贴）

```bash
# 如果再次遇到 Host key verification failed
ln -s /mnt/workspace/.ssh /root/.ssh
ssh-keyscan github.com >> /mnt/workspace/.ssh/known_hosts 2>/dev/null
git push origin main
```

---

*创建日期：2026-08-19*  
*创建者：攻城狮阿信 [Jackson]*  
*状态：已解决*
