# 🐢 玄武固件扫描器 - 离线部署指南

**适用环境**: 无外网权限 / 内网隔离 / 仅允许 pip 安装  
**更新日期**: 2026-08-18  
**前置条件**: Python 3.9+, Git (可选)

---

## 📋 部署策略

由于你的环境**无法访问外网**，需要采用**完整离线包**方式部署：

```
┌─────────────────────────────────────────────────────────────┐
│  有网机器（准备离线包）  →  传输（U 盘/内网）  →  无网机器（安装）  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 需要准备的文件清单

### 必须文件

| 文件/目录 | 大小 | 用途 | 获取方式 |
|---------|------|------|---------|
| `firmware_scanner/` (完整项目) | ~50 MB | 源代码 | Git 克隆或下载 ZIP |
| `db/grype/6/vulnerability.db` | ~600 MB | CVE 数据库 | 运行下载脚本 |
| Python 依赖包 (`offline_deps/`) | ~100 MB | pip 离线安装 | `pip download` |
| `tools/grype/grype` (可选) | ~30 MB | Grype 二进制 | 自动下载或手动 |

### 可选文件

| 文件/目录 | 用途 |
|---------|------|
| `tools/syft/syft` | 提升 SBOM 质量 |
| `tools/binwalk/` | 增强固件分析 |
| 测试固件样本 | 验证部署 |

---

## 🖥️ 步骤 1: 在有网机器准备离线包

### 1.1 克隆项目

```bash
# 选择一台可以访问外网的机器
git clone https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner.git
cd firmware_scanner
```

### 1.2 下载 Grype 数据库

```bash
# 自动下载（推荐）
python scripts/download_grype_db.py

# 验证下载成功
ls -lh db/grype/6/vulnerability.db
# 应显示 ~600MB
```

### 1.3 下载 Python 依赖

```bash
# 创建离线依赖目录
mkdir offline_deps

# 下载所有依赖（包括依赖的依赖）
pip download -r requirements.txt -d ./offline_deps

# 验证下载完成
ls offline_deps/ | wc -l
# 应显示 50+ 个.whl 文件
```

### 1.4 下载 Grype 二进制（可选但推荐）

```bash
# Linux
python scripts/download_grype.py

# 或手动下载
# https://github.com/anchore/grype/releases/download/v0.117.0/grype_0.117.0_linux_amd64.tar.gz
```

### 1.5 打包离线包

```bash
cd ..

# 创建完整离线包
tar -czvf firmware_scanner_offline_complete.tar.gz firmware_scanner/

# 或仅打包必要文件（更小）
cd firmware_scanner
tar -czvf ../firmware_scanner_offline_minimal.tar.gz \
  api/ \
  scanner/ \
  config.yaml \
  requirements.txt \
  db/grype/6/vulnerability.db \
  scripts/ \
  offline_deps/
```

### 1.6 传输到无网机器

```bash
# 方式 1: U 盘拷贝
cp firmware_scanner_offline_*.tar.gz /media/usb/

# 方式 2: 内网 SCP
scp firmware_scanner_offline_*.tar.gz user@target-machine:/path/to/destination/

# 方式 3: 内部文件共享
# 上传到内部文件服务器，从目标机器下载
```

---

## 🖥️ 步骤 2: 在无网机器安装

### 2.1 解压离线包

```bash
# 解压
tar -xzvf firmware_scanner_offline_complete.tar.gz
cd firmware_scanner
```

### 2.2 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

### 2.3 离线安装 Python 依赖

```bash
# 从本地目录安装（不访问 PyPI）
pip install --no-index --find-links=./offline_deps -r requirements.txt

# 验证安装
pip list | grep -E "fastapi|uvicorn|grype"
```

### 2.4 验证数据库

```bash
# 检查 Grype 数据库
ls -lh db/grype/6/vulnerability.db
# 应显示 ~600MB

# 如果数据库不在预期位置，修改配置
# 编辑 config.yaml:
# paths:
#   grype_db: /absolute/path/to/firmware_scanner/db/grype/6/vulnerability.db
```

### 2.5 安装系统工具（需要 root 权限）

```bash
# unsquashfs (必需)
sudo apt install squashfs-tools  # Ubuntu/Debian
sudo yum install squashfs-tools  # CentOS/RHEL

# 7-Zip (可选但推荐)
sudo apt install p7zip-full

# Binwalk (可选)
sudo apt install binwalk
```

**如果无法安装系统工具**：
- 只能扫描 ELF/简单固件
- SquashFS 固件会跳过解压步骤
- 建议联系管理员提前安装

### 2.6 启动服务

```bash
cd api

# 启动服务
python main.py

# 验证启动成功
# 应看到：
# INFO:     Uvicorn running on http://0.0.0.0:8765
# INFO:     应用启动完成
```

### 2.7 验证部署

```bash
# 健康检查
curl http://localhost:8765/api/health

