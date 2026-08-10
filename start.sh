#!/bin/bash

# 固件扫描平台启动脚本（WebSocket 增强版）
# 用法：./start.sh

echo "================================================"
echo "🦞 固件漏洞扫描平台 v2.3 (带 WebSocket 实时通知)"
echo "================================================"
echo ""

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 Python3，请先安装"
    exit 1
fi

echo "✅ Python3: $(python3 --version)"

# 检查依赖
echo ""
echo "📦 检查依赖包..."
cd "$(dirname "$0")"

# 安装 Socket.IO 相关依赖（如果缺失）
pip3 install -q python-socketio==5.11.0 fastapi-socketio==0.0.10

# 检查是否已经安装
if pip3 list | grep -q "python-socketio" && pip3 list | grep -q "fastapi-socketio"; then
    echo "✅ Socket.IO 依赖已安装"
else
    echo "⚠️  警告：Socket.IO 依赖安装失败，请手动运行:"
    echo "   pip3 install python-socketio==5.11.0 fastapi-socketio==0.0.10"
    exit 1
fi

# 清理旧进程（可选）
if [ "$1" == "--clean" ]; then
    echo ""
    echo "🧹 清理旧进程..."
    pkill -f "uvicorn.*api.main:app" || true
    sleep 1
fi

# 创建必要目录
mkdir -p logs data uploads workspace reports

# 显示配置信息
echo ""
echo "⚙️  服务器配置:"
grep -E "^host:|^port:" config.yaml | sed 's/^/   /'

echo ""
echo "🔌 端口占用情况:"
netstat -tuln 2>/dev/null | grep ":8000 " || ss -tuln | grep ":8000 " || echo "   端口 8000 未被占用 ✅"

echo ""
echo "🚀 正在启动服务器..."
echo "   - WebSocket 实时通知已启用"
echo "   - Socket.IO 长连接已配置"
echo "   - 自动重连功能已开启"
echo ""

# 启动服务器
cd api
exec uvicorn main:socket_app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
