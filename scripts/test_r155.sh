#!/bin/bash
# R155 合规功能演示脚本
# 
# 用法：./test_r155.sh

set -e

echo "========================================="
echo "🔒 R155 合规检查功能测试"
echo "========================================="

# 检查服务器是否运行
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ 服务器未运行，请先启动服务"
    echo "   运行：cd /mnt/workspace/firmware_scanner && ./scripts/startup.sh"
    exit 1
fi

echo "✅ 服务器运行正常"

# 检查 API 端点
echo ""
echo "📡 检查 API 端点..."

# 健康检查
HEALTH=$(curl -s http://localhost:8000/health)
echo "   健康检查：$HEALTH"

# API 文档
echo ""
echo "📖 API 文档地址：http://localhost:8000/docs"
echo ""

# 列出所有扫描任务
echo "📋 当前扫描任务列表..."
TASKS=$(curl -s http://localhost:8000/api/tasks | python3 -m json.tool 2>/dev/null || echo "暂无任务")
echo "$TASKS"
echo ""

# 示例：如果有关闭的任务，显示合规报告
echo "🔍 查找已完成任务的合规报告..."
COMPLETED_TASKS=$(curl -s "http://localhost:8000/api/tasks?limit=10&status=completed")

if [ "$(echo "$COMPLETED_TASKS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")" -gt 0 ]; then
    TASK_ID=$(echo "$COMPLETED_TASKS" | python3 -c "import sys,json; tasks=json.load(sys.stdin); print(tasks[0]['task_id'] if tasks else '')" 2>/dev/null)
    
    if [ -n "$TASK_ID" ]; then
        echo "   找到任务：$TASK_ID"
        echo ""
        echo "📊 合规报告:"
        COMPLIANCE=$(curl -s "http://localhost:8000/api/compliance/$TASK_ID")
        echo "$COMPLIANCE" | python3 -m json.tool
        
        echo ""
        echo "📈 类别得分:"
        CATEGORIES=$(curl -s "http://localhost:8000/api/compliance/categories/$TASK_ID")
        echo "$CATEGORIES" | python3 -m json.tool
    fi
else
    echo "   ⚠️ 暂无已完成的扫描任务"
    echo ""
    echo "💡 提示：上传固件文件进行扫描以查看 R155 合规报告"
fi

echo ""
echo "========================================="
echo "✅ 测试完成！"
echo "========================================="
echo ""
echo "🎯 下一步操作:"
echo "   1. 访问 Web 界面：http://localhost:8000"
echo "   2. 上传固件文件进行扫描"
echo "   3. 扫描完成后查看 R155 合规报告选项卡"
echo ""
