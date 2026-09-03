#!/bin/bash
# install_offline.sh - 离线安装脚本（在无网机器运行）

set -e

echo "=========================================="
echo "🐢 玄武固件扫描器 - 离线安装"
echo "=========================================="
echo ""

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "🐍 Python 版本：$PYTHON_VERSION"

# 检查 Python 版本 >= 3.9
REQUIRED_VERSION="3.9"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "⚠️  警告：Python 版本可能过低（需要 3.9+）"
fi

echo ""

# 1. 创建虚拟环境
echo "📦 步骤 1/6: 创建 Python 虚拟环境..."
if [ -d "venv" ]; then
    echo "  → 虚拟环境已存在，跳过创建"
else
    python3 -m venv venv
    echo "  → 虚拟环境创建完成"
fi

# 激活虚拟环境
echo "  → 激活虚拟环境..."
source venv/bin/activate

# 2. 安装 Python 依赖
echo ""
echo "📦 步骤 2/6: 安装 Python 依赖（离线模式）..."
if [ -d "offline_deps" ] && [ "$(ls -A offline_deps)" ]; then
    echo "  → 从 ./offline_deps 安装..."
    pip install --no-index --find-links=./offline_deps -r requirements.txt --quiet
    echo "  → 依赖安装完成"
else
    echo "❌ 错误：offline_deps 目录不存在或为空"
    echo "   请先在有网机器运行 scripts/prepare_offline_package.sh"
    exit 1
fi

# 3. 验证 Grype 数据库
echo ""
echo "🗄️  步骤 3/6: 验证 Grype 数据库..."
if [ -f "db/grype/6/vulnerability.db" ]; then
    SIZE=$(du -h db/grype/6/vulnerability.db | cut -f1)
    DB_SIZE=$(stat -c%s db/grype/6/vulnerability.db 2>/dev/null || stat -f%z db/grype/6/vulnerability.db 2>/dev/null || echo "0")
    
    if [ "$DB_SIZE" -gt 100000000 ]; then  # > 100MB
        echo "✅ Grype 数据库验证通过 ($SIZE)"
    else
        echo "⚠️  警告：数据库文件可能不完整 ($SIZE)"
    fi
else
    echo "❌ 错误：Grype 数据库不存在"
    echo "   路径：db/grype/6/vulnerability.db"
    echo "   请先在有网机器下载数据库"
    exit 1
fi

# 4. 检查系统工具
echo ""
echo "🔨 步骤 4/6: 检查系统工具..."

# unsquashfs
if command -v unsquashfs &> /dev/null; then
    echo "✅ unsquashfs 已安装 ($(unsquashfs --version 2>&1 | head -1))"
else
    echo "⚠️  unsquashfs 未安装"
    echo "   建议：sudo apt install squashfs-tools"
    echo "   影响：SquashFS 固件将无法解压"
fi

# 7-Zip
if command -v 7z &> /dev/null; then
    echo "✅ 7-Zip 已安装"
else
    echo "⚠️  7-Zip 未安装"
    echo "   建议：sudo apt install p7zip-full"
fi

# Binwalk (可选)
if command -v binwalk &> /dev/null; then
    echo "✅ Binwalk 已安装"
else
    echo "ℹ️  Binwalk 未安装 (可选)"
fi

# Grype 二进制
if [ -f "tools/grype/grype" ]; then
    echo "✅ Grype 二进制已存在"
else
    echo "ℹ️  Grype 二进制未找到 (可选，将使用 Python 实现)"
fi

# 5. 配置检查
echo ""
echo "⚙️  步骤 5/6: 配置检查..."

# 检查 config.yaml
if [ -f "config.yaml" ]; then
    echo "✅ config.yaml 存在"
    
    # 提示用户检查路径配置
    echo "  → 请确保以下配置项使用绝对路径："
    echo "     - paths.grype_db"
    echo "     - paths.work_dir"
    echo "     - paths.upload_dir"
else
    echo "⚠️  config.yaml 不存在，使用默认配置"
fi

# 6. 启动服务
echo ""
echo "🚀 步骤 6/6: 启动服务..."

# 创建日志目录
mkdir -p logs

# 检查服务是否已在运行
if pgrep -f "python.*main.py" > /dev/null; then
    echo "  → 检测到服务已在运行，停止旧进程..."
    pkill -f "python.*main.py" || true
    sleep 2
fi

# 启动服务
echo "  → 启动新服务..."
cd api
nohup python main.py > ../logs/service.log 2>&1 &
SERVICE_PID=$!
echo "  → 服务已启动 (PID: $SERVICE_PID)"

# 等待服务启动
echo "  → 等待服务就绪..."
sleep 5

# 7. 验证服务
echo ""
echo "🧪 验证服务..."

if curl -s http://localhost:8765/api/health > /dev/null 2>&1; then
    echo "✅ 服务健康检查通过"
    
    # 显示健康信息
    curl -s http://localhost:8765/api/health | python3 -m json.tool 2>/dev/null || true
else
    echo "⚠️  服务健康检查失败"
    echo "  → 查看日志：tail -f logs/service.log"
fi

echo ""
echo "=========================================="
echo "✅ 安装完成！"
echo "=========================================="
echo ""
echo "📝 访问 Web UI: http://localhost:8765"
echo "📝 查看日志：tail -f logs/service.log"
echo "📝 停止服务：pkill -f 'python.*main.py'"
echo ""
echo "🔧 常用命令："
echo "  • 重启服务：cd api && pkill -f 'python.*main.py' && python main.py &"
echo "  • 查看状态：curl http://localhost:8765/api/health"
echo "  • 清理缓存：rm -rf api/cache/* workspace/*"
echo ""
echo "=========================================="
echo ""
