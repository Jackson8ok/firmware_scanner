# PAI-DSW 持久化存储规则

## 核心原则

**只有 `/mnt/workspace/` 目录是持久化的**，其他位置（如 `/root/`、`/tmp/`、`/home/`）在实例重启后都会丢失。

## 必须放在 /mnt/workspace/ 的内容

| 类型 | 正确路径 | 错误路径 | 说明 |
|-----|---------|---------|------|
| SSH 密钥 | `/mnt/workspace/.ssh/id_ed25519` | `/root/.ssh/id_ed25519` | 重启后丢失 |
| 项目代码 | `/mnt/workspace/firmware_scanner/` | `/home/user/project/` | 重启后丢失 |
| 缓存数据 | `/mnt/workspace/firmware_scanner/cache/` | `/tmp/cache/` | 重启后丢失 |
| 数据库 | `/mnt/workspace/firmware_scanner/db/` | `/var/lib/xxx` | 重启后丢失 |
| 日志文件 | `/mnt/workspace/firmware_scanner/logs/` | `/var/log/xxx` | 重启后丢失 |

## SSH 配置正确做法

```bash
# 1. 在 workspace 下创建 .ssh 目录
mkdir -p /mnt/workspace/.ssh
chmod 700 /mnt/workspace/.ssh

# 2. 生成密钥到 workspace
ssh-keygen -t ed25519 -f /mnt/workspace/.ssh/id_ed25519 -N "" -C "your@email.com"

# 3. 创建软链接到标准位置（可选，方便工具自动发现）
ln -sf /mnt/workspace/.ssh /root/.ssh

# 4. 设置 Git 使用 workspace 的 SSH 目录
git config --global core.sshCommand "ssh -i /mnt/workspace/.ssh/id_ed25519"
```

## 检查清单

项目部署后检查：
- [ ] SSH 密钥在 `/mnt/workspace/.ssh/`
- [ ] 所有数据文件在 `/mnt/workspace/` 下
- [ ] 没有硬编码 `/root/`、`/tmp/`、`/home/` 路径
- [ ] 配置文件引用的是 workspace 路径

## 本次教训

**时间**: 2026-08-17  
**问题**: SSH 密钥生成在 `/root/.ssh/`，实例重启后丢失，导致 `git push` 失败  
**根因**: 默认 `ssh-keygen` 会写到 `/root/.ssh/`，没有指定到 workspace  
**解决**: 
1. 密钥移到 `/mnt/workspace/.ssh/`
2. 创建软链接 `/root/.ssh -> /mnt/workspace/.ssh`
3. 更新本记忆文件

---
*此文件应放在 `/mnt/workspace/MEMORY.md` 或项目根目录的 `DEPLOYMENT.md` 中*
