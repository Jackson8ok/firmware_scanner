# 🦞 固件漏洞扫描平台 - 快速部署指南

## 📋 系统要求

- Python 3.8+
- Linux/WSL2 (推荐 Ubuntu 20.04+)
- 至少 2GB 可用磁盘空间
- 8GB+ RAM (推荐)

---

## 🚀 一键部署

### 1. 克隆/进入项目目录

```bash
cd /mnt/workspace/firmware_scanner
```

### 2. 启动服务

```bash
./scripts/startup.sh
```

服务将启动在以下端口：
- **Web 界面**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

### 3. 验证安装

```bash
curl http://localhost:8000/health
# 应返回：{"status":"ok","timestamp":"..."}
```

---

## 🎯 快速使用

### 单个文件扫描

1. 打开浏览器访问 http://localhost:8000
2. 选择"单个文件扫描"标签
3. 上传固件文件（支持 .bin, .hex, .srec, squashfs 等）
4. 选择固件类型
5. 点击"开始扫描"

等待扫描完成，查看结果。

### 批量扫描

1. 切换到"批量扫描"标签
2. 上传多个固件文件
3. 选择固件类型
4. 设置最大并发数（默认 3）
5. 点击"开始批量扫描"

可以实时监控每个任务的进度。

---

## 🔒 R155 合规报告

### 查看合规详情

扫描完成后，页面会自动显示：

1. **R155 合规评分卡片**
   - 显示总评分（0-100）
   - 根据分数显示等级：
     - ✅ 优秀 (≥90)
     - ⚠️ 良好 (75-89)
     - ⚠️ 中等 (60-74)
     - ❌ 需改进 (<60)

2. **合规详情选项卡**
   点击或滚动到"R155 合规报告"区域，包含三个选项卡：

   - **📋 违规详情**: 列出所有违反 R155 规则的 CVE
   - **📊 类别得分**: 饼图展示各分类得分分布
   - **💡 改进建议**: 提供具体的修复指导

### API 调用示例

获取完整合规报告：

```bash
curl http://localhost:8000/api/compliance/{task_id}
```

查看类别得分：

```bash
curl http://localhost:8000/api/compliance/categories/{task_id}
```

运行测试脚本：

```bash
./scripts/test_r155.sh
```

---

## 📁 项目结构

```
firmware_scanner/
├── README.md                 # 本文档
├── PROJECT_SUMMARY.md        # 本周工作总结
├── config.yaml              # 配置文件
│
├── compliance/              # R155 合规模块 ✨
│   ├── __init__.py
│   └── r155_rules.py       # 核心规则引擎
│
├── scanner/                 # 扫描引擎
│   ├── engine.py           # 提取 + 识别逻辑
│   ├── task_queue.py       # 任务队列 (+合规集成)
│   ├── epss_cache.py       # EPSS 评分缓存
│   └── sbom_generator.py   # SBOM 生成器
│
├── api/                     # REST API
│   └── main.py             # FastAPI 服务
│
├── frontend/                # Web 前端
│   ├── templates/
│   │   └── index.html      # 主页面
│   └── static/
│       ├── styles.css      # 样式表
│       ├── app.js          # 主应用逻辑
│       ├── charts.js       # 图表组件
│       └── r155-ui.js      # R155 UI 交互 ✨
│
├── scripts/                 # 辅助脚本
│   ├── startup.sh          # 启动脚本
│   ├── stop.sh             # 停止脚本
│   ├── batch_scan.py       # 批量扫描工具
│   ├── report_export.py    # 报告导出工具
│   └── test_r155.sh        # R155 功能测试 ✨
│
└── data/                    # 数据存储
    ├── vulndb.sqlite       # 漏洞数据库
    ├── scans/              # 固件文件存储
    └── reports/            # 导出的报告
```

---

## 🔧 配置说明

### 修改配置 (`config.yaml`)

```yaml
server:
  host: "0.0.0.0"  # 监听地址
  port: 8000       # 监听端口
  debug: false     # 开发模式开启

scanning:
  max_concurrent: 3     # 最大并发扫描数
  timeout: 300         # 单次扫描超时 (秒)
  
paths:
  uploads: "./data/scans"
  reports: "./data/reports"
  database: "./data/vulndb.sqlite"
```

### 性能优化

调整并发数（根据机器性能）：

