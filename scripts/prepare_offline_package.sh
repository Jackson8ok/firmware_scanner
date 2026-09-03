#!/bin/bash
# prepare_offline_package.sh - 准备离线部署包（在有网机器运行）

set -e

echo "=========================================="
echo "🐢 玄武固件扫描器 - 准备离线部署包"
echo "=========================================="
echo ""

# 1. 克隆/更新项目
echo "📥 步骤 1/5: 获取项目代码..."
if [ -d firmware_scanner ]; then
    echo "  → 检测到现有目录，执行 git pull..."
    cd firmware_scanner && git pull && cd ..
else
    echo "  → 克隆项目..."
    git clone https://github.com/Jackson8ok/firmware_scanner.git
fi

cd firmware_scanner

# 2. 下载 Grype 数据库
echo ""
echo "📥 步骤 2/5: 下载 Grype 漏洞数据库..."
if [ -f "db/grype/6/vulnerability.db" ]; then
    SIZE=$(du -h db/grype/6/vulnerability.db | cut -f1)
    echo "  → 数据库已存在 ($SIZE)，跳过下载"
else
    echo "  → 开始下载（约 600MB，需 5-15 分钟）..."
    python3 scripts/download_grype_db.py
    SIZE=$(du -h db/grype/6/vulnerability.db | cut -f1)
    echo "  → 下载完成 ($SIZE)"
fi

# 3. 下载 Python 依赖
echo ""
echo "📦 步骤 3/5: 下载 Python 依赖包..."
if [ -d "offline_deps" ] && [ "$(ls -A offline_deps)" ]; then
    COUNT=$(ls offline_deps | wc -l)
    echo "  → 检测到现有依赖包 ($COUNT 个文件)，跳过下载"
else
    echo "  → 创建离线依赖目录..."
    mkdir -p offline_deps
    echo "  → 下载依赖（约 100MB，需 2-5 分钟）..."
    python3 -m pip download -r requirements.txt -d ./offline_deps
    COUNT=$(ls offline_deps | wc -l)
    echo "  → 下载完成 ($COUNT 个文件)"
fi

# 4. 下载 Grype 二进制
echo ""
echo "🔨 步骤 4/5: 下载 Grype 二进制..."
if [ -f "tools/grype/grype" ]; then
    echo "  → Grype 已存在，跳过下载"
else
    echo "  → 尝试自动下载..."
    python3 scripts/download_grype.py 2>/dev/null && echo "  → 下载成功" || echo "  → 自动下载失败，可手动下载"
fi

# 5. 打包
echo ""
echo "📦 步骤 5/5: 打包离线包..."
cd ..

PACKAGE_NAME="firmware_scanner_offline_$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czvf $PACKAGE_NAME firmware_scanner/ --exclude='firmware_scanner/.git' --exclude='firmware_scanner/__pycache__' --exclude='firmware_scanner/*.log'

PACKAGE_SIZE=$(du -h $PACKAGE_NAME | cut -f1)
echo "  → 打包完成：$PACKAGE_NAME ($PACKAGE_SIZE)"

echo ""
echo "=========================================="
echo "✅ 离线包准备完成！"
echo "=========================================="
echo ""
echo "📦 离线包：$PACKAGE_NAME"
echo "📊 总大小：$PACKAGE_SIZE"
echo ""
echo "📝 下一步操作："
echo "  1. 将 $PACKAGE_NAME 传输到无网机器"
echo "     方式：U 盘拷贝 / SCP / 内网文件共享"
echo ""
echo "  2. 在无网机器上解压："
echo "     tar -xzvf $PACKAGE_NAME"
echo ""
echo "  3. 进入目录并运行安装脚本："
echo "     cd firmware_scanner"
echo "     bash install_offline.sh"
echo ""
echo "  4. 访问 Web UI："
echo "     http://localhost:8765"
echo ""
echo "=========================================="
echo ""

# 显示文件清单
echo "📋 离线包内容清单："
tar -tzf $PACKAGE_NAME | grep -E "^(firmware_scanner/db/|firmware_scanner/offline_deps/|firmware_scanner/api/|firmware_scanner/scanner/)" | head -20
echo "  ... (更多文件)"
echo ""