# 预期响应：
# {"status":"healthy","version":"2.4.1",...}
```

---

## 🔧 配置调整（离线环境）

### 修改 config.yaml

```yaml
# config.yaml

paths:
  # 使用绝对路径（避免相对路径问题）
  grype_db: /absolute/path/to/firmware_scanner/db/grype/6/vulnerability.db
  grype_bin: /absolute/path/to/firmware_scanner/tools/grype/grype
  work_dir: /absolute/path/to/firmware_scanner/workspace
  upload_dir: /absolute/path/to/firmware_scanner/api/uploads

server:
  host: 0.0.0.0
  port: 8765
  debug: false  # 生产环境设为 false

scanner:
  # 离线环境禁用 EPSS（需要网络）
  enable_epss: false
  
  # 启用 R155 合规检查（本地计算，不需要网络）
  enable_r155: true
  
  # 并发工作线程数（根据机器性能调整）
  max_workers: 2
```

### 环境变量（可选）

```bash
# 设置 Grype 数据库路径
export GRYPE_DB_PATH=/absolute/path/to/vulnerability.db

# 禁用 EPSS
export DISABLE_EPSS=true

# 设置 Grype 二进制路径
export GRYPE_BIN=/absolute/path/to/grype
```

---

## 🧪 离线验证测试

### 测试 1: 健康检查

```bash
curl http://localhost:8765/api/health
```

**预期**:
```json
{
  "status": "healthy",
  "version": "2.4.1",
  "grype_db": "loaded",
  "epss": "disabled"
}
```

### 测试 2: 上传测试固件

```bash
# 准备一个小固件文件（可以从官网下载后传输）
# 例如：https://downloads.openwrt.org/.../openwrt-*.bin

curl -X POST http://localhost:8765/api/upload \
  -F "file=@test_firmware.bin"
```

### 测试 3: 扫描测试

```bash
curl -X POST http://localhost:8765/api/scan \
  -F "firmware_id=test_firmware.bin" \
  -F "firmware_type=auto"
```

### 测试 4: 查询结果

```bash
# 获取任务 ID 后
curl http://localhost:8765/api/task/{task_id}/result
```

**预期**: 包含组件列表和 CVE 详情

---

## ⚠️ 离线环境注意事项

### 1. Grype 数据库更新

Grype DB 会定期更新（通常每周），离线环境需要：

```bash
# 定期（如每月）在有网机器更新数据库
cd firmware_scanner
python scripts/download_grype_db.py

# 重新打包传输
tar -czvf firmware_scanner_db_update_$(date +%Y%m%d).tar.gz db/grype/

# 在无网机器替换
mv db/grype/6/vulnerability.db db/grype/6/vulnerability.db.bak
tar -xzf firmware_scanner_db_update_*.tar.gz -C /path/to/firmware_scanner/

# 重启服务
pkill -f "python.*main.py"
cd api && python main.py &
```

### 2. EPSS 数据

EPSS 评分需要网络下载，离线环境建议：

```yaml
# config.yaml
scanner:
  enable_epss: false  # 禁用 EPSS
```

**影响**: CVE 优先级计算仅使用 CVSS 分数，不影响漏洞检测本身

### 3. 日志轮转

离线环境无法上传日志，建议配置日志轮转：

```bash
# 创建日志轮转脚本
cat > /etc/logrotate.d/firmware_scanner << 'EOF'
/mnt/workspace/firmware_scanner/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

### 4. 磁盘空间监控

```bash
# 定期检查磁盘使用
df -h /mnt/workspace

# 清理旧任务缓存（保留最近 7 天）
find /path/to/firmware_scanner/api/cache -type d -mtime +7 -exec rm -rf {} \;
```

---

## 🐳 Docker 离线部署（推荐用于生产）

### 在有网机器构建镜像

```bash
# 克隆项目
git clone https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner.git
cd firmware_scanner

# 构建 Docker 镜像
docker build -t firmware_scanner:offline .

# 导出镜像
docker save -o firmware_scanner_offline.tar firmware_scanner:offline

# 传输到无网机器
scp firmware_scanner_offline.tar user@target-machine:/path/
```

### 在无网机器导入运行

```bash
# 导入镜像
docker load -i firmware_scanner_offline.tar

# 运行容器
docker run -d \
  -p 8765:8765 \
  -v /path/to/data:/app/api/uploads \
  -v /path/to/data:/app/api/cache \
  --name firmware_scanner \
  firmware_scanner:offline

# 验证
docker ps | grep firmware_scanner
docker logs firmware_scanner
```

---

## 📊 离线包大小参考

