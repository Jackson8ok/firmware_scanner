# 🐢 玄武固件扫描器 - 本地部署验证指南

**版本**: v2.4.1  
**更新日期**: 2026-08-18  
**适用系统**: Windows / macOS / Linux

---

## 📋 目录

1. [系统要求](#系统要求)
2. [快速开始（推荐）](#快速开始推荐)
3. [完整安装](#完整安装)
4. [配置说明](#配置说明)
5. [验证测试](#验证测试)
6. [常见问题](#常见问题)
7. [性能基准](#性能基准)

---

## 系统要求

### 最低配置

| 组件 | 要求 |
|-----|------|
| **CPU** | 4 核心 (x86_64) |
| **内存** | 8 GB RAM |
| **磁盘** | 20 GB 可用空间 |
| **系统** | Windows 10 / macOS 11 / Ubuntu 20.04+ |
| **网络** | 需要访问 GitHub 和 PyPI |

### 推荐配置

| 组件 | 要求 |
|-----|------|
| **CPU** | 8 核心+ |
| **内存** | 16 GB RAM |
| **磁盘** | 50 GB SSD |
| **系统** | Ubuntu 22.04 LTS / macOS 13+ |
| **网络** | 稳定宽带连接 |

### 依赖工具

| 工具 | 版本 | 用途 | 安装方式 |
|-----|------|------|---------|
| Python | 3.9+ | 运行环境 | [python.org](https://www.python.org/) |
| Git | 2.30+ | 代码管理 | 系统包管理器 |
| unsquashfs | 4.5+ | SquashFS 解压 | `apt install squashfs-tools` |
| 7-Zip | 16.02+ | 固件解压 | `apt install p7zip-full` |
| Binwalk | 2.1.2 (可选) | 固件分析 | `pip install binwalk` |
| Syft | 1.51.0 (可选) | SBOM 生成 | 见下方 |

---

## 快速开始（推荐）

### 1. 克隆项目

```bash
# Windows (PowerShell) / macOS / Linux
git clone https://github.com/Jackson8ok/firmware_scanner.git
cd firmware_scanner
```

### 2. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt
```

### 3. 下载 Grype 漏洞数据库

```bash
# 自动下载脚本（推荐）
python scripts/download_grype_db.py

# 或手动下载
# 见下方 "手动下载数据库" 章节
```

### 4. 启动服务

```bash
# 进入 API 目录
cd api

# 启动服务
python main.py

# 服务将在 http://localhost:8765 启动
```

### 5. 访问 UI

打开浏览器访问：**http://localhost:8765**

---

## 完整安装

### Windows 10/11

#### 步骤 1: 安装 Python

1. 访问 [python.org](https://www.python.org/downloads/)
2. 下载 Python 3.9+ (勾选 "Add to PATH")
3. 安装完成后验证：
   ```powershell
   python --version
   ```

#### 步骤 2: 安装 Git

1. 访问 [git-scm.com](https://git-scm.com/download/win)
2. 下载安装 Git for Windows
3. 验证：
   ```powershell
   git --version
   ```

#### 步骤 3: 安装 unsquashfs

```powershell
# 使用 Chocolatey (推荐)
choco install squashfs-tools

# 或手动下载
# https://github.com/plougher/squashfs-tools/releases
```

#### 步骤 4: 克隆项目

```powershell
git clone https://github.com/Jackson8ok/firmware_scanner.git
cd firmware_scanner
```

#### 步骤 5: 安装依赖

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### 步骤 6: 下载数据库

```powershell
python scripts/download_grype_db.py
```

#### 步骤 7: 启动服务

```powershell
cd api
python main.py
```

---

### macOS (11+)

#### 步骤 1: 安装 Homebrew (如未安装)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 步骤 2: 安装依赖

```bash
brew install python@3.11 git squashfs p7zip
```

#### 步骤 3: 克隆项目

```bash
git clone https://github.com/Jackson8ok/firmware_scanner.git
cd firmware_scanner
```

#### 步骤 4: 安装 Python 依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 步骤 5: 下载数据库

```bash
python scripts/download_grype_db.py
```

#### 步骤 6: 启动服务

```bash
cd api
python main.py
```

---

### Ubuntu/Debian Linux

#### 步骤 1: 安装系统依赖

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git squashfs-tools p7zip-full wget curl
```

#### 步骤 2: 克隆项目

```bash
git clone https://github.com/Jackson8ok/firmware_scanner.git
cd firmware_scanner
```

#### 步骤 3: 安装 Python 依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 步骤 4: 下载数据库

```bash
python scripts/download_grype_db.py
```

#### 步骤 5: 启动服务

```bash
cd api
python main.py
```

---

## 配置说明

### 配置文件位置

```
firmware_scanner/
├── config.yaml          # 主配置文件
└── api/
    └── config.yaml      # API 配置（可选）
```

### 关键配置项

```yaml
# config.yaml

paths:
  # Grype 二进制路径（自动检测，可手动指定）
  grype_bin: /usr/local/bin/grype
  
  # Grype 数据库路径（重要！）
  grype_db: /mnt/workspace/firmware_scanner/db/grype/6/vulnerability.db
  
  # 工作目录
  work_dir: ./workspace
  
  # 上传目录
  upload_dir: ./api/uploads

server:
  host: 0.0.0.0
  port: 8765
  debug: false  # 生产环境设为 false

scanner:
  # 是否启用 EPSS 评分（需要网络）
  enable_epss: true
  
  # 是否启用 R155 合规检查
  enable_r155: true
  
  # 并发工作线程数
  max_workers: 4
```

### 环境变量（可选）

```bash
# Grype 数据库路径
export GRYPE_DB_PATH=/path/to/vulnerability.db

# Grype 二进制路径
export GRYPE_BIN=/usr/local/bin/grype

# 禁用 EPSS（离线环境）
export DISABLE_EPSS=true
```

---

## 验证测试

### 测试 1: 健康检查

```bash
curl http://localhost:8765/api/health
```

**预期响应**:
```json
{
  "status": "healthy",
  "version": "2.4.1",
  "websocket": "enabled",
  "timestamp": "2026-08-18T..."
}
```

### 测试 2: 上传固件

```bash
# 准备测试固件（可从 OpenWrt 下载）
wget https://downloads.openwrt.org/archive/15.05.1/ar71xx/generic/openwrt-15.05.1-ar71xx-generic-antminer-s1-squashfs-sysupgrade.bin -O test_firmware.bin

# 上传
curl -X POST http://localhost:8765/api/upload \
  -F "file=@test_firmware.bin"
```

**预期响应**:
```json
{
  "success": true,
  "filename": "test_firmware.bin",
  "path": "uploads/test_firmware.bin",
  "size": 8126464
}
```

### 测试 3: 触发扫描

```bash
curl -X POST http://localhost:8765/api/scan \
  -F "firmware_id=test_firmware.bin" \
  -F "firmware_type=auto"
```

**预期响应**:
```json
{
  "success": true,
  "task_id": "uuid-here",
  "message": "扫描任务已提交"
}
```

### 测试 4: 查询进度

```bash
curl http://localhost:8765/api/task/{task_id}/status
```

**预期响应**:
```json
{
  "task_id": "uuid-here",
  "status": "running",
  "progress": 35,
  "progress_details": {
    "stage": "sbom_generation",
    "details": "正在识别组件"
  }
}
```

### 测试 5: 获取结果

```bash
curl http://localhost:8765/api/task/{task_id}/result
```

**预期响应**: 包含组件列表和 CVE 详情

### 测试 6: 使用 Web UI

1. 打开浏览器访问 **http://localhost:8765**
2. 点击 "上传固件"
3. 选择测试固件文件
4. 点击 "开始扫描"
5. 观察进度条和实时日志
6. 查看扫描结果和 CVE 列表

---

## 常见问题

### Q1: Grype 数据库下载失败

**现象**: `scripts/download_grype_db.py` 执行失败

**解决方案**:

```bash
# 方案 1: 使用镜像源
python scripts/download_grype_db.py --mirror

# 方案 2: 手动下载
# 访问 https://tools anchore.io/grype/databases/
# 下载 vulnerability.db.gz
# 解压到 db/grype/6/vulnerability.db

# 方案 3: 离线模式
# 从其他机器复制已下载的数据库
```

### Q2: unsquashfs 未找到

**现象**: `unsquashfs: command not found`

**解决方案**:

```bash
# Ubuntu/Debian
sudo apt install squashfs-tools

# macOS
brew install squashfs

# Windows (Chocolatey)
choco install squashfs-tools

# Windows (手动)
# 下载 https://github.com/plougher/squashfs-tools/releases
# 添加到 PATH
```

### Q3: 端口被占用

**现象**: `Address already in use: port 8765`

**解决方案**:

```bash
# 查找占用端口的进程
# Linux/macOS:
lsof -i :8765
# Windows:
netstat -ano | findstr :8765

# 杀死进程或修改配置
# 修改 config.yaml:
server:
  port: 8766  # 改用其他端口
```

### Q4: 内存不足

**现象**: `MemoryError` 或进程被杀死

**解决方案**:

```bash
# 1. 减少并发线程数
# config.yaml:
scanner:
  max_workers: 2  # 降低为 2

# 2. 增加系统交换空间（Linux）
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 3. 扫描大型固件时使用高性能机器
```

### Q5: 扫描结果为空

**现象**: 组件数为 0，CVE 数为 0

**可能原因**:

1. **Grype DB 未加载**
   ```bash
   # 检查数据库文件
   ls -lh db/grype/6/vulnerability.db
   # 应 > 500MB
   ```

2. **固件类型检测失败**
   ```bash
   # 手动指定类型
   curl -X POST http://localhost:8765/api/scan \
     -F "firmware_id=test.bin" \
     -F "firmware_type=squashfs"
   ```

3. **Syft 未安装（可选）**
   ```bash
   # 安装 Syft 提升 SBOM 质量
   # 见下方 "安装 Syft" 章节
   ```

### Q6: WebSocket 连接失败

**现象**: 前端显示 "WebSocket 连接失败"

**解决方案**:

```bash
# 1. 检查服务是否正常启动
curl http://localhost:8765/api/health

# 2. 检查防火墙设置
# Windows: 允许 Python 通过防火墙
# Linux: sudo ufw allow 8765

# 3. 使用 HTTP 轮询模式（前端自动降级）
```

---

## 安装 Syft（可选但推荐）

Syft 可提升 SBOM 生成质量，特别是对于复杂固件。

### Linux/macOS

```bash
# 自动安装脚本
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin v1.51.0

# 验证
syft --version
```

### Windows

```powershell
# 使用 Scoop
scoop install syft

# 或手动下载
# https://github.com/anchore/syft/releases/download/v1.51.0/syft_1.51.0_windows_amd64.zip
# 解压并添加到 PATH
```

### 配置 Syft 路径

```yaml
# config.yaml
paths:
  syft_bin: /usr/local/bin/syft  # Linux/macOS
  # syft_bin: C:\Program Files\syft.exe  # Windows
```

---

## 安装 Binwalk（可选）

Binwalk 提供更强大的固件分析能力。

```bash
# 注意：Binwalk 安装较复杂，推荐使用 Docker 版本

# Ubuntu/Debian
sudo apt install binwalk

# 或使用 Python
pip install binwalk

# macOS
brew install binwalk
```

---

## 性能基准

### 测试环境

```
CPU: Intel i7-12700K (12 核)
内存：32 GB DDR4
磁盘：1 TB NVMe SSD
系统：Ubuntu 22.04 LTS
```

### 扫描性能

| 固件类型 | 大小 | 耗时 | 组件数 | CVE 数 |
|---------|------|------|-------|-------|
| OpenWrt SquashFS | 6.6 MB | 25 秒 | 100 | 475 |
| OpenWrt 复合固件 | 7.75 MB | 35 秒 | 100 | 475 |
| 典型 IoT 固件 | 16 MB | 60 秒 | 250 | 800+ |
| 大型路由器固件 | 64 MB | 180 秒 | 800 | 2000+ |

### 资源占用

| 阶段 | CPU | 内存 | 磁盘 I/O |
|-----|-----|------|---------|
| 上传 | <5% | 100 MB | 低 |
| 解压 | 30% | 500 MB | 中 |
| SBOM 生成 | 50% | 1 GB | 中 |
| CVE 匹配 | 80% | 2 GB | 高 |
| 空闲 | <2% | 200 MB | 无 |

---

## 离线部署

### 步骤 1: 准备离线包

在有网络的机器上：

```bash
# 1. 下载项目
git clone https://github.com/Jackson8ok/firmware_scanner.git

# 2. 下载 Python 依赖
cd firmware_scanner
pip download -r requirements.txt -d ./offline_deps

# 3. 下载 Grype 数据库
python scripts/download_grype_db.py

# 4. 打包
cd ..
tar -czvf firmware_scanner_offline.tar.gz firmware_scanner/
```

### 步骤 2: 传输到离线机器

```bash
# 使用 U 盘或内部网络传输
scp firmware_scanner_offline.tar.gz user@offline-machine:/path/
```

### 步骤 3: 离线安装

```bash
# 解压
tar -xzvf firmware_scanner_offline.tar.gz
cd firmware_scanner

# 安装依赖（离线）
pip install --no-index --find-links=./offline_deps -r requirements.txt

# 启动服务
cd api
python main.py
```

---

## Docker 部署（推荐用于生产环境）

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git squashfs-tools p7zip-full wget curl \
    && rm -rf /var/lib/apt/lists/*

# 克隆项目
RUN git clone https://github.com/Jackson8ok/firmware_scanner.git .

# 安装 Python 依赖
RUN pip install -r requirements.txt

# 下载 Grype 数据库
RUN python scripts/download_grype_db.py

# 暴露端口
EXPOSE 8765

# 启动服务
CMD ["python", "api/main.py"]
```

### 构建和运行

```bash
# 构建镜像
docker build -t firmware_scanner:latest .

# 运行容器
docker run -d \
  -p 8765:8765 \
  -v firmware_data:/app/api/uploads \
  -v firmware_data:/app/api/cache \
  --name firmware_scanner \
  firmware_scanner:latest

# 查看日志
docker logs -f firmware_scanner

# 停止服务
docker stop firmware_scanner
```

---

## 故障排查

### 日志位置

```
firmware_scanner/
├── logs/
│   ├── service.log      # 主服务日志
│   └── scanner.log      # 扫描引擎日志
└── api/
    └── data/
        └── tasks.db     # 任务数据库
```

### 查看日志

```bash
# 实时查看
tail -f logs/service.log

# 查看错误
grep ERROR logs/service.log

# 查看特定任务
grep "task_id" logs/service.log
```

### 重置环境

```bash
# 清理缓存
rm -rf api/cache/*
rm -rf workspace/*

# 重置数据库
rm api/data/tasks.db

# 重启服务
pkill -f "python.*main.py"
cd api && python main.py
```

---

## 获取帮助

### 文档

- [项目 README](https://github.com/Jackson8ok/firmware_scanner)
- [架构设计文档](./ARCHITECTURE.md)
- [API 文档](./api/README.md)
- [漏洞对比报告](./docs/OpenWrt_Vulnerability_Comparison_Report_2026-08-18.md)

### 联系方式

- **GitHub Issues**: [提交问题](https://github.com/Jackson8ok/firmware_scanner/issues)
- **邮箱**: zhu80k@163.com
- **开发者**: 攻城狮阿信 [Jackson]

### 社区支持

- 加入 Discord/Slack 频道（如有）
- 参与 GitHub Discussions
- 查看已有 Issues 和 FAQ

---

## 下一步

部署成功后，建议：

1. ✅ 运行 [验证测试](#验证测试) 确保一切正常
2. 📊 阅读 [漏洞对比报告](./docs/OpenWrt_Vulnerability_Comparison_Report_2026-08-18.md) 了解检测能力
3. 🔧 尝试扫描自己的固件样本
4. 📝 如有问题，提交 GitHub Issue

**祝你部署顺利！** 🎉

---

*文档版本：v1.0*  
*最后更新：2026-08-18*  
*维护者：攻城狮阿信 [Jackson]*
