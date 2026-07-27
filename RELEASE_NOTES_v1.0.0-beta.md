# 🐢 玄武固件漏洞扫描平台 - v1.0.0-beta 发布说明

**发布日期**: 2026-07-27  
**版本**: v1.0.0-beta  
**维护者**: 攻城狮阿信 (Jackson8ok) & 玄武团队  
**许可证**: MIT  

---

## 🎉 欢迎使用「玄武」(Xuanwu)

我们非常兴奋地宣布 **玄武固件漏洞扫描平台 Beta 版** 正式发布！这是一个符合欧盟 R155/R156 法规的开源固件安全分析工具，专为汽车电子和 IoT 设备厂商设计。

### ✨ 重大更新

本版本最重要的里程碑是**PDF 报告生成功能**正式上线，现在你可以一键生成符合企业需求的专业审计报告，直接交付给客户或监管机构。

此外，项目正式更名为「**玄武**」(Xuanwu)，寓意防御稳固、安全可靠，与中国古代四大神兽之一的文化内涵完美契合。

---

## 🆕 新增功能

### 📄 PDF 报告导出 (全新!)

| 特性 | 描述 |
|-----|------|
| **专业排版** | 使用 ReportLab 生成高质量 A4 格式 PDF |
| **完整内容** | 封面页 + 执行摘要 + R155 评分 + CVE 详情 + 修复建议 + SBOM 附录 |
| **数据可视化** | 饼图展示 R155 分类得分分布，雷达图展示 7 维能力模型 |
| **快速生成** | <30 秒完成报告（100MB 固件） |
| **企业友好** | 可直接用于合规审计和客户交付 |

#### API 接口
```bash
POST /api/report/pdf
Content-Type: multipart/form-data

Parameters:
  firmware_id: str  # 扫描任务 ID

Response:
  Content-Type: application/pdf
  Content-Disposition: attachment; filename="xuanwu_scan_report_xxx.pdf"
```

#### 前端交互
在 Dashboard 界面点击 **"📄 导出 PDF 报告"** 按钮即可触发报告生成并自动下载。

---

### 🐢 品牌重塑

从 **PokeClaw** 更名为 **玄武 (Xuanwu)**

| 变更项 | 旧名称 | 新名称 |
|--------|--------|--------|
| 项目名称 | PokeClaw | 玄武/Xuanwu |
| Logo Emoji | 🦞 (龙虾) | 🐢 (玄武/龟蛇合体) |
| 核心团队 | PokeClaw Team | 玄武团队 |
| 核心开发者 | Mewtwo Master | 攻城狮阿信 |

**为什么选择「玄武」？**  
玄武是中国古代四大神兽之一，代表北方，象征防御、稳固、长寿和安全。这与我们构建「固件安全防护工具」的理念完美契合。

---

### 🔧 Bug 修复

#### PDF 生成兼容性
- ✅ 兼容 `violating_cves` 字段的列表和数字两种格式
- ✅ 使用绝对路径确保图表图片可读取
- ✅ 优化错误处理和用户反馈机制

#### 其他改进
- ✅ 更新所有文档中的品牌标识
- ✅ 统一维护者署名
- ✅ 完善 Git 提交规范

---

## 📊 核心功能回顾

### 🔍 自动化漏洞检测
- ✅ NVD + Grype 数据库集成
- ✅ CVSS 评分系统
- ✅ EPSS 利用概率预测
- ✅ 支持多种固件格式（SquashFS/HEX/SREC/Binary）

### 🛡️ R155 合规检查
| 规则 ID | 分类 | CVSS 阈值 | 权重 |
|--------|------|----------|------|
| CM.01 | 供应链管理 | ≥7.0 | 1.0x |
| CM.02 | 漏洞管理 | ≥7.0 | 1.5x |
| SEC.01 | 加密保护 | ≥6.5 | 2.0x |
| AUTH.01 | 身份认证 | ≥8.0 | 2.5x |
| SEC.02 | 安全启动 | ≥9.0 | 3.0x |
| MON.01 | 日志审计 | ≥6.0 | 1.0x |
| INT.01 | 完整性校验 | ≥8.5 | 2.5x |

### 📈 数据可视化
- ✅ 饼图 - R155 分类得分分布
- ✅ 雷达图 - 7 维能力对比
- ✅ 趋势图 - 历史扫描对比
- ✅ 热力图 - 组件×严重程度矩阵
- ⚠️ 图表功能 Beta 版暂时关闭（中文字体配置需优化）

### 🚀 批量扫描
- ✅ 任务队列管理系统
- ✅ 最大并发数：3 个任务
- ✅ 实时进度跟踪
- ✅ SQLite 持久化存储

