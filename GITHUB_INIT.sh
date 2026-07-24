#!/bin/bash
# PokeClaw 开源准备 - GitHub 初始化脚本
# 
# 使用方法:
#   ./GITHUB_INIT.sh
#
# 前提条件:
#   - Git 已安装
#   - 已在 GitHub 创建仓库
#   - SSH key 已配置（或准备使用 HTTPS）

set -e

echo "🦞 PokeClaw 开源准备 - GitHub 初始化"
echo "======================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 Git 是否已安装
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ 错误：Git 未安装${NC}"
    echo "请先安装 Git: https://git-scm.com/downloads"
    exit 1
fi

# 检查当前目录
if [ ! -f "LICENSE" ] || [ ! -f "README.md" ]; then
    echo -e "${RED}❌ 错误：这不是 PokeClaw 项目根目录${NC}"
    echo "请在包含 LICENSE 和 README.md 的目录下运行此脚本"
    exit 1
fi

echo -e "${BLUE}ℹ️  步骤 1: 检查现有 Git 状态${NC}"
if [ -d ".git" ]; then
    echo "Git 仓库已存在"
    git status --short | head -5
else
    echo "⚠️  还未初始化 Git 仓库"
fi

echo ""
echo -e "${BLUE}ℹ️  步骤 2: 创建远程仓库${NC}"
echo "请在 GitHub 上执行以下操作:"
echo "  1. 访问 https://github.com/new"
echo "  2. 仓库名：scanner (或其他你喜欢的名字)"
echo "  3. 可见性：Public (公开)"
echo "  4. 不要勾选 'Initialize with README'"
echo "  5. 点击 'Create repository'"
echo ""

read -p "是否已创建 GitHub 仓库？(y/n): " create_done
if [ "$create_done" != "y" ]; then
    echo -e "${YELLOW}⏸️  请先创建仓库后按任意键继续...${NC}"
    read -n 1
fi

echo ""
echo -e "${BLUE}ℹ️  步骤 3: 初始化 Git 仓库${NC}"

if [ ! -d ".git" ]; then
    echo "初始化 Git..."
    git init
    git add .
    git commit -m "chore: 初始化项目 - 准备好开源

- ✅ MIT License
- ✅ 完整 README 文档
- ✅ CI/CD流水线
- ✅ Docker 部署支持
- ✅ 贡献指南和安全政策
- ✅ Issue 和 PR 模板"
    echo -e "${GREEN}✅ 初始提交完成${NC}"
else
    echo "⚠️  Git 仓库已存在，跳过初始化"
fi

echo ""
echo -e "${BLUE}ℹ️  步骤 4: 添加远程仓库${NC}"
echo "请输入你的 GitHub 用户名:"
read github_username
echo "请输入仓库名（默认为 scanner）:"
read repo_name
repo_name=${repo_name:-scanner}

echo ""
echo "将设置两种远程连接方式，选择你偏好的："
echo "  1) SSH (推荐，需要配置 SSH Key)"
echo "  2) HTTPS (简单但需输入密码)"
read -p "请选择 (1/2): " ssh_choice

if [ "$ssh_choice" = "1" ]; then
    remote_url="git@github.com:${github_username}/${repo_name}.git"
    echo -e "${YELLOW}⚠️  如果提示 Permission denied，请先配置 SSH Key${NC}"
    echo "     参考：https://docs.github.com/en/authentication/connecting-to-github-with-ssh"
else
    remote_url="https://github.com/${github_username}/${repo_name}.git"
fi

# 删除旧的 remote（如果有）
git remote remove origin 2>/dev/null || true

git remote add origin ${remote_url}
echo -e "${GREEN}✅ 远程仓库已添加：${remote_url}${NC}"

echo ""
echo -e "${BLUE}ℹ️  步骤 5: 推送代码到 GitHub${NC}"
git branch -M main
git push -u origin main --force
echo -e "${GREEN}✅ 代码已推送到 GitHub${NC}"

echo ""
echo -e "${BLUE}ℹ️  步骤 6: 创建版本标签${NC}"
echo "创建 v1.0.0-alpha 标签..."
git tag v1.0.0-alpha
git push origin v1.0.0-alpha
echo -e "${GREEN}✅ 标签已推送${NC}"

echo ""
echo -e "${BLUE}ℹ️  步骤 7: 启用保护规则${NC}"
echo "请访问以下链接配置分支保护:"
echo "  ${remote_url/settings/branches}"
echo ""
echo "建议开启:"
echo "  ☑️ Require a pull request before merging"
echo "  ☑️ Require approvals (至少 1 人)"
echo "  ☑️ Require status checks to pass before merging"
echo "  ☑️ Do not allow bypassing the above settings"

echo ""
echo -e "${BLUE}ℹ️  步骤 8: 发布第一个 Release${NC}"
echo "请访问 Releases 页面创建首个版本:"
echo "  ${remote_url}/releases/new"
echo ""
echo "填写:"
echo "  Tag version: v1.0.0-alpha"
echo "  Title: Alpha Release 🦞"
echo "  Description: 复制 OPEN_SOURCE_PREPARATION_REPORT.md 中的内容"

echo ""
echo "=========================================="
echo -e "${GREEN}🎉 恭喜！PokeClaw 已成功开源！${NC}"
echo "=========================================="
echo ""
echo "下一步行动:"
echo ""
echo "1. 📢 分享到社交媒体"
echo "   - Twitter/X: @PokeClawIO"
echo "   - LinkedIn"
echo "   - Reddit (r/netsec, r/opensource)"
echo "   - Hacker News"
echo ""
echo "2. 👥 邀请早期用户试用"
echo "   - 技术社区朋友"
echo "   - 安全研究团队"
echo "   - 汽车电子厂商"
echo ""
echo "3. 📊 监控数据"
echo "   - GitHub Insights: ${remote_url}/insights"
echo "   - Star History: https://starchart.cc/${github_username}/${repo_name}"
echo ""
echo "4. 🤝 欢迎贡献者"
echo "   - 回复 Issues"
echo "   - Review Pull Requests"
echo "   - 添加 good first issue 标签"
echo ""
echo "5. 📈 持续改进"
echo "   - 定期更新 Changelog"
echo "   - 保持文档同步"
echo "   - 响应社区反馈"
echo ""
echo -e "${BLUE}ℹ️  需要帮助？${NC}"
echo "  Email: contact@pokeclaw.io"
echo "  Discord: [待配置]"
echo ""
echo -e "${YELLOW}⭐ 祝你好运！记住，开源不仅是代码，更是社区！${NC}"
echo ""
