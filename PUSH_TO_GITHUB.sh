#!/bin/bash
# v2.7.1 紧急推送脚本
# 使用方式：./PUSH_TO_GITHUB.sh <YOUR_GITHUB_TOKEN>

set -e

TOKEN="${1:-}"
REPO="https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner.git"

if [ -z "$TOKEN" ]; then
    echo "❌ 错误：缺少 GitHub Token"
    echo ""
    echo "使用方法:"
    echo "  ./PUSH_TO_GITHUB.sh <YOUR_GITHUB_TOKEN>"
    echo ""
    echo "获取 Token 步骤:"
    echo "  1. 访问 https://github.com/settings/tokens"
    echo "  2. 点击 'Generate new token (classic)'"
    echo "  3. 勾选 'repo' 权限"
    echo "  4. 生成并复制 Token"
    echo "  5. 运行：./PUSH_TO_GITHUB.sh ghp_xxxxxxxxxxxx"
    exit 1
fi

cd /mnt/workspace/firmware_scanner

echo "🚀 开始推送到 GitHub..."
echo ""

# 推送主分支
git push "${REPO/https:\/\//https://${TOKEN}@}" main

echo ""
echo "✅ 推送成功！"
echo ""
echo "下一步:"
echo "  1. 访问 https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner"
echo "  2. 确认最新提交：feat(v2.7.1-hotfix): 修复 4 项低优先级问题"
echo "  3. 创建 Release v2.7.1 (可选)"
