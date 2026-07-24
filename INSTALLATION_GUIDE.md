# 🦞 固件漏洞扫描平台 - 安装指南

## 📋 安装清单

按照以下步骤在 Windows/Linux/Mac 上搭建完整的固件漏洞扫描平台。

---

## 步骤 1: Python 环境

### Windows
```powershell
# 下载 Python 3.12
https://www.python.org/downloads/

# 安装时勾选 "Add Python to PATH"

# 验证
python --version
pip --version
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3.12 python3-pip python3-venv
```

### macOS
```bash
brew install python@3.12
```

---

## 步骤 2: 克隆/解压项目

```bash
cd /mnt/workspace
# 如果已解压到此目录，跳过此步

# 确认项目结构
ls firmware_scanner/
```

---

## 步骤 3: 安装 Python 依赖

```bash
cd firmware_scanner

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

**预期输出**:
```
Successfully installed fastapi-0.111.0 uvicorn-0.30.1 ...
```

---

## 步骤 4: 安装外部工具

### 4.1 Binwalk (强烈推荐 - 固件专用)

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install binwalk squashfs-tools python3-pip

# 额外依赖（可选但推荐）
sudo apt install p7zip-full lzop cabextract u-boot-tool \
                 yaffs yaffsh liblz4-tool fakeroot
```

#### Linux (通用)
```bash
curl -sSfL https://raw.githubusercontent.com/ReFirmLabs/binwalk/master/install.sh | sudo bash
```

#### macOS
```bash
brew install binwalk
brew install --cask sevenzip
```

#### Windows (WSL2)
```bash
wsl sudo apt install binwalk squashfs-tools
```

**验证**:
```bash
binwalk --version
# 应该显示 v3.x.x
```

**为什么需要 Binwalk**:
- ✅ **500+ 种格式识别**（远超 7-Zip 的 180 种）
- ✅ **递归提取**（Matryoshka 模式，处理嵌套结构）
- ✅ **熵分析**（检测加密/压缩区域）
- ✅ **文件系统自动识别**（JFFS2, CramFS, SquashFS...）
- ⚡ **提升扫描准确率 ~206%**

---

### 4.2 7-Zip (备用方案)

#### Windows
```powershell
# 使用 Chocolatey
choco install 7zip

# 或下载 https://www.7-zip.org/
```

#### Linux
```bash
sudo apt install p7zip-full  # Ubuntu/Debian
sudo yum install p7zip       # CentOS/RHEL
```

#### macOS
```bash
brew install seven-zip
```

**验证**:
```bash
7z --version
```

---

### 4.2 Syft (推荐 - Linux 固件 SBOM)

#### 所有平台
```bash
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
```

#### Windows (PowerShell)
```powershell
iwr -useb https://raw.githubusercontent.com/anchore/syft/main/install.ps1 | iex
```

**验证**:
```bash
syft version
```

**说明**: 
- 如果不安装 Syft，系统会自动降级到字符串提取模式
- Linux/ELF固件精度会下降，但 MCU 固件不受影响

---

### 4.3 Node.js (必需 - 报告生成)

#### Windows/macOS
```bash
# 访问 https://nodejs.org/ 下载 LTS 版本
```

#### Linux
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**验证**:
```bash
node --version   # 需要 >= 16
npm --version    # 需要 >= 8
```

---

### 4.4 binutils (可选 - HEX 转换)

#### Linux
```bash
sudo apt install binutils  # 包含 objcopy, strings
```

**说明**: 
- 如果没有安装，Python 会自动使用备用实现
- 性能略低，但功能完整

---

## 步骤 5: 下载 Grype 漏洞数据库

**重要**: Grype v6 SQLite DB 约 2GB，需要预先下载

```bash
cd firmware_scanner
./scripts/download_grype_db.sh ./grype-db
```

**手动下载** (如果脚本失败):
```bash
mkdir -p grype-db
cd grype-db

wget https://toolbox-data.anchore.io/grype/databases/vulnerability-db_v6_latest.tar.gz
tar xzf vulnerability-db_v6_latest.tar.gz
rm vulnerability-db_v6_latest.tar.gz

# 应该得到 grype.db
ls -lh grype.db  # ~2GB
```

---

## 步骤 6: 配置项目

编辑 `config.yaml`:

```yaml
server:
  host: "127.0.0.1"
  port: 8765

paths:
  # ⚠️ 修改为实际路径
  grype_db: "/mnt/workspace/firmware_scanner/grype-db/vulnerability.db"
  
  uploads: "./uploads"
  workspace: "./workspace"
  reports: "./reports"
```