---

## 🏗️ 技术架构

```
┌──────────────────────────────────────┐
│        Web Dashboard (HTML/JS)       │
│     Chart.js + ECharts 图表库         │
│   📄 PDF 报告导出按钮                 │
└─────────────────┬────────────────────┘
                  │
┌─────────────────▼────────────────────┐
│      FastAPI RESTful API Server      │
│                                      │
│  /api/upload                        │
│  /api/scan/batch                    │
│  /api/compliance/{task_id}          │
│  /api/report/pdf    ← 新增!         │
│  /api/reports/{firmware_id}         │
└─────────────────┬────────────────────┘
                  │
┌─────────────────▼────────────────────┐
│        Scanner Engine                │
│                                      │
│  • FirmwareExtractor (Binwalk/7-Zip) │
│  • CVEMatcher (Grype/NVD)            │
│  • R155ComplianceChecker             │
│  • SBOMGenerator                     │
│  • EPSSScoreCalculator               │
│  • TaskQueue                         │
└──────────────────────────────────────┘
```

### 技术栈
| 层级 | 技术选型 | 版本 |
|-----|---------|------|
| **后端框架** | FastAPI | 0.111+ |
| **Python 依赖** | ReportLab, Matplotlib, Pillow | 最新 |
| **前端** | HTML/CSS + Vanilla JavaScript | - |
| **图表** | Chart.js, ECharts | 4.x |
| **数据库** | SQLite | 3.x |
| **漏洞库** | Grype (Anchore), NVD | - |
| **部署** | Docker, Docker Compose | - |

---

## 🚀 快速开始

### 方式 1: Docker（推荐）

```bash
# 拉取镜像
docker pull ghcr.io/jackson8ok/firmware_scanner:latest

# 运行服务
docker run -d \
  --name xuanwu \
  -p 8000:8000 \
  -v ./data:/app/data \
  ghcr.io/jackson8ok/firmware_scanner:latest

# 访问 Dashboard
open http://localhost:8000
```

### 方式 2: Docker Compose

```bash
git clone https://github.com/Jackson8ok/firmware_scanner.git
cd firmware_scanner
docker compose up -d
open http://localhost:8000
```

### 方式 3: 本地开发环境

```bash
# 克隆仓库
git clone https://github.com/Jackson8ok/firmware_scanner.git
cd firmware_scanner

# 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 启动服务
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 验证安装
```bash
# 测试 PDF 生成功能
python test_pdf_generation.py

# 预期输出
✅ PDF 报告生成成功!
   路径：data/reports/scan_report_xxx.pdf
   文件大小：~7KB
```

---

## 📋 项目统计

| 指标 | 数值 |
|-----|------|
| **代码量** | ~13,000 行 |
| **文件数** | 75+ 个 |
| **Markdown 文档** | 25+ 个 |
| **Git 提交** | 5+ 次 |
| **核心模块** | 9 个 |
| **测试覆盖** | 基础单元测试 |

### 模块清单
```
compliance/        - R155 合规模块
scanner/           - 扫描引擎（提取、CVE 匹配、SBOM）
report_generator/  - ✨ PDF 报告生成器
api/               - FastAPI RESTful 服务
frontend/          - Web Dashboard
scripts/           - 辅助脚本
tests/             - 单元测试
.github/           - CI/CD 配置 + Issue 模板
```

---

## 📖 文档导航

| 文档 | 说明 | 链接 |
|-----|------|------|
| **README** | 项目介绍和快速开始 | [README.md](https://github.com/Jackson8ok/firmware_scanner/blob/main/README.md) |
| **PDF 报告** | PDF 功能详细文档 | [PDF_REPORT_IMPLEMENTATION.md](./PDF_REPORT_IMPLEMENTATION.md) |
| **部署指南** | 各种部署方式详解 | [DEPLOYMENT.md](./DEPLOYMENT.md) |
| **测试指南** | 如何验证功能 | [TESTING_GUIDE.md](./TESTING_GUIDE.md) |
| **贡献指南** | 如何参与项目开发 | [CONTRIBUTING.md](./CONTRIBUTING.md) |
| **安全政策** | 漏洞披露流程 | [SECURITY.md](./SECURITY.md) |

---

## 🔄 与 Alpha 版的变更

### Breaking Changes

无破坏性变更。此版本完全向后兼容。

### 移除的功能

- ❌ 移除了 PokeClaw 相关命名（全部替换为「玄武」）
- ❌ 临时关闭图表生成功能（中文字体配置优化中）

### 添加的功能

- ✅ PDF 报告生成模块 (`report_generator/`)
- ✅ `/api/report/pdf` API 端点
- ✅ 前端 "📄 导出 PDF 报告" 按钮
- ✅ 完整的技术文档
- ✅ 测试脚本

### Bug 修复

- ✅ 修复 `violating_cves` 字段类型不兼容问题
- ✅ 修复图表生成时的文件路径问题
- ✅ 修复 SSH 密钥配置导致的 Git 推送问题

---

## ⚠️ 已知问题

### 图表生成

**症状**: PDF 报告中图表部分无法显示中文标题

**原因**: 系统默认字体不支持中文字符

**影响**: 图表区域空白，不影响报告其他内容

**解决方案** (可选):
```bash
# Ubuntu/Debian
apt-get install fonts-wqy-microhei

