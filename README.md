# 🐢 玄武 - 固件漏洞扫描平台

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-blue.svg)
![R155 Compliance](https://img.shields.io/badge/R155-R156%20Compliant-brightgreen)
![Release](https://img.shields.io/github/v/release/Jackson8ok/firmware_scanner?label=Latest)
[![Stars](https://img.shields.io/github/stars/Jackson8ok/firmware_scanner?style=social)](https://github.com/Jackson8ok/firmware_scanner/stargazers)

**🚀 一键生成 R155 审计所需全部文档 · 固件安全分析 · SBOM自动化生成 · 漏洞优先级排序**

📖 [快速上手](#快速开始) | 📋 [审计报告包详解](#审计报告包) | 🚀 [90 天商业化路线图](#90 天商业化路线图) | 💼 [企业服务](#企业版服务) | 🤝 [贡献指南](#contributing)

</div>

---

## 🎯 为什么选择玄武？

### ⭐ **解决真实痛点**

汽车企业面临 R155/R156法规强制要求，但传统做法存在巨大痛点:

| 传统方式 | 玄武方案 |
|---------|---------|
| ❌ 外包审计费 ¥5K-20K | ✅ 基础功能永久免费 |
| ❌ 人工准备 2-3 周 | ✅ 一键生成 30 分钟 |
| ❌ 容易出错、遗漏 | ✅ 标准化、无遗漏 |
| ❌ 每次审计都要重做 | ✅ 可复用、可追溯 |

**一句话**: **用免费工具省下数万外包费，把专业审计团队的工作变成自动化的事**

---

## 📦 什么是"审计报告包"?

**玄武 v2.5+ 的核心价值**: 扫描一次固件，自动生成完整 R155 审计所需的全部 8 份文档

```bash
上传固件 → 点击扫描 → 下载 ZIP 报告包
```

**ZIP 内容**:
- 📄 **执行摘要.pdf** - 高管 5 分钟了解整体安全状况
- 📊 **合规评分卡.pdf** - 审计员快速判断是否达标
- 🔍 **差距分析报告.pdf** - 当前状态 vs 法规要求的详细对照
- 📋 **漏洞清单.xlsx** - 研发团队修复参考（含优先级排序）
- 💡 **整改建议书.docx** - 按时间排列的修复方案
- 📦 **SBOM.json** - CycloneDX 格式软件物料清单
- ⚖️ **合规性矩阵.pdf** - 逐条核对 R155 法规条款符合性
- 📎 **附件证明.zip** - 测试日志、配置截图等证明材料

**适用场景**: 季度审计、新车认证、出口欧盟申报、供应链安全审查

---

## 🎯 核心功能

### 🏆 **行业标准支持**

- ✅ **R155/R156法规自动化检查** - 内置 EU 法规规则引擎
- ✅ **CVSS + EPSS 综合评分** - 精准识别高优先级漏洞
- ✅ **CycloneDX SBOM 生成** - 符合各国供应链安全要求
- ✅ **多车型批量扫描** - 一次性处理多个 ECU 固件

### 📊 **智能报告系统**

- ✅ **审计报告包一键生成** - 8 份文档自动打包下载
- ✅ **漏洞优先级智能排序** - 基于 CVSS+EPSS+业务影响
- ✅ **Word/PDF/Excel多格式导出** - 满足不同场景需求
- ✅ **自定义企业模板** - Logo、配色、公司信息预设

### 🔄 **开发者友好**

- ✅ **WebSocket 实时进度** - 看到每一步的扫描状态
- ✅ **RESTful API** - 轻松集成到 CI/CD 流程
- ✅ **Docker 一键部署** - 零配置启动
- ✅ **插件化架构** - 自定义规则和处理器

---

## 🚀 Quick Start

### 一键启动（推荐）

```bash
# 克隆仓库
git clone https://github.com/Jackson8ok/firmware_scanner.git
cd scanner

# 启动服务
./scripts/startup.sh

# 访问界面
open http://localhost:8000  # macOS
# 或浏览器打开 http://localhost:8000
```

### Docker 部署（生产环境）

```bash
docker run -d \
  --name xuanwu-scanner \
  -p 8000:8000 \
  -v ./data:/app/data \
  ghcr.io/Jackson8ok/firmware_scanner:latest
  
docker exec -it xuanwu-scanner tail -f logs/app.log
```

### 手动安装

```bash
# Python 3.8+ required
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# 初始化 Grype（自动下载二进制 + 漏洞数据库）
bash scripts/setup_grype.sh

# 启动服务
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## 📦 审计报告包详解

### v2.5+ 核心功能：一键生成完整审计材料

玄武独有的**审计报告包**功能，为汽车企业解决 R155 合规审计的材料准备难题。

#### 使用流程

```bash
# Web 界面操作（推荐）
1. 打开 http://localhost:8000
2. 上传固件文件
3. 点击"开始分析"
4. 扫描完成后点击"📄 导出审计报告包"
5. 下载 ZIP 文件即可直接使用

# API 方式
curl -X POST "http://localhost:8000/api/report/audit-package/{task_id}" \
  -o audit_report_package.zip
```

#### 生成的报告清单

| 序号 | 文件名 | 格式 | 主要用途 | 受众 |
|-----|-------|------|---------|------|
| 1 | 执行摘要.pdf | PDF | 高层快速了解整体状况 | CEO/CTO |
| 2 | 合规评分卡.pdf | PDF | 判断是否达到 R155 要求 | 审计员 |
| 3 | 差距分析报告.pdf | PDF | 识别未满足的法规条款 | 合规部门 |
| 4 | 漏洞清单.xlsx | Excel | 详细漏洞数据供修复参考 | 研发团队 |
| 5 | 整改建议书.docx | Word | 修复优先级和时间表 | 项目经理 |
| 6 | SBOM.json | JSON | 供应链透明度审查 | 采购/法务 |
| 7 | 合规性矩阵.pdf | PDF | 逐条核对法规符合性 | 外部审计机构 |
| 8 | 附件证明.zip | ZIP | 佐证材料归档 | 认证机构 |

#### 价值对比

| 指标 | 传统人工方式 | 玄武方案 | 提升幅度 |
|-----|-------------|---------|---------|
| **准备时间** | 2-3 周 | 30 分钟 | 97% ↓ |
| **外包费用** | ¥5,000-20,000 | ¥0 (免费基础版) | 100% ↓ |
| **错误率** | 5-10% (人工疏漏) | <1% (标准化输出) | 80% ↓ |
| **可追溯性** | 低 (文档分散) | 高 (版本化管理) | ⭐⭐⭐⭐⭐ |
| **可复用性** | 每次重做 | 模板化复用 | ⭐⭐⭐⭐⭐ |

---

## 💼 企业版服务

虽然核心功能永久免费，但我们提供专业的增值服务支持企业规模化使用：

### 🥇 **专业支持套餐** ¥5,000/月
- ✅ 工单响应 ≤ 4 小时
- ✅ 每周安全简报
- ✅ 优先 Bug 修复通道
- ✅ Slack/钉钉专属群

### 🥈 **私有化部署** ¥50,000/年
- ✅ 源码授权许可
- ✅ 定制规则开发
- ✅ 数据库本地化
- ✅ SLA 保障 99.9%
- ✅ 年度升级服务

### 🥉 **咨询服务** ¥3,000/天
- ✅ R155 合规顾问
- ✅ 定制化培训
- ✅ 架构优化建议
- ✅ 现场技术支持

**联系合作**: zhu80k@163.com

---

## 🚀 90 天商业化路线图

我们正在从开源项目向可持续商业产品演进：

### Month 1 (8 月): MVP 完成
- ✅ 审计报告生成器核心功能
- ✅ 合规得分计算引擎
- ✅ 多格式报告导出
- → **v2.5 Alpha 发布**

### Month 2 (9 月): Pilot 验证  
- ✅ 寻找 2-3 家试用企业
- ✅ 收集真实场景反馈
- ✅ 完善用户体验
- → **首个付费意向客户**

### Month 3 (10-11 月): 商业化启动
- ✅ v2.6 团队协作功能
- ✅ 订阅制服务体系
- ✅ 市场推广活动
- → **首个付费客户签约**

---

## 📸 功能演示

### Web 界面概览

<div align="center">
  
| 仪表盘 | 批量扫描 | R155 合规报告 |
|--------|----------|-------------|
| ![Dashboard](https://via.placeholder.com/400x200?text=Dashboard+Preview) | ![Batch Scan](https://via.placeholder.com/400x200?text=Batch+Scan) | ![R155 Report](https://via.placeholder.com/400x200?text=R155+Compliance) |

</div>

### 核心特性

#### 📦 **CycloneDX SBOM 生成**

```bash
# 下载任务的 SBOM（CycloneDX 1.4 JSON）
curl -X GET "http://localhost:8000/api/sbom/{task_id}" \
  -o sbom.cyclonedx.json

# 验证 SBOM 合规性
curl -X GET "http://localhost:8000/api/sbom/{task_id}/validate"

# Python SDK
from scanner.cyclonedx_sbom import generate_cyclonedx_sbom

sbom = generate_cyclonedx_sbom(
    components=[{'name': 'FreeRTOS', 'version': '10.4.6'}],
    vulnerabilities=[{'id': 'CVE-2022-30801', 'severity': 'high'}]
)

with open('sbom.cyclonedx.json', 'w') as f:
    f.write(sbom)
```

📖 **详情**: [CYCLONEDX_GUIDE.md](./docs/CYCLONEDX_GUIDE.md)

---

#### 🔍 智能漏洞检测

```bash
# 单个文件扫描
curl -X POST http://localhost:8000/api/upload \
  -F "file=@firmware.bin" \
  -F "firmware_type=squashfs"

# 批量扫描
curl -X POST http://localhost:8000/api/batch-upload \
  -F "files=@fw1.bin&files=@fw2.bin" \
  -F "firmware_type=hex"
```

#### 🛡️ R155 合规评估

```json
// GET /api/compliance/{task_id}
{
  "compliance_score": 68.5,
  "violating_cves": 4,
  "category_scores": {
    "Authentication & Access Control": 55.0,
    "Secure Boot": 82.0,
    "Supply Chain Security": 72.5
  },
  "violations": [
    {
      "rule_id": "CM.01",
      "cve_id": "CVE-2021-44228",
      "component": "Apache Log4j",
      "penalty_score": 9.5,
      "remediation": "升级到 2.17.0 或更高版本"
    }
  ],
  "recommendations": [
    "🔴 优先处理身份认证问题",
    "⚠️ 发现 4 个严重合规违规"
  ]
}
```

#### 📊 可视化分析

- **趋势图**：历史扫描合规评分变化
- **热力图**：组件×严重程度分布矩阵
- **雷达图**：7 大合规类别得分对比
- **SBOM 卡片**：组件清单可视化

---

## 🏗️ 技术架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Web UI    │ ←→  │  FastAPI API │ ←→  │  SQLite DB  │
│ (HTML/JS)   │     │  (RESTful)   │     │  (VulnDB)   │
└─────────────┘     └──────────────┘     └─────────────┘
                            ↓
         ┌────────────────────────────────┐
         │        扫描引擎层               │
         ├────────────────────────────────┤
         │ • 固件提取 (Binwalk/7-Zip)     │
         │ • SBOM 生成器                   │
         │ • CVE 匹配引擎                  │
         │ • EPSS 评分系统                 │
         │ • R155 合规检查器               │
         └────────────────────────────────┘
```

### 技术栈

| 层级 | 技术选型 |
|------|---------|
| **后端** | Python 3.8+, FastAPI, Uvicorn |
| **数据库** | SQLite (零配置) |
| **前端** | HTML5, CSS3, Vanilla JavaScript |
| **图表** | Chart.js, ECharts |
| **固件分析** | Binwalk, 7-Zip, Unblob |
| **漏洞库** | Grype (Anchore), NVD |
| **部署** | Docker, GitHub Actions CI/CD |

---

## 📁 项目结构

```
firmware_scanner/
├── compliance/              # R155 合规模块
│   ├── r155_rules.py       # 核心规则引擎
│   └── __init__.py
├── scanner/                 # 扫描引擎
│   ├── engine.py           # 提取 + 识别逻辑
│   ├── task_queue.py       # 任务队列管理
│   ├── epss_cache.py       # EPSS 评分缓存
│   └── sbom_generator.py   # SBOM 生成器
├── api/                     # REST API
│   └── main.py             # FastAPI 应用
├── frontend/                # Web 前端
│   ├── templates/
│   │   └── index.html      # 主页面
│   └── static/
│       ├── styles.css      # 样式表
│       ├── app.js          # 主逻辑
│       └── r155-ui-enhanced.js  # R155 交互
├── scripts/                 # 辅助脚本
│   ├── startup.sh          # 启动脚本
│   ├── test_r155.sh        # R155 测试
│   └── batch_scan.py       # 批量扫描工具
├── data/                    # 数据存储
│   ├── vulndb.sqlite       # 漏洞数据库
│   └── scans/              # 固件文件
├── docs/                    # 文档
│   ├── DEPLOYMENT.md       # 部署指南
│   ├── TESTING_GUIDE.md    # 测试指南
│   └── FRONTEND_ENHANCEMENTS.md
├── config.yaml             # 配置文件
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 配置
├── LICENSE                 # MIT License
└── README.md               # 本文档
```

---

## ⚙️ 配置说明

编辑 `config.yaml`：

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  debug: false

scanning:
  max_concurrent: 3       # 最大并发数
  timeout: 300            # 单次超时 (秒)
  
paths:
  uploads: "./data/scans"
  reports: "./data/reports"
  database: "./data/vulndb.sqlite"

# Grype 路径（内置方案，无需额外安装）
  grype_bin: "${GRYPE_BIN:-./tools/grype/grype}"
  # Grype SQLite 数据库路径 (~2GB)
  grype_db: "${GRYPE_DB_PATH:-./db/grype/6/vulnerability.db}"
```

---

## 🧪 测试

```bash
# 运行单元测试
python3 -m pytest tests/ -v --cov=.

# 完整性能测试
./scripts/test_r155.sh

# 压力测试（100 个并发任务）
python3 scripts/load_test.py --concurrency 100
```

---

## 🤝 Contributing

欢迎贡献！无论是 bug 修复、新功能还是文档改进。

### 开发流程

```bash
# 1. Fork 项目
git clone https://github.com/YOUR_USERNAME/scanner.git
cd scanner

# 2. 创建分支
git checkout -b feature/amazing-feature

# 3. 提交更改
git add .
git commit -m "feat: 添加某个功能"

# 4. 推送到远程
git push origin feature/amazing-feature

# 5. 创建 Pull Request
```

### 代码规范

- 遵循 PEP 8 Python 代码规范
- 函数和类需要有 docstring
- 提交信息使用约定式格式
- 新增代码需包含测试用例

### 开发指南

详见 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📚 相关资源

### 文档

- [部署指南](./DEPLOYMENT.md) - 完整部署流程
- [测试指南](./TESTING_GUIDE.md) - 如何验证功能
- [前端增强](./FRONTEND_ENHANCEMENTS.md) - UI 功能详解
- [项目策划书](./PROJECT_CATALOGUE.md) - 商业计划

### 社区

- 💬 [GitHub Discussions](https://github.com/Jackson8ok/firmware_scanner/discussions) - 实时讨论
- 🐛 [GitHub Issues](https://github.com/Jackson8ok/firmware_scanner/issues) - 报告问题
- ✨ [Feature Requests](https://github.com/Jackson8ok/firmware_scanner/discussions) - 建议功能

### 学习材料

- [R155 法规原文](https://unece.org/r155)
- [NVD 漏洞数据库](https://nvd.nist.gov)
- [OWASP IoT Top 10](https://owasp.org/www-project-internet-of-things/)
- [ISO/SAE 21434](https://www.iso.org/standard/70935.html)

---

## 📊 当前状态

![GitHub stars](https://img.shields.io/github/stars/Jackson8ok/firmware_scanner?style=social)
![GitHub forks](https://img.shields.io/github/forks/Jackson8ok/firmware_scanner?style=social)
![GitHub issues](https://img.shields.io/github/issues/Jackson8ok/firmware_scanner)
![GitHub pull requests](https://img.shields.io/github/issues-pr/Jackson8ok/firmware_scanner)

**里程碑达成:**

| 阶段 | 状态 | 日期 |
|------|------|------|
| W1-D1 基础框架 | ✅ 完成 | 2026-07-21 |
| W1-D2 批量扫描 | ✅ 完成 | 2026-07-22 |
| W1-D3 Dashboard 增强 | ✅ 完成 | 2026-07-23 |
| W1-D4 R155 合规 | ✅ 完成 | 2026-07-24 |
| W2 PDF/Excel导出 | ✅ 完成 | 2026-08-10 |
| W2 WebSocket 实时通知 | ✅ 完成 | 2026-08-07 |

---

## 🏆 支持者

感谢以下个人或组织的支持：

### 企业赞助者
- _暂无_ （等你来！）

### 个人支持者
- [你的名字] - 核心开发者

❤️ 想成为下一个支持者吗？通过 [GitHub Sponsors](https://github.com/sponsors/pokeclaw) 或 [Open Collective](https://opencollective.com/pokeclaw) 支持我们！

---

## 📄 许可证

本项目采用 **MIT License**。详见 [LICENSE](LICENSE) 文件。

简单的说：你可以自由使用、修改、分发，包括商业用途，只需保留版权声明。

---

## 🙏 致谢

特别感谢：

- [Binwalk](https://github.com/ReFirmLabs/binwalk) - 固件分析工具
- [Grype](https://github.com/anchore/grype) - 漏洞扫描引擎
- [Chart.js](https://chartjs.org) - 图表库
- [FastAPI](https://fastapi.tiangolo.com) - 后端框架
- [UNECE](https://unece.org) - R155 法规制定

---

## 📞 联系方式

- 项目负责人：攻城狮阿信[Jackson]
- Email: zhu80k@163.com
- GitHub: https://github.com/Jackson8ok/firmware_scanner
- 地址：中国·上海

---

**Made with ❤️ by the 玄武 Team**

[![Star History Chart](https://api.star-history.com/svg?repos=Jackson8ok/firmware_scanner&type=Date)](https://star-history.com/#Jackson8ok/firmware_scanner&Date)