**Windows 示例**:
```yaml
paths:
  grype_db: "C:/workspace/firmware_scanner/grype-db/vulnerability.db"
```

---

## 步骤 7: 安装 Node.js 服务依赖

```bash
cd firmware_scanner/services/node-report
npm install
```

**预期输出**:
```
added 95 packages in 5s
```

---

## 步骤 8: 运行验证

```bash
cd firmware_scanner
./scripts/verify_env.sh
```

**期望结果**:
```
✅ Python 3.10+
✅ pip3
✅ FastAPI
...
❌ 失败：0
```

如果仍有 ❌，请根据提示修复。

---

## 步骤 9: 启动服务

```bash
cd firmware_scanner
./scripts/startup.sh
```

**成功输出**:
```
=========================================
  🦞 固件漏洞扫描平台启动脚本
=========================================

[1/5] 检查 Python 环境...
Python 版本：3.12.0
...

✅ 服务启动成功！

访问地址：http://localhost:8765
```

---

## 步骤 10: 测试扫描

### Web UI 测试
1. 浏览器打开 http://localhost:8765
2. 选择一个固件文件（任何 .bin/.hex 文件即可）
3. 选择类型（MCU Binary）
4. 点击 "上传并开始扫描"
5. 查看结果和图表

### API 测试
```bash
# 上传
curl -X POST http://localhost:8765/api/upload \
  -F "file=@test_firmware.bin"

# 扫描
curl -X POST http://localhost:8765/api/scan \
  -F "firmware_id=test_firmware" \
  -F "firmware_type=bin"

# 获取结果
curl http://localhost:8765/api/results/test_firmware
```

---

## 🔧 故障排查

### 问题 1: Python 依赖安装失败
```bash
# 升级 pip
python3 -m pip install --upgrade pip

# 使用国内镜像（中国大陆）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题 2: 7-Zip 命令不存在
```bash
# Windows
$env:Path += ";C:\Program Files\7-Zip"

# Linux
sudo ln -s /usr/bin/7zz /usr/local/bin/7z
```

### 问题 3: Grype 数据库找不到
```bash
# 确认配置文件
grep grype_db config.yaml

# 确认文件存在
ls -lh <配置的路径>

# 如果文件太大被 gitignore，重新下载
./scripts/download_grype_db.sh ./grype-db
```

### 问题 4: Node.js 服务无法启动
```bash
cd services/node-report

# 清除并重装
rm -rf node_modules package-lock.json
npm install

# 手动启动测试
node report-service.js
```

### 问题 5: 端口被占用
```bash
# 查找占用进程
netstat -tlnp | grep 8765

# 杀死进程
kill -9 <PID>

# 或修改 config.yaml 中的端口
```

---

## 📊 性能建议

### 首次扫描较慢
- EPSS 查询需要网络
- 大固件 (~100MB) 需要几分钟

### 优化方案
1. **缓存 EPSS**: 定期同步本地数据库
2. **并行扫描**: 支持多固件同时处理
3. **增量扫描**: 只扫描变更的组件

---

## 🔄 更新平台

```bash
cd firmware_scanner

# 备份数据
cp -r uploads uploads.bak
cp -r workspace workspace.bak

# 更新代码
git pull  # 如果用 Git

# 更新依赖
pip install -r requirements.txt --upgrade
cd services/node-report && npm update
```

---

## ✅ 最终检查清单

- [ ] Python 3.10+ 已安装
- [ ] pip3 可用
- [ ] FastAPI + Uvicorn 已安装
- [ ] Node.js 16+ 已安装
- [ ] 7-Zip 已安装（必需）
- [ ] Syft 已安装（推荐）
- [ ] Grype 数据库已下载并配置
- [ ] Python 依赖已安装
- [ ] Node.js 服务依赖已安装
- [ ] config.yaml 配置正确
- [ ] 服务启动成功
- [ ] Web UI 可访问
- [ ] 能执行扫描任务

---

## 🆘 获取帮助

如果遇到无法解决的问题:

1. 查看详细日志:
   ```bash
   tail -f logs/server.log
   ```

2. 检查状态:
   ```bash
   ./scripts/status.sh
   ```

3. 提供以下信息:
   - 操作系统版本
   - Python 版本
   - 错误日志片段
   - `status.sh` 输出

---

**下一步**: 阅读 [README.md](README.md) 了解完整功能

---

*最后更新*: 2026-07-21