| 组件 | 大小 | 是否必需 |
|-----|------|---------|
| 源代码 | ~50 MB | ✅ 必需 |
| Grype DB | ~600 MB | ✅ 必需 |
| Python 依赖 | ~100 MB | ✅ 必需 |
| Grype 二进制 | ~30 MB | ⚠️ 推荐 |
| Syft 二进制 | ~30 MB | ❌ 可选 |
| Binwalk | ~5 MB | ❌ 可选 |
| **完整包总计** | **~815 MB** | |
| **最小包总计** | **~750 MB** | |

---

## 🔍 故障排查

### 问题 1: 数据库加载失败

```bash
# 检查数据库文件
ls -lh db/grype/6/vulnerability.db

# 检查配置路径
cat config.yaml | grep grype_db

# 使用绝对路径
export GRYPE_DB_PATH=/absolute/path/to/vulnerability.db
```

### 问题 2: unsquashfs 缺失

```bash
# 检查是否安装
which unsquashfs

# 如果缺失，扫描 SquashFS 固件会降级
# 日志会显示：Unsquashfs 不可用，跳过
```

### 问题 3: pip 安装失败

```bash
# 确保使用离线模式
pip install --no-index --find-links=./offline_deps -r requirements.txt

# 检查离线依赖目录
ls offline_deps/ | head -10
```

### 问题 4: 服务启动失败

```bash
# 查看详细日志
cd api && python main.py 2>&1 | tee startup.log

# 检查端口占用
netstat -tlnp | grep 8765

# 检查 Python 版本
python --version  # 应 >= 3.9
```

---

## 📎 附录：一键打包脚本

### 在有网机器运行

```bash
#!/bin/bash
# prepare_offline_package.sh

set -e

echo "🔧 准备离线部署包..."

# 1. 克隆/更新项目
if [ -d firmware_scanner ]; then
    cd firmware_scanner && git pull
else
    git clone https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner.git
    cd firmware_scanner
fi

# 2. 下载 Grype 数据库
echo "📥 下载 Grype 数据库..."
python scripts/download_grype_db.py

# 3. 下载 Python 依赖
echo "📦 下载 Python 依赖..."
mkdir -p offline_deps
pip download -r requirements.txt -d ./offline_deps

# 4. 下载 Grype 二进制
echo "🔨 下载 Grype 二进制..."
python scripts/download_grype.py 2>/dev/null || echo "Grype 下载失败，继续..."

# 5. 打包
cd ..
echo "📦 打包离线包..."
PACKAGE_NAME="firmware_scanner_offline_$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czvf $PACKAGE_NAME firmware_scanner/

echo "✅ 离线包准备完成：$PACKAGE_NAME"
echo "📊 大小：$(du -h $PACKAGE_NAME | cut -f1)"
echo ""
echo "📝 下一步："
echo "  1. 将 $PACKAGE_NAME 传输到无网机器"
echo "  2. 解压：tar -xzvf $PACKAGE_NAME"
echo "  3. 安装：cd firmware_scanner && bash install_offline.sh"
```

### 在无网机器运行

```bash
#!/bin/bash
# install_offline.sh

set -e

echo "🔧 开始离线安装..."

# 1. 创建虚拟环境
echo "🐍 创建 Python 虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 2. 安装依赖
echo "📦 安装 Python 依赖..."
pip install --no-index --find-links=./offline_deps -r requirements.txt

# 3. 验证数据库
echo "🗄️ 验证 Grype 数据库..."
if [ -f "db/grype/6/vulnerability.db" ]; then
    SIZE=$(du -h db/grype/6/vulnerability.db | cut -f1)
    echo "✅ Grype 数据库存在 ($SIZE)"
else
    echo "❌ Grype 数据库缺失！"
    exit 1
fi

# 4. 检查系统工具
echo "🔨 检查系统工具..."
which unsquashfs >/dev/null && echo "✅ unsquashfs 已安装" || echo "⚠️ unsquashfs 未安装"
which 7z >/dev/null && echo "✅ 7-Zip 已安装" || echo "⚠️ 7-Zip 未安装"

# 5. 启动服务
echo "🚀 启动服务..."
cd api
nohup python main.py > ../logs/service.log 2>&1 &
echo "✅ 服务已启动 (PID: $!)"

# 6. 验证
sleep 5
echo "🧪 验证服务..."
curl -s http://localhost:8765/api/health | python3 -m json.tool || echo "⚠️ 服务验证失败"

echo ""
echo "✅ 安装完成！"
echo "📝 访问 UI: http://localhost:8765"
echo "📝 查看日志：tail -f ../logs/service.log"
```

---

## 📞 获取帮助

如遇到部署问题：

1. **查看日志**: `logs/service.log`
2. **检查配置**: `config.yaml`
3. **验证数据库**: `ls -lh db/grype/6/vulnerability.db`
4. **联系支持**: zhu80k@163.com

---

*文档版本：v1.0*  
*最后更新：2026-08-18*  
*维护者：攻城狮阿信 [Jackson]*
