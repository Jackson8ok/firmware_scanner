#!/bin/bash
# 固件漏洞扫描平台 - 快速测试脚本

set +e  # 不立即退出

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "========================================="
echo "  🐢 固件漏洞扫描平台 - 测试套件"
echo "========================================="
echo ""

# 1. 环境验证
echo "[1/4] 环境检查..."
./scripts/verify_env.sh | grep -E "✅|❌|总结" || true

# 2. 运行 Python 单元测试
echo ""
echo "[2/4] 运行单元测试..."
echo "----------------------------------------"
python3 tests/test_firmware_scanner.py
TEST_RESULT=$?

# 3. 如果 Grype DB 可用，尝试真实扫描
echo ""
echo "[3/4] 检查 Grype 数据库..."
GRYPE_DB=$(grep "grype_db:" config.yaml | sed 's/.*: *"\(.*\)"/\1/')
if [ -f "$GRYPE_DB" ]; then
    echo "✅ Grype 数据库找到：$GRYPE_DB"
    
    # 简单查询测试
    TABLES=$(sqlite3 "$GRYPE_DB" ".tables" 2>/dev/null | wc -l)
    if [ "$TABLES" -gt 0 ]; then
        echo "   ✓ 包含 $TABLES 个表"
        
        CVE_COUNT=$(sqlite3 "$GRYPE_DB" "SELECT COUNT(*) FROM vulnerability;" 2>/dev/null)
        echo "   ✓ 漏洞数量：${CVE_COUNT:-'未知'}"
    fi
else
    echo "⚠️  Grype 数据库未配置或不存 (跳过真实扫描测试)"
    echo "   运行：./scripts/download_grype_db.sh ./grype-db"
fi

# 4. Web API 测试（如果服务正在运行）
echo ""
echo "[4/4] Web API 健康检查..."
if curl -s http://localhost:8765/ > /dev/null 2>&1; then
    echo "✅ Web UI 可访问"
    
    HEALTH=$(curl -s http://localhost:8765/api/scans 2>/dev/null)
    if [ ! -z "$HEALTH" ]; then
        echo "✅ API 响应正常"
    fi
else
    echo "⚠️  Web 服务未运行（先运行 ./scripts/startup.sh）"
fi

# 总结
echo ""
echo "========================================="
echo "  测试总结"
echo "========================================="

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ 核心功能测试通过"
else
    echo "⚠️  部分测试失败，请查看上方错误"
fi

echo ""
echo "下一步:"
echo "  1. 安装缺失工具：sudo apt install binwalk squashfs-tools"
echo "  2. 下载 Grype DB: ./scripts/download_grype_db.sh ./grype-db"
echo "  3. 启动服务：./scripts/startup.sh"
echo "  4. 浏览器访问：http://localhost:8765"
echo ""
echo "========================================="

exit $TEST_RESULT