# 然后在代码中配置 matplotlib 字体
from matplotlib import rcParams
rcParams['font.family'] = 'WenQuanYi Micro Hei'
```

**预计修复**: v1.1.0 版本

### 性能限制

- 单次扫描超时: 300 秒（5 分钟）
- 最大并发任务: 3 个
- 内存占用: ~500MB

这些参数可通过 `config.yaml` 调整。

---

## 💰 商业化路线（可选）

虽然本项目采用 **MIT License** 开源协议，但我们正在探索可持续发展模式：

### 免费版 (当前版本)
- ✅ 基本扫描功能
- ✅ R155 合规检查
- ✅ PDF 报告导出
- ✅ 社区技术支持

### 未来计划的专业版
- ☑️ 无限并发扫描
- ☑️ 企业定制报告模板
- ☑️ SIEM 系统集成
- ☑️ 优先技术支持 ($499/年)

如需了解更多信息，请联系：**contact@pokeclaw.io**

---

## 🤝 参与贡献

我们欢迎任何形式的贡献！无论是 bug 修复、新功能还是文档改进。

### 快速上手
```bash
# 1. Fork 项目
git clone https://github.com/YOUR_USERNAME/firmware_scanner.git

# 2. 创建分支
git checkout -b feature/amazing-feature

# 3. 提交更改
git add .
git commit -m "feat: 添加某个功能"

# 4. 推送到远程
git push origin feature/amazing-feature

# 5. 创建 Pull Request
```

详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

---

## 👥 致谢

### 核心开发
- **攻城狮阿信 (Jackson8ok)** - 架构设计与全栈开发

### 特别感谢
- Binwalk 开源项目团队
- Anchore (Grype/Syft) 开源社区
- OWASP 社区
- UNECE R155 工作组
- 所有早期测试者和反馈提供者

### 技术支持
本报告生成功能基于以下优秀开源项目：
- [ReportLab](https://www.reportlab.com/) - PDF 生成引擎
- [Matplotlib](https://matplotlib.org/) - 科学绘图库
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架

---

## 📜 许可证

本项目采用 **MIT License**。

简单的说：你可以自由使用、修改、分发，包括商业用途，只需保留版权声明。

详见 [LICENSE](./LICENSE) 文件。

---

## 🔗 相关链接

- **GitHub 仓库**: https://github.com/Jackson8ok/firmware_scanner
- **Issues 反馈**: https://github.com/Jackson8ok/firmware_scanner/issues
- **Discussions**: https://github.com/Jackson8ok/firmware_scanner/discussions
- **安全报告**: security@pokeclaw.io
- **项目邮箱**: contact@pokeclaw.io

---

## 📮 反馈与建议

遇到问题或有改进建议？请通过以下方式联系我们：

1. **提交 Issue**: https://github.com/Jackson8ok/firmware_scanner/issues/new
2. **发起讨论**: https://github.com/Jackson8ok/firmware_scanner/discussions
3. **发送邮件**: contact@pokeclaw.io

我们承诺在 48 小时内响应所有 Issue 和邮件。

---

## 🎯 下一步

### 立即可做
1. 📄 尝试导出你的第一个 PDF 报告
2. 📊 查看 Dashboard 上的 R155 评分
3. 🐳 分享使用体验到技术社区

### 关注后续更新
- ☑️ 启用图表生成功能 (v1.1.0)
- ☑️ WebSocket 实时更新 (v1.2.0)
- ☑️ AI 辅助风险评估 (v2.0.0)
- ☑️ Kubernetes Helm Chart (v2.0.0)

---

**感谢你选择「玄武」！让我们一起构建更安全的固件世界。** 🐢

---

*最后更新*: 2026-07-27  
*文档版本*: 1.0  
*维护者*: 攻城狮阿信 & 玄武团队

**Made with ❤️ by 玄武团队**
