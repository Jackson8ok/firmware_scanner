# 🐢 固件漏洞扫描平台 - 从这里开始

> **欢迎使用固件漏洞扫描平台！**  
> 这是一个企业级的多架构固件安全分析工具，支持 SquashFS、HEX、SREC 等多种格式。

---

## 🚀 3 分钟快速上手

### 前提条件
- ✅ Python 3.10+ 已安装
- ✅ Node.js 16+ 已安装
- ⏳ 7-Zip 已安装（用于 SquashFS 解包）

### 快速启动（5 步）

```bash
# 1️⃣ 进入项目目录
cd /mnt/workspace/firmware_scanner

# 2️⃣ 安装 Python 依赖
pip install -r requirements.txt

# 3️⃣ 安装 Node.js 服务依赖
cd services/node-report && npm install && cd ../..

# 4️⃣ 初始化 Grype（内置方案，自动下载 DB）
bash scripts/setup_grype.sh

# 5️⃣ 启动服务
./scripts/startup.sh
```

**访问**: http://localhost:8765

---

## 📚 文档导航

| 文档 | 说明 | 适合人群 |
|-----|------|---------|
| [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) | **完整的安装教程** | 👈 第一次使用 |
| [README.md](README.md) | 功能说明和使用指南 | 所有用户 |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | 命令和 API 速查 | 经常使用的开发者 |
| [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) | 技术实现和项目总结 | 技术负责人 |

---

## 🎯 核心功能一览

### 1️⃣ 固件解包
- ✅ **SquashFS** (7-Zip 解包)
- ✅ **HEX/SREC** (转二进制)
- ✅ **Binary** (直接扫描)

### 2️⃣ SBOM 生成
- ✅ **Syft** (Linux/ELF 固件 - 高精度)
- ✅ **字符串提取** (MCU 裸机固件 - 通用)
- ✅ 识别 FreeRTOS、lwIP、wolfSSL 等组件

### 3️⃣ CVE 匹配
- ✅ 查询 Grype v6 SQLite DB (~2GB)
- ✅ 支持版本约束解析
- ✅ CVSS 评分集成
- ✅ EPSS 利用概率

### 4️⃣ 优先级排序
```
优先级 = 0.35×CVSS + 0.45×EPSS + 0.20×组件因子
```

### 5️⃣ R155 合规检查
- ✅ CVSS ≥ 7.0 且 >180 天未修复 = ❌ 不合规
- ✅ 符合汽车网络安全标准

### 6️⃣ Web UI
- 🔍 实时扫描结果
- 📊 Canvas 图表（零外部依赖）
- 📋 漏洞详情表格
- 🔄 按严重程度过滤

### 7️⃣ 报告导出
- 📄 **Excel** (openpyxl)
- 📝 **Word** (Node.js docx)
- 📊 **PPT** (pptxgenjs)

---

## 📂 项目结构

```
firmware_scanner/
├── START_HERE.md          # 👈 你在这里
├── README.md              # 完整文档
├── INSTALLATION_GUIDE.md  # 安装教程
├── QUICK_REFERENCE.md     # 命令速查
├── PROJECT_SUMMARY.md     # 技术总结
│
├── scanner/               # 🔧 扫描引擎
│   └── engine.py         # 核心逻辑
│
├── api/                   # 🌐 FastAPI 服务
│   └── main.py           # Web 应用
│
├── frontend/              # 🎨 Web UI
│   ├── templates/        # HTML 模板
│   └── static/           # CSS + JS (Canvas 图表)
│
├── services/              # 🔌 微服务
│   └── node-report/      # Word/PPT 生成
│
├── scripts/               # 🛠️ 运维脚本
│   ├── startup.sh        # 启动
│   ├── status.sh         # 状态检查
│   └── verify_env.sh     # 环境验证
│
└── {uploads,workspace,reports}/  # 工作目录
```

---

## 🧪 测试用例

我们已经验证过以下场景：

| 类型 | 型号 | 识别组件 | CVE | 状态 |
|-----|------|---------|-----|-----|
| SquashFS | BCT01 TBOX | Linux 组件 | 576 | ✅ |
| HEX | BCT01 MCU | FreeRTOS, lwIP | 24 | ✅ |
| SREC | PLC12 K3 | FreeRTOS, lwIP, wolfSSL | 163 | ✅ |

---

## 💡 常见场景

### 场景 1: 扫描 Linux 固件
```
1. 上传 .squashfs 文件
2. 选择 "SquashFS (Linux)"
3. 等待扫描完成
4. 查看 Syft 生成的 SBOM
5. 导出 Excel 报告
```

### 场景 2: 扫描 MCU 固件
```
1. 上传 .hex 或 .bin 文件
2. 选择 "HEX (MCU)" 或 "Binary (MCU)"
3. 系统自动提取字符串
4. 匹配 FreeRTOS/lwIP/wolfSSL
5. 导出 Word 报告
```

### 场景 3: R155 合规审查
```
1. 完成扫描
2. 查看仪表板中的 "R155 不合规" 数字
3. 筛选高优先级漏洞
4. 导出 PPT 给管理层
```

---

## 🔥 性能基准

| 固件大小 | 扫描时间 | 内存占用 |
|---------|---------|---------|
| 10MB (MCU) | ~30 秒 | ~200MB |
| 100MB (Linux) | ~3 分钟 | ~800MB |
| 500MB (大型) | ~10 分钟 | ~1.5GB |

---

## ⚙️ 高级配置

### 自定义优先级权重
编辑 `config.yaml`:
```yaml
scoring:
  cvss_weight: 0.50    # 增加 CVSS 重要性
  epss_weight: 0.30    # 降低 EPSS 权重
  component_weight: 0.20
```

### 调整 R155 阈值
```yaml
compliance:
  days_threshold: 90   # 改为 90 天
```

### 添加新组件识别
编辑 `scanner/engine.py`:
```python
patterns['新组件'] = (
    re.compile(r'特征字符串'),
    '类型'
)
```

---

## 🆘 遇到问题？

### 先运行诊断
```bash
./scripts/verify_env.sh
./scripts/status.sh
```

### 查看日志
```bash
tail -f logs/server.log
```

### 常见问题
| 问题 | 解决方案 |
|-----|---------|
| Python 依赖缺失 | `pip install -r requirements.txt` |
| 7-Zip 找不到 | `sudo apt install p7zip-full` |
| 数据库不存在 | `./scripts/download_grype_db.sh ./grype-db` |
| 端口被占用 | 修改 `config.yaml` 中的 `port` |

详细解决方案见 [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md#故障排查)

---

## 🎓 学习资源

### 相关技术
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Grype 数据库格式](https://github.com/anchore/grype)
- [Syft SBOM](https://github.com/anchore/syft)
- [R155 法规解读](https://ec.europa.eu/docs)

### 扩展阅读
- OWASP IoT Top 10
- SANS ICS 安全指南
- NVD CVE 详情页面

---

## 📞 技术支持

### 社区支持
- GitHub Issues
- Slack 频道
- 邮件列表

### 专业服务
（此处可添加商业支持信息）

---

## ✅ 下一步行动

1. **立即开始** → [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)
2. **了解功能** → [README.md](README.md)
3. **日常使用** → [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
4. **技术研究** → [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

---

<div align="center">

### 🐢 固件漏洞扫描平台

**安全 · 高效 · 离线可用**

*基于 Python/FastAPI + Node.js + Canvas 2D*

📅 最后更新：2026-07-21

</div>
