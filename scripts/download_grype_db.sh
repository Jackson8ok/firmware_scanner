#!/bin/bash
# Grype v6 漏洞数据库下载脚本

set -e

echo "========================================="
echo "  🐢 Grype v6 漏洞数据库下载"
echo "========================================="

# 输出目录
OUTPUT_DIR="${1:-./grype-db}"
mkdir -p "$OUTPUT_DIR"

cd "$OUTPUT_DIR"

echo ""
echo "目标目录：$(pwd)"
echo ""

# 最新版本
DB_URL="https://toolbox-data.anchore.io/grype/databases/vulnerability-db_v6_latest.tar.gz"

echo "开始下载 Grype v6 数据库..."
echo "URL: $DB_URL"
echo ""

# 使用 wget 或 curl
if command -v wget &> /dev/null; then
    echo "使用 wget 下载..."
    wget --progress=bar:force "$DB_URL" -O vulnerability-db.tar.gz
elif command -v curl &> /dev/null; then
    echo "使用 curl 下载..."
    curl -L --progress-bar "$DB_URL" -o vulnerability-db.tar.gz
else
    echo "❌ 需要安装 wget 或 curl"
    exit 1
fi

echo ""
echo "下载完成，解压中..."

# 解压
tar xzf vulnerability-db.tar.gz

# 清理压缩包
rm vulnerability-db.tar.gz

# 查找生成的数据库
DB_FILE=$(find . -name "*.db" -type f | head -n1)

if [ ! -f "$DB_FILE" ]; then
    echo "❌ 未找到数据库文件"
    ls -la
    exit 1
fi

DB_SIZE=$(du -h "$DB_FILE" | cut -f1)

echo ""
echo "========================================="
echo "✅ 下载完成！"
echo ""
echo "数据库路径：$(realpath "$DB_FILE")"
echo "数据库大小：$DB_SIZE"
echo ""
echo "下一步:"
echo "1. 编辑 config.yaml"
echo "2. 设置 grype_db = \"$(realpath "$DB_FILE")\""
echo "3. 运行 ./scripts/startup.sh"
echo "========================================="

# 显示配置片段
echo ""
echo "在 config.yaml 中添加/修改:"
echo "---"
cat << EOF
paths:
  grype_db: "$(realpath "$DB_FILE")"
EOF
echo "---"
