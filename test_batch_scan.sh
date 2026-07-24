#!/bin/bash
# 批量扫描测试脚本

echo "=========================================="
echo "固件漏洞扫描平台 - 批量扫描测试"
echo "=========================================="

# 配置
BASE_URL="http://127.0.0.1:8765"
TEST_DIR="./test_firmware"
REPORT_DIR="./reports"

# 创建测试目录
mkdir -p "$TEST_DIR"
mkdir -p "$REPORT_DIR"

echo ""
echo "📋 步骤 1: 检查服务器状态"
curl -s "$BASE_URL/" > /dev/null && echo "✅ 服务器运行正常" || echo "❌ 服务器未启动"

echo ""
echo "📋 步骤 2: 查看队列状态"
curl -s "$BASE_URL/api/queue/stats" | jq '.'

echo ""
echo "📋 步骤 3: 上传测试固件（示例）"
# 注意：这里需要实际的固件文件
if [ -d "$TEST_DIR" ] && [ "$(ls -A $TEST_DIR)" ]; then
    for file in "$TEST_DIR"/*; do
        if [ -f "$file" ]; then
            echo "正在上传：$(basename "$file")"
            curl -s -X POST \
                -F "file=@$file" \
                "$BASE_URL/api/upload" | jq '.'
        fi
    done
else
    echo "⚠️  测试目录为空，请添加固件文件到 $TEST_DIR"
    echo "   或者创建一些测试文件:"
    echo "   mkdir -p test_firmware"
    echo "   echo 'test firmware data' > test_firmware/sample.bin"
fi

echo ""
echo "📋 步骤 4: 获取任务列表"
curl -s "$BASE_URL/api/tasks?limit=10" | jq '.'

echo ""
echo "📋 步骤 5: 查看最终统计"
curl -s "$BASE_URL/api/queue/stats" | jq '.'

echo ""
echo "=========================================="
echo "✅ 测试完成"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 访问 http://127.0.0.1:8765 查看 Web 界面"
echo "2. 使用批量扫描功能上传多个固件"
echo "3. 监控任务队列状态"
echo ""
