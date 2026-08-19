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
| Grype DB | `/mnt/workspace/firmware_scanner/db/grype/` | `~/.cache/grype/` | 重启后丢失 |

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

## Grype CLI 配置（v2.5.0+）

### 安装 grype CLI

```bash
# 方式 1: 使用安装脚本（推荐）
bash scripts/setup_grype.sh

# 方式 2: 手动安装
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# 验证安装
grype --version  # 应显示 v0.115+
```

### 配置 Grype DB 路径

```bash
# 创建 Grype DB 目录（持久化）
mkdir -p /mnt/workspace/firmware_scanner/db/grype

# 下载 Grype DB（约 2GB）
grype db update

# 验证 DB 位置
grype db list
```

### 环境变量配置

```bash
# ~/.bashrc 或 ~/.bash_profile
export GRYPE_BIN="/usr/local/bin/grype"
export GRYPE_DB_PATH="/mnt/workspace/firmware_scanner/db/grype/6/vulnerability.db"
```

### config.yaml 配置

```yaml
paths:
  grype_bin: "${GRYPE_BIN:-/usr/local/bin/grype}"
  grype_db: "${GRYPE_DB_PATH:-/mnt/workspace/firmware_scanner/db/grype/6/vulnerability.db}"
```

---

## Docker 部署（生产环境）

```bash
docker run -d \
  --name xuanwu-scanner \
  -p 8000:8000 \
  -v /mnt/workspace/firmware_scanner/data:/app/data \
  -v /mnt/workspace/firmware_scanner/db/grype:/app/db/grype \
  ghcr.io/Jackson8ok/firmware_scanner:latest
```

---

## 检查清单

项目部署后检查：
- [ ] SSH 密钥在 `/mnt/workspace/.ssh/`
- [ ] 所有数据文件在 `/mnt/workspace/` 下
- [ ] 没有硬编码 `/root/`、`/tmp/`、`/home/` 路径
- [ ] 配置文件引用的是 workspace 路径
- [ ] grype CLI 已安装（`grype --version`）
- [ ] Grype DB 已下载（`grype db list`）
- [ ] Grype DB 路径在 workspace 下

## 本次教训

**时间**: 2026-08-17  
**问题**: SSH 密钥生成在 `/root/.ssh/`，实例重启后丢失，导致 `git push` 失败  
**根因**: 默认 `ssh-keygen` 会写到 `/root/.ssh/`，没有指定到 workspace  
**解决**: 
1. 密钥移到 `/mnt/workspace/.ssh/`
2. 创建软链接 `/root/.ssh -> /mnt/workspace/.ssh`
3. 更新本记忆文件

**时间**: 2026-08-19  
**问题**: v2.4.3 字段补全修复未生效  
**根因**: task_queue.py 序列化时未包含 published_date/epss_score 字段  
**解决**: 更新 task_queue.py vulnerabilities 字典，新增字段序列化

---
*此文件应放在 `/mnt/workspace/MEMORY.md` 或项目根目录的 `DEPLOYMENT.md` 中*
