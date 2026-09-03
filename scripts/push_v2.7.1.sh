#!/bin/bash
# AFVS v2.7.1 一键推送脚本
# 使用方式：./push_v2.7.1.sh

set -e

echo "═══════════════════════════════════════════════════════════"
echo "🚀 AFVS v2.7.1 一键推送脚本"
echo "═══════════════════════════════════════════════════════════"
echo ""

# 检查 Git
if ! command -v git &> /dev/null; then
    echo "❌ Git 未安装，请先安装 Git"
    exit 1
fi

# 检查是否在 Git 仓库中
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ 当前目录不是 Git 仓库"
    echo ""
    echo "请在正确的 Git 仓库目录中执行此脚本："
    echo "  cd /path/to/afvs-auto-firmware-vulnerability-scanner"
    echo "  ./scripts/push_v2.7.1.sh"
    exit 1
fi

# 检查远程仓库
REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
if [[ ! "$REMOTE" =~ "Jackson8ok/afvs-auto-firmware-vulnerability-scanner" ]]; then
    echo "⚠️  警告：远程仓库可能不正确"
    echo "   当前远程：$REMOTE"
    read -p "是否继续？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ Git 环境检查通过"
echo ""

# 显示将要提交的文件
echo "📝 将要提交的文件变更:"
echo "───────────────────────────────────────────────────────────"
git status --short
echo ""

# 确认提交
read -p "是否提交并推送 v2.7.1？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 取消推送"
    exit 1
fi

echo ""
echo "🔧 添加所有变更..."
git add -A

echo "🔧 提交代码..."
git commit -m "feat(v2.7.1-hotfix): 修复 4 项低优先级问题

修复内容:
- 修复版本号管理（config.yaml 添加 app.version）
- 修复 SBOM API 参数命名（firmware_id → task_id，向后兼容）
- 修复 SBOM 路径硬编码（支持跨平台和环境变量）
- 实现 SBOM SQLite 持久化（重启不丢失）

技术变更:
- config.yaml: +10 行（app.version, paths.sbom_*）
- api/main.py: +2/-2（从配置读取版本号）
- services/sbom/sbom_api.py: +126/-35（SQLite 持久化 + 路径解析）

测试:
- 语法检查：✅ 通过
- 模块导入：✅ 通过
- CRUD 测试：✅ 通过（8/8）

验收编号：VAL-AFVS-2026-015
相关文档：DEV_LOG_v2.7.1_HOTFIX.md, RELEASE_NOTES_v2.7.1.md"

echo "🔧 推送到 GitHub..."
git push origin main

echo ""
echo "🏷️  创建标签 v2.7.1..."
git tag v2.7.1

echo "🔧 推送标签..."
git push origin v2.7.1

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ v2.7.1 推送成功！"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📦 GitHub Release 创建指南:"
echo "   1. 访问：https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/new"
echo "   2. 标签：选择 v2.7.1"
echo "   3. 标题：🐢 玄武·AFVS v2.7.1 - 质量修复版"
echo "   4. 内容：使用 RELEASE_NOTES_v2.7.1.md"
echo "   5. 点击 Publish release"
echo ""
echo "📧 客户通知模板:"
echo "   参考 V2.7.1_RELEASE_GUIDE.md 中的邮件模板"
echo ""
echo "🎉 完成！"
