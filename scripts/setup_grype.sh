#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "  Grype 初始化脚本 (v0.117.0)"
echo "========================================"
echo ""

# 1. 检查 Grype 二进制
GRYPE_BIN="${GRYPE_BIN:-$PROJECT_ROOT/tools/grype/grype}"
if [ ! -f "$GRYPE_BIN" ]; then
    echo -e "${YELLOW}[!] Grype 二进制不存在: $GRYPE_BIN${NC}"
    echo "    请先下载 Grype 到 tools/grype/ 目录"
    exit 1
fi
chmod +x "$GRYPE_BIN"
echo -e "${GREEN}[✓] Grype 二进制已就绪: $GRYPE_BIN${NC}"
"$GRYPE_BIN" --version
echo ""

# 2. 设置 Grype DB 路径
GRYPE_DB_PATH="${GRYPE_DB_PATH:-$PROJECT_ROOT/db/grype/6/vulnerability.db}"
GRYPE_DB_DIR="$(dirname "$GRYPE_DB_PATH")"

# 创建目录
mkdir -p "$GRYPE_DB_DIR"
mkdir -p "$PROJECT_ROOT/db/grype"

echo "Grype DB 路径: $GRYPE_DB_PATH"
echo "Grype DB 缓存目录: $PROJECT_ROOT/db/grype"
echo ""

# 3. 下载/更新 Grype DB
if [ -f "$GRYPE_DB_PATH" ]; then
    echo -e "${GREEN}[✓] Grype DB 已存在: $GRYPE_DB_PATH${NC}"
    echo "    如需更新，请删除后重新运行此脚本"
else
    echo -e "${YELLOW}[!] Grype DB 不存在，开始下载...${NC}"
    echo "    这可能需要几分钟（约 2GB）..."
    echo ""
    
    # 使用项目内置的 Grype 下载 DB
    GRYPE_DB_CACHE_DIR="$PROJECT_ROOT/db/grype" \
    GRYPE_DB_PATH="$GRYPE_DB_PATH" \
    "$GRYPE_BIN" db update
    
    if [ ! -f "$GRYPE_DB_PATH" ]; then
        echo -e "${RED}[✗] Grype DB 下载失败${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}[✓] Grype DB 下载完成${NC}"
fi

echo ""
echo "========================================"
echo "  Grype 初始化完成"
echo "========================================"
echo ""
echo "下一步:"
echo "1. 确保 config.yaml 中的路径正确（通常无需修改）"
echo "2. 启动服务: python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "自定义路径（可选）:"
echo "  export GRYPE_BIN=/path/to/grype"
echo "  export GRYPE_DB_PATH=/path/to/grype.db"
