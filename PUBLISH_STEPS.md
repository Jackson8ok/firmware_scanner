# 🚀 玄武 GitHub 发布步骤

## ✅ 已完成的工作

- [x] Git 仓库初始化
- [x] 所有文件已提交 (75 个文件, 18,471+ 行)
- [x] 主分支重命名为 `main`
- [x] 版本标签 `v1.0.0-alpha` 已创建

---

## 📋 下一步：推送到 GitHub

### 步骤 1: 在 GitHub 创建仓库

1. **访问**: https://github.com/new
2. **填写信息**:
   - Repository name: `scanner` (或 `pokeclaw-scanner`)
   - Description: `🦞 固件漏洞扫描平台 - R155/R156合规检查`
   - Visibility: **Public** (公开)
   - ⚠️ **不要勾选** "Initialize with README" 等选项
3. **点击**: "Create repository"

### 步骤 2: 获取仓库 URL

创建后会显示类似这样的命令:

```bash
git remote add origin git@github.com:YOUR_USERNAME/scanner.git
```

**复制那个 SSH URL** (形如 `git@github.com:username/repo.git`)

### 步骤 3: 设置远程并推送

在你的终端执行:

```bash
cd /mnt/workspace/firmware_scanner

# 添加远程仓库 (替换 YOUR_USERNAME 和 repo_name)
git remote add origin git@github.com:YOUR_USERNAME/scanner.git

# 推送主分支
git push -u origin main

# 推送标签
git push origin v1.0.0-alpha
```

**如果还没有 SSH Key:**
```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "your_email@example.com"

# 复制公钥
cat ~/.ssh/id_ed25519.pub

# 在 GitHub Settings → SSH and GPG keys 中添加
```

---

## 🎯 推送后必做事项

### 1. 启用分支保护规则

访问: `https://github.com/YOUR_USERNAME/scanner/settings/branches`

**建议设置**:
- ☑️ Require a pull request before merging
- ☑️ Require approvals (至少 1 人)
- ☑️ Require status checks to pass before merging  
- ☑️ Do not allow bypassing the above settings

### 2. 发布第一个 Release

访问: `https://github.com/YOUR_USERNAME/scanner/releases/new`

**填写内容**:
- Tag version: `v1.0.0-alpha`
- Target: `main`
- Title: `Alpha Release 🦞 - 开源首发版`
- Description: 复制下方模板

**Release 描述模板**:
```markdown
## 🎉 欢迎使用 玄武 固件漏洞扫描平台!

首个 Alpha 版本正式发布!这是一个开源的、符合欧盟 R155/R156 法规的固件安全分析工具。

### ✨ 核心功能

- 🔍 **自动化 CVE 检测** - 集成 NVD + Grype 数据库
- 🛡️ **R155 合规检查** - 7 条核心法规自动评估
- 📊 **实时可视化** - 高级图表展示扫描结果
- 🚀 **批量扫描** - 支持并发处理多个固件
- 🐳 **Docker 部署** - 一键启动，零配置

### 📦 快速开始

```bash
docker run -d --name pokeclaw -p 8000:8000 ghcr.io/Jackson8ok/firmware_scanner:latest
open http://localhost:8000
```

### 📊 项目统计

- 代码量: 9,434+ 行
- Python 后端 + JavaScript 前端
- MIT License 开源协议
- 完整 CI/CD 流水线

### 🤝 参与贡献

查看 [CONTRIBUTING.md](https://github.com/YOUR_USERNAME/scanner/blob/main/CONTRIBUTING.md)

### 📚 文档

- [README](https://github.com/YOR_USERNAME/scanner/blob/main/README.md)
- [部署指南](https://github.com/YOUR_USERNAME/scanner/blob/main/DEPLOYMENT.md)
- [测试指南](https://github.com/YOUR_USERNAME/scanner/blob/main/TESTING_GUIDE.md)

### 🙏 感谢

早期贡献者: Mewtwo Master & 玄武 Team

---
**Made with ❤️ by 玄武 Team**
```

### 3. 配置 CI/CD Badge

在 README 中更新徽章链接:

```markdown
![Build Status](https://github.com/YOUR_USERNAME/scanner/actions/workflows/ci-cd.yml/badge.svg)
![GitHub Release](https://img.shields.io/github/v/release/YOUR_USERNAME/scanner)
![License](https://img.shields.io/github/license/YOUR_USERNAME/scanner)
![Stars](https://img.shields.io/github/stars/YOUR_USERNAME/scanner?style=social)
```

### 4. 启用 GitHub Discussions

访问: `https://github.com/YOUR_USERNAME/scanner/discussions/setup`

启用讨论区，用于社区交流和问题咨询。

### 5. 添加 Topics

在仓库首页编辑 Topics:
```
security-scanning
firmware-analysis
r155-compliance
automotive-security
iot-security
vulnerability-detection
open-source
python
fastapi
docker
```

---

## 📢 发布后推广

### 立即行动

1. **Twitter/X 帖子** (示例):
   ```
   🎉  excited to announce 玄武 Scanner - an open-source 
   firmware vulnerability scanner for R155/R156 compliance!
   
   🔍 Auto CVE detection
   🛡️ R155 compliance check  
   📊 Real-time visualization
   🐳 Docker ready
   
   Try it now: https://github.com/YOUR_USERNAME/scanner
   
   #InfoSec #OpenSource #CyberSecurity #Automotive
   ```

2. **Reddit 发布**:
   - r/netsec (技术深度文章)
   - r/opensource (开源项目介绍)
   - r/cybersecurity (应用场景分享)

3. **Hacker News**: 
   - 标题: "玄武: An open-source firmware scanner for R155 compliance"
   - 重点强调技术实现和社区价值

4. **Product Hunt**: 
   - 制作演示视频/GIF
   - 准备完整的产品介绍

---

## 🔍 验证清单

推送完成后检查:

- [ ] 代码成功推送到 GitHub
- [ ] 可以看到所有文件
- [ ] `v1.0.0-alpha` 标签可见
- [ ] CI/CD流水线运行正常 (Actions 页面)
- [ ] README 正确显示
- [ ] License 被 GitHub 识别
- [ ] Release 已发布

---

## 🆘 常见问题

**Q: 推送时提示 Permission denied?**
A: 需要先配置 SSH Key。参考上面的 SSH 设置步骤。

**Q: 需要输入密码？**
A: 如果使用 HTTPS 连接会需要密码。推荐配置 SSH 避免每次输入。

**Q: 如何回滚错误的推送？**
A: 使用 `git reset --hard HEAD~1` 撤销，然后强制推送 `git push -f`。

**Q: CI/CD没触发？**
A: 检查 `.github/workflows/` 目录是否存在，以及文件名是否正确。

---

**祝你发布顺利！🎉**

如有问题，联系: contact@pokeclaw.io
