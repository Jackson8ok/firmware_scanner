#!/bin/bash
# 玄武固件扫描器 v2.4.3 冒烟测试脚本
# 目的：在打包发布前快速验证服务可正常启动和基本功能

set -e

echo "=== 玄武固件扫描器 v2.4.3 冒烟测试 ==="
echo "开始时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

FAILED=0

# 测试函数
test_check() {
    local name="$1"
    local cmd="$2"
    
    echo -n "检查 $name ... "
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 通过${NC}"
    else
        echo -e "${RED}❌ 失败${NC}"
        FAILED=$((FAILED + 1))
    fi
}

# 1. 导入测试
echo "=== 1. 导入测试 ==="
test_check "api.main 模块导入" "python -c 'import api.main'"

# 2. 配置测试
echo ""
echo "=== 2. 配置测试 ==="
test_check "config.yaml 存在" "test -f config.yaml"

# 检查 Grype DB（处理环境变量格式）
GRYPE_DB_PATH=$(grep -oP 'grype_db:.*?/vulnerability\.db' config.yaml | head -1 | sed 's/.*:-//' | tr -d ' ')
if [ -n "$GRYPE_DB_PATH" ] && [ -f "$GRYPE_DB_PATH" ]; then
    echo -e "检查 Grype DB 存在 ... ${GREEN}✅ 通过${NC}"
else
    echo -e "检查 Grype DB 存在 ... ${RED}❌ 失败${NC}"
    FAILED=$((FAILED + 1))
fi

# 3. 启动测试
echo ""
echo "=== 3. 启动测试 ==="
echo "启动 uvicorn 服务（后台运行）..."
cd "$(dirname "$0")/.."

# 清理旧进程
pkill -f "uvicorn api.main:app" 2>/dev/null || true
sleep 1

# 启动服务
uvicorn api.main:app --host 127.0.0.1 --port 8765 --log-level warning > /tmp/xuanwu_smoke_test.log 2>&1 &
UVICORN_PID=$!

# 等待启动
echo "等待服务启动（3秒）..."
sleep 3

# 检查进程是否存活
if ! kill -0 $UVICORN_PID 2>/dev/null; then
    echo -e "${RED}❌ 服务启动失败${NC}"
    echo "日志输出："
    cat /tmp/xuanwu_smoke_test.log 2>/dev/null || true
    FAILED=$((FAILED + 1))
else
    echo -e "${GREEN}✅ 服务进程存活${NC}"
    
    # 4. 健康检查
    echo ""
    echo "=== 4. 健康检查 ==="
    
    HEALTH=$(curl -s http://127.0.0.1:8765/api/health 2>/dev/null || echo "FAIL")
    
    if echo "$HEALTH" | grep -q '"status":"healthy"'; then
        echo -e "${GREEN}✅ 健康检查通过${NC}"
        echo "   响应：$HEALTH"
    else
        echo -e "${RED}❌ 健康检查失败${NC}"
        echo "   响应：$HEALTH"
        FAILED=$((FAILED + 1))
    fi
    
    # 5. 版本检查
    echo ""
    echo "=== 5. 版本检查 ==="
    
    VERSION=$(echo "$HEALTH" | grep -oP '"version":\s*"\K[^"]+' || echo "UNKNOWN")
    if [ "$VERSION" = "2.4.3" ]; then
        echo -e "${GREEN}✅ 版本标识正确：$VERSION${NC}"
    else
        echo -e "${RED}❌ 版本标识错误：期望 2.4.3，实际 $VERSION${NC}"
        FAILED=$((FAILED + 1))
    fi
    
    # 6. WebSocket 检查
    echo ""
    echo "=== 6. WebSocket 检查 ==="
    
    if grep -q "WebSocket" /tmp/xuanwu_smoke_test.log 2>/dev/null; then
        echo -e "${GREEN}✅ WebSocket 已启用${NC}"
    else
        echo -e "${RED}❌ WebSocket 未启用${NC}"
        FAILED=$((FAILED + 1))
    fi
    
    # 清理
    echo ""
    echo "=== 清理 ==="
    kill $UVICORN_PID 2>/dev/null || true
    wait $UVICORN_PID 2>/dev/null || true
    echo -e "${GREEN}✅ 服务已停止${NC}"
fi

# 总结
echo ""
echo "=== 测试总结 ==="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 冒烟测试全部通过！${NC}"
    exit 0
else
    echo -e "${RED}❌ 冒烟测试失败：$FAILED 项未通过${NC}"
    echo ""
    echo "详细日志："
    cat /tmp/xuanwu_smoke_test.log 2>/dev/null || echo "（无日志）"
    exit 1
fi
