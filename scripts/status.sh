#!/bin/bash
# 固件漏洞扫描平台 - 状态检查脚本

PROJECT_ROOT="$(dirname "$(dirname "$0")")"

echo "========================================="
echo "  🦞 固件漏洞扫描平台状态"
echo "========================================="

# 检查 Python 服务器
echo ""
echo "[1] FastAPI 服务器:"
UVICORN_PID=$(pgrep -f "uvicorn.*8765" || echo "")
if [ ! -z "$UVICORN_PID" ]; then
    echo "  ✅ 运行中 (PID: $UVICORN_PID)"
    echo "  URL: http://localhost:8765"
else
    echo "  ❌ 未运行"
fi

# 检查 Node.js 报告服务
echo ""
echo "[2] Node.js 报告服务:"
NODE_PID=$(pgrep -f "node.*report-service" || echo "")
if [ ! -z "$NODE_PID" ]; then
    echo "  ✅ 运行中 (PID: $NODE_PID)"
    echo "  URL: http://localhost:3000"
else
    echo "  ⚠️  未运行 (Word/PPT 导出不可用)"
fi

# 检查 Grype 数据库
echo ""
echo "[3] Grype 数据库:"
source <(grep "^grype_db" config.yaml | sed 's/.*: *"\(.*\)"/\1/')
DB_PATH="$GRYPE_DB"
if [ -f "$DB_PATH" ]; then
    DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
    echo "  ✅ 找到 ($DB_PATH)"
    echo "     大小：$DB_SIZE"
    
    # 检查数据库完整性
    TABLES=$(sqlite3 "$DB_PATH" ".tables" 2>/dev/null | wc -l)
    if [ "$TABLES" -gt 0 ]; then
        echo "     表数量：$TABLES"
    fi
else
    echo "  ❌ 不存在：$DB_PATH"
    echo "  请更新 config.yaml 配置正确的路径"
fi

# 检查目录
echo ""
echo "[4] 工作目录:"
for dir in uploads workspace reports; do
    if [ -d "$PROJECT_ROOT/$dir" ]; then
        COUNT=$(find "$PROJECT_ROOT/$dir" -type f 2>/dev/null | wc -l)
        echo "  ✅ $dir/ ($COUNT 个文件)"
    else
        echo "  ❌ $dir/ 不存在"
    fi
done

# 检查工具
echo ""
echo "[5] 外部工具:"
for tool in 7z syft objcopy strings node npm python3 pip3; do
    if command -v $tool &> /dev/null; then
        echo "  ✅ $tool 可用"
    else
        echo "  ❌ $tool 未安装"
    fi
done

# 最近的扫描
echo ""
echo "[6] 最近扫描:"
SCAN_COUNT=$(find workspace -name "*.log" -mtime -1 2>/dev/null | wc -l)
if [ "$SCAN_COUNT" -gt 0 ]; then
    echo "  今天执行了 $SCAN_COUNT 次扫描"
else
    echo "  今日无扫描记录"
fi

echo ""
echo "========================================="
