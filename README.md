# 🦞 PokeClaw - 固件漏洞扫描平台

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-blue.svg)
![R155](https://img.shields.io/badge/R155-Compliant-brightgreen.svg)
[![Stars](https://img.shields.io/github/stars/pokeclaw/scanner?style=social)](https://github.com/pokeclaw/scanner/stargazers)

**欧盟 R155/R156 合规自动化 · 汽车固件安全分析 · SBOM生成**

📖 [文档](./DEPLOYMENT.md) | 🚀 [快速开始](#quick-start) | 💡 [示例](#examples) | 🤝 [贡献](#contributing)

</div>

---

## 🎯 项目简介

PokeClaw 是一个**开源的固件安全分析平台**，专注于：

- ✅ **自动化 CVE 检测** - 集成 NVD + Grype 数据库
- ✅ **R155 合规检查** - 符合欧盟 UNECE R155/R156法规
- ✅ **SBOM 生成** - 自动生成 CycloneDX 格式软件物料清单
- ✅ **EPSS 评分** - 漏洞利用概率预测
- ✅ **批量扫描** - 支持并发处理多个固件
- ✅ **可视化仪表板** - 实时进度 + 高级图表分析

**目标用户：** 汽车电子制造商、IoT 设备厂商、安全研究团队、学术机构

---

## 🚀 Quick Start

### 一键启动（推荐）

```bash
# 克隆仓库
git clone https://github.com/pokeclaw/scanner.git
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
  --name pokeclaw \
  -p 8000:8000 \
  -v ./data:/app/data \
  ghcr.io/pokeclaw/scanner:latest
  
docker exec -it pokeclaw tail -f logs/app.log
```

### 手动安装

```bash
# Python 3.8+ required
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# 下载 Grype 漏洞数据库
./scripts/download_grype_db.sh

# 启动服务
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## 📸 功能演示

### Web 界面概览

<div align="center">
  
| 仪表盘 | 批量扫描 | R155 合规报告 |
|--------|----------|-------------|
| ![Dashboard](https://via.placeholder.com/400x200?text=Dashboard+Preview) | ![Batch Scan](https://via.placeholder.com/400x200?text=Batch+Scan) | ![R155 Report](https://via.placeholder.com/400x200?text=R155+Compliance) |

</div>

### 核心特性

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

# Grype 数据库路径
grype_db: "/path/to/grype-db/vulnerability.db"
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

- 💬 [Discord 服务器](https://discord.gg/pokeclaw) - 实时讨论
- 🐛 [GitHub Issues](https://github.com/pokeclaw/scanner/issues) - 报告问题
- ✨ [Feature Requests](https://github.com/pokeclaw/scanner/discussions) - 建议功能

### 学习材料

- [R155 法规原文](https://unece.org/r155)
- [NVD 漏洞数据库](https://nvd.nist.gov)
- [OWASP IoT Top 10](https://owasp.org/www-project-internet-of-things/)
- [ISO/SAE 21434](https://www.iso.org/standard/70935.html)

---

## 📊 当前状态

![GitHub stars](https://img.shields.io/github/stars/pokeclaw/scanner?style=social)
![GitHub forks](https://img.shields.io/github/forks/pokeclaw/scanner?style=social)
![GitHub issues](https://img.shields.io/github/issues/pokeclaw/scanner)
![GitHub pull requests](https://img.shields.io/github/issues-pr/pokeclaw/scanner)

**里程碑达成:**

| 阶段 | 状态 | 日期 |
|------|------|------|
| W1-D1 基础框架 | ✅ 完成 | 2026-07-21 |
| W1-D2 批量扫描 | ✅ 完成 | 2026-07-22 |
| W1-D3 Dashboard 增强 | ✅ 完成 | 2026-07-23 |
| W1-D4 R155 合规 | ✅ 完成 | 2026-07-24 |
| W2 PDF/Excel导出 | 🔄 进行中 | 2026-07-25 |

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

- 项目负责人：Mewtwo Master
- Email: contact@pokeclaw.io
- 网站：https://pokeclaw.io
- 地址：中国·上海

---

**Made with ❤️ by the PokeClaw Team**

[![Star History Chart](https://api.star-history.com/svg?repos=pokeclaw/scanner&type=Date)](https://star-history.com/#pokeclaw/scanner&Date)
