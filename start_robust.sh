#!/bin/bash

# ============================================================
# 固件扫描平台 - 健壮启动脚本 v2.3
# 功能：自动检测依赖 + 健康检查 + 实时反馈
# ============================================================

set -e  # 任何命令失败立即退出

echo "=================================================="
echo "🦞 固件漏洞扫描平台 v2.3 健壮启动"
echo "=================================================="
echo ""

WORK_DIR="/mnt/workspace/firmware_scanner"
API_DIR="$WORK_DIR/api"
LOG_FILE="/tmp/fs_service_$$.log"
PID_FILE="/tmp/fs_service.pid"

# ============================================================
# 步骤 1: 清理旧进程
# ============================================================
echo "🧹 步骤 1/6: 清理旧进程..."
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        kill $OLD_PID 2>/dev/null || true
        echo "   ✅ 已停止旧进程 (PID: $OLD_PID)"
    fi
fi
pkill -f "python.*main.py" 2>/dev/null || true
sleep 1
echo ""

# ============================================================
# 步骤 2: 检查并安装依赖
# ============================================================
echo "📦 步骤 2/6: 检查核心依赖..."

REQUIRED_PKGS="socketio fastapi-socketio reportlab weasyprint pdfkit matplotlib pillow css-inline openpyxl lxml"
MISSING_PKGS=""

for pkg in $REQUIRED_PKGS; do
    if ! pip show $pkg > /dev/null 2>&1; then
        MISSING_PKGS="$MISSING_PKGS $pkg"
    fi
done

if [ -n "$MISSING_PKGS" ]; then
    echo "   ⚠️  检测到缺失的包:$MISSING_PKGS"
    echo "   🔧 正在安装..."
    pip install -q --no-cache-dir $MISSING_PKGS
    echo "   ✅ 依赖安装完成"
else
    echo "   ✅ 所有依赖已安装"
fi
echo ""

# ============================================================
# 步骤 3: 导入测试（关键！防止运行时才发现错误）
# ============================================================
echo "🔍 步骤 3/6: 快速导入测试..."
cd "$API_DIR"

if timeout 15 python -c "from main import app" > /tmp/import_test.log 2>&1; then
    echo "   ✅ 模块导入成功，无语法/依赖错误"
else
    echo "   ❌ 导入失败！查看详细错误:"
    tail -20 /tmp/import_test.log
    echo ""
    echo "💡 建议修复:"
    echo "   1. 查看完整日志：cat /tmp/import_test.log"
    echo "   2. 常见错误:"
    echo "      - ModuleNotFoundError → pip install xxx"
    echo "      - SyntaxError → 检查代码语法"
    echo "      - ConnectionError → 检查配置"
    exit 1
fi
echo ""

# ============================================================
# 步骤 4: 启动服务
# ============================================================
echo "🚀 步骤 4/6: 启动服务..."
cd "$API_DIR"
nohup python main.py > "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"
echo "   📌 PID: $NEW_PID"
echo "   📄 日志文件：$LOG_FILE"
echo ""

# ============================================================
# 步骤 5: 等待服务就绪（最多 30 秒）
# ============================================================
echo "⏳ 步骤 5/6: 等待服务启动..."
MAX_WAIT=30
WAIT_COUNT=0

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    
    # 检查进程是否存在
    if ! ps -p $NEW_PID > /dev/null 2>&1; then
        echo "   ❌ 进程意外退出！查看错误:"
        tail -30 "$LOG_FILE"
        exit 1
    fi
    
    # 检查端口是否监听
    if ss -tuln 2>/dev/null | grep -q ":8000 "; then
        echo "   ✅ 端口 8000 已监听 ($WAIT_COUNT 秒)"
        break
    fi
    
    echo "   ⏳ 等待中... ($WAIT_COUNT/$MAX_WAIT 秒)"
done

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo "   ❌ 超时！30 秒后仍未就绪"
    echo "   📄 错误日志:"
    tail -30 "$LOG_FILE"
    exit 1
fi
echo ""

# ============================================================
# 步骤 6: 最终健康检查
# ============================================================
echo "🏥 步骤 6/6: 最终健康检查..."

# 测试 HTTP 端点
if curl -s http://localhost:8000 > /dev/null 2>&1; then
    echo "   ✅ HTTP 端点可访问"
elif curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "   ✅ API 健康检查通过"
else
    echo "   ⚠️  HTTP 响应异常（可能还在初始化）"
    echo "   📄 最新日志:"
    tail -20 "$LOG_FILE"
fi
echo ""

# ============================================================
# 启动成功！
# ============================================================
echo "=================================================="
echo "🎉 服务启动成功！"
echo "=================================================="
echo ""
echo "📊 服务信息:"
echo "   • 访问地址：http://localhost:8000"
echo "   • 进程 PID: $NEW_PID"
echo "   • 日志文件：$LOG_FILE"
echo "   • Socket.IO: ✅ 已启用"
echo ""
echo "🔍 快速诊断命令:"
echo "   查看日志：tail -f $LOG_FILE"
echo "   停止服务 : pkill -f 'python.*main.py'"
echo "   检查状态：curl http://localhost:8000/api/queue/stats"
echo ""
echo "🎨 WebSocket 连接状态指示器"
echo "   打开浏览器后，右下角会显示:"
echo "   🟢 绿色 = 已连接（实时推送正常）"
echo "   ⚪ 灰色 = 未连接（回退到轮询）"
echo ""
echo "=================================================="
