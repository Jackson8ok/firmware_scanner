#!/bin/bash
# 环境验证脚本 - 检查所有前置条件

set +e  # 不立即退出

echo "========================================="
echo "  🦞 固件漏洞扫描平台 - 环境验证"
echo "========================================="

PROJECT_ROOT="$(dirname "$(dirname "$0")")"
cd "$PROJECT_ROOT"

PASS=0
FAIL=0
WARN=0

check() {
    local name="$1"
    local cmd="$2"
    
    if eval "$cmd" > /dev/null 2>&1; then
        echo "✅ $name"
        ((PASS++))
        return 0
    else
        echo "❌ $name"
        ((FAIL++))
        return 1
    fi
}

warn() {
    local name="$1"
    local msg="$2"
    echo "⚠️  $name: $msg"
    ((WARN++))
}

echo ""
echo "[1] Python 环境"
echo "---------------"
check "Python 3.10+" "python3 --version"
check "pip3" "pip3 --version"
check "FastAPI" "python3 -c 'import fastapi'"
check "Uvicorn" "python3 -c 'import uvicorn'"
check "Jinja2" "python3 -c 'import jinja2'"
check "openpyxl" "python3 -c 'import openpyxl'"

echo ""
echo "[2] Node.js 环境 (用于报告生成)"
echo "-------------------------------"
check "Node.js 16+" "node --version"
check "npm" "npm --version"

echo ""
echo "[3] 外部工具 (可选但推荐)"
echo "-------------------------"
check "7-Zip (SquashFS 解包)" "command -v 7z"
check "Syft (SBOM 生成)" "command -v syft"
check "objcopy (HEX 转换)" "command -v objcopy"
check "strings (字符串提取)" "command -v strings"

echo ""
echo "[4] 项目配置"
echo "------------"
check "config.yaml 存在" "test -f config.yaml"

# 检查 Grype 数据库路径
if [ -f config.yaml ]; then
    GRYPE_DB=$(grep "grype_db:" config.yaml | sed 's/.*: *"\(.*\)"/\1/')
    if [ -n "$GRYPE_DB" ] && [ -f "$GRYPE_DB" ]; then
        echo "✅ Grype 数据库找到 ($GRYPE_DB)"
        ((PASS++))
        
        # 检查数据库内容
        TABLE_COUNT=$(sqlite3 "$GRYPE_DB" ".tables" 2>/dev/null | wc -l)
        if [ "$TABLE_COUNT" -gt 0 ]; then
            echo "   └─ 包含 $TABLE_COUNT 个表"
        fi
    else
        warn "Grype 数据库" "未找到或未配置 ($GRYPE_DB)"
    fi
fi

echo ""
echo "[5] 工作目录"
echo "------------"
for dir in uploads workspace reports logs; do
    check "$dir/" "test -d $dir"
done

echo ""
echo "[6] Python 依赖"
echo "--------------"
if [ -f requirements.txt ]; then
    MISSING=0
    while IFS='=' read -r pkg _; do
        pkg=$(echo "$pkg" | cut -d'[' -f1)  # 移除版本号
        pkg=$(echo "$pkg" | tr '-' '_')     # 规范化
        if python3 -c "import $pkg" 2>/dev/null; then
            :
        else
            # 尝试别名
            if ! python3 -c "import ${pkg//-/_}" 2>/dev/null; then
                ((MISSING++))
            fi
        fi
    done < requirements.txt
    
    if [ $MISSING -eq 0 ]; then
        echo "✅ 主要依赖已安装"
        ((PASS++))
    else
        warn "Python 依赖" "有 $MISSING 个包未安装"
        echo "   运行：pip3 install -r requirements.txt"
    fi
fi

echo ""
echo "========================================="
echo "  总结"
echo "========================================="
echo "✅ 通过：$PASS"
echo "⚠️  警告：$WARN"
echo "❌ 失败：$FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "🎉 环境基本就绪！"
    echo ""
    
    # 检查是否需要下载 Grype DB
    if ! grep -q 'grype_db:.*\.db' config.yaml 2>/dev/null; then
        echo "💡 建议："
        echo "   ./scripts/download_grype_db.sh ./grype-db"
        echo ""
    fi
    
    echo "启动服务:"
    echo "   ./scripts/startup.sh"
else
    echo "❌ 存在严重问题，请先修复上述 ❌ 项"
    echo ""
    echo "常用修复命令:"
    echo "   pip3 install -r requirements.txt"
    echo "   sudo apt install p7zip-full binutils"
    echo "   curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin"
fi

echo ""
echo "========================================="