```bash
# 高配机器 (16GB+ RAM, 8+ cores)
max_concurrent: 5

# 中配机器 (8GB RAM, 4 cores)
max_concurrent: 3

# 低配机器 (4GB RAM, 2 cores)
max_concurrent: 1
```

---

## 📊 功能特性清单

### W1-D1: 基础框架 ✅
- [x] 项目初始化
- [x] 配置文件创建
- [x] 数据库设计
- [x] 基本目录结构

### W1-D2: 批量扫描队列 ✅
- [x] SQLite 任务队列
- [x] 多线程并发控制
- [x] 实时进度跟踪
- [x] 错误处理和重试

### W1-D3: Dashboard 增强 ✅
- [x] AJAX 实时刷新
- [x] EPSS 评分集成
- [x] 优先级排序算法
- [x] ECharts 可视化
- [x] Excel/PDF/YAML导出

### W1-D4: R155 合规深化 ✅
- [x] R155 法规规则引擎
  - 7 条核心合规规则
  - 自动违规检测
  - 智能打分算法
- [x] 合规报告生成器
  - 类别得分分析
  - 修复建议生成
- [x] 扫描流程集成
- [x] REST API 端点
- [x] 前端 UI 组件
  - 合规评分卡片
  - 违规详情表格
  - 雷达图可视化
  - 选项卡切换

---

## 🐛 故障排查

### 问题 1: 服务无法启动

**症状**: `./scripts/startup.sh` 无响应或报错

**解决**:
```bash
# 检查 Python 版本
python3 --version  # 应 >= 3.8

# 检查依赖
pip3 list | grep -E "(fastapi|uvicorn|sqlalchemy)"

# 手动安装缺失的包
pip3 install fastapi uvicorn sqlalchemy python-multipart pandas openpyxl chart-studio
```

### 问题 2: 数据库文件锁定

**症状**: `sqlite3.OperationalError: database is locked`

**解决**:
```bash
# 停止所有服务
pkill -f "uvicorn.*main:app"

# 删除锁文件
rm -f ./data/*.sqlite-journal
```

### 问题 3: R155 报告未显示

**症状**: 扫描完成后看不到合规评分卡片

**原因**: 
- 可能没有发现 R155 相关漏洞
- 或者前端 JavaScript 加载失败

**解决**:
```bash
# 检查浏览器控制台
# F12 -> Console 查看是否有错误

# 确认 r155-ui.js 正确加载
curl http://localhost:8000/static/r155-ui.js
# 应该返回 JS 代码内容
```

---

## 📈 监控和维护

### 查看日志

```bash
# 查看最近的服务日志
tail -f logs/app.log

# 查看数据库查询
tail -f logs/sql.log
```

### 清理旧数据

```bash
# 保留最近 30 天的扫描记录
python3 scripts/cleanup.py --days 30
```

### 备份数据库

```bash
cp data/vulndb.sqlite backup/vulndb_$(date +%Y%m%d).sqlite
```

---

## 🔐 安全建议

1. **不要在生产环境暴露公网**
   - 仅限内网访问
   - 或使用 Nginx 反向代理 + HTTPS

2. **定期更新 CVE 数据库**
   ```bash
   python3 scripts/update_cve_db.py
   ```

3. **限制上传文件大小**
   - 在 `config.yaml` 中设置 `max_file_size: 500MB`

4. **定期备份数据**
   ```bash
   tar -czf backup_$(date +%Y%m%d).tar.gz data/
   ```

---

## 🤝 贡献指南

### 添加新的合规规则

编辑 `compliance/r155_rules.py`:

```python
ComplianceRule(
    rule_id="NEW.01",
    category="Your Category",
    requirement="描述新规则的要求",
    description="详细说明",
    severity_weight=1.5,  # 惩罚权重
    component_types=["Component Type"],  # 可选
    cvss_threshold=7.0,   # CVSS 阈值
    max_days_threshold=120  # 允许的最长修复时间
)
```

### 修改 UI 样式

编辑 `frontend/static/styles.css`,找到 `.stat-card.compliance` 相关样式。

---

## 📞 技术支持

- **文档**: http://localhost:8000/docs
- **Issues**: GitHub Issues Tracker
- **Email**: support@firmware-scanner.local

---

## 📄 许可证

本项目仅供学习和研究目的使用。

---

**版本**: v1.0.0  
**最后更新**: 2026-07-23  
**作者**: Mewtwo Master & Team 🦞
