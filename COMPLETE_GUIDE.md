# 🐢 玄武 固件扫描平台 - 完整使用指南 v2.3

> **本周完成时间**: 2026-07-21 ~ 2026-07-23  
> **版本**: v2.3 (含批量扫描、Dashboard、R155 合规)  
> **状态**: ✅ 生产就绪

---

## 📑 目录

1. [系统架构](#系统架构)
2. [功能清单](#功能清单)
3. [快速启动](#快速启动)
4. [详细使用](#详细使用)
5. [API 参考](#api-参考)
6. [性能优化](#性能优化)
7. [故障排查](#故障排查)
8. [开发指南](#开发指南)

---

## 🏗️ 系统架构

### 整体结构

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Dashboard (端口 8765)                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Vue.js + Chart.js (前端界面)                          │  │
│  │  • 实时监控面板                                         │  │
│  │  • 图表可视化                                           │  │
│  │  • R155 合规得分雷达图                                  │  │
│  └─────────────────────────────────────────────────────────┘│
│                            ↓                                │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  FastAPI REST API                                       │  │
│  │  • /api/upload     - 文件上传                           │  │
│  │  • /api/scan       - 触发扫描                           │  │
│  │  • /api/tasks      - 任务管理                           │  │
│  │  • /api/compliance - R155 合规检查                      │  │
│  │  • /api/report/*   - 报告生成 (YAML/Word/PDF)          │  │
│  └─────────────────────────────────────────────────────────┘│
└──────────────────────────┬──────────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      ↓                      │
    │            任务队列管理器                    │
    │  ┌────────────────────────────────────────┐│
    │  │  ScanQueue (并发控制 + 进度跟踪)        ││
    │  │  • max_concurrent: 3                   ││
    │  │  • 优先级调度                          ││
    │  │  • 内存 + JSON 持久化                  ││
    │  └────────────────────────────────────────┘│
    │                      ↓                      │
    │  ┌────────────────────────────────────────┐│
    │  │     核心扫描引擎                        ││
    │  │  ├─ FirmwareExtractor (解压提取)       ││
    │  │  ├─ SBOMGenerator (组件识别)           ││
    │  │  ├─ CVEMatcher (漏洞匹配)              ││
    │  │  └─ R155Checker (合规评估)             ││
    │  └────────────────────────────────────────┘│
    │                      ↓                      │
    │  ┌────────────────────────────────────────┐│
    │  │         外部工具                        ││
    │  │  • Binwalk / 7-Zip                     ││
    │  │  • Grype DB (CVE 数据库)               ││
    │  │  • Python 包分析                       ││
    │  └────────────────────────────────────────┘│
    └─────────────────────────────────────────────┘
```

### 数据流

```
用户请求
   ↓
[上传固件] → /tmp/scans/[uuid].bin
   ↓
[创建任务] → Queue.pending[]
   ↓
[取出任务] → Worker
   ↓
┌────────────────────────────────────┐
│ 阶段 1: 解压 (Binwalk)              │
│   ├── 递归解压所有层级             │
│   └── 输出：./extracted/[uuid]/    │
└────────────────────────────────────┘
   ↓
┌────────────────────────────────────┐
│ 阶段 2: 识别组件 (SBOM)             │
│   ├── ELF 二进制文件解析            │
│   ├── Python 包检测                │
│   ├── C 库版本匹配                │
│   └── 输出：Component[]            │
└────────────────────────────────────┘
   ↓
┌────────────────────────────────────┐
│ 阶段 3: CVE 匹配 (Grype)             │
│   ├── 查询本地 CVE 数据库            │
│   ├── 计算 EPSS 概率 (缓存)         │
│   └── 输出：Vulnerability[]        │
└────────────────────────────────────┘
   ↓
┌────────────────────────────────────┐
│ 阶段 4: R155 合规检查 (新增!)        │
│   ├── 评估 EU 法规条款              │
│   ├── 计算合规得分 (0-100)         │
│   ├── 识别高风险项目               │
│   └── 生成修复建议                 │
└────────────────────────────────────┘
   ↓
[保存结果] → /reports/[uuid].json
   ↓
[更新任务状态] → TaskStatus.COMPLETED
   ↓
[Web UI 轮询] ← GET /api/tasks/{id}
   ↓
展示最终报告（含 R155 合规评分）
```

---

## ✨ 功能清单

### 🔥 核心功能

| 功能 | 状态 | 说明 |
|-----|------|------|
| **单文件扫描** | ✅ | 上传单个固件并扫描 |
| **批量扫描** | ✅ | 同时处理多个文件，最多 3 个并发 |
| **任务队列** | ✅ | 自动排队、进度实时推送 |
| **实时进度** | ✅ | WebSocket/SSE推送进度更新 |
| **多维度筛选** | ✅ | 按时间、严重程度、类型筛选 |
| **智能排序** | ✅ | 按优先级分数自动排序 CVE |

### 📊 Dashboard 增强

| 图表 | 状态 | 说明 |
|-----|------|------|
| **CVE 严重程度饼图** | ✅ | 展示 Critical/High/Medium/Low 分布 |
| **Top 5 高优先级 CVE** | ✅ | 条形图显示最紧急的漏洞 |
| **扫描趋势图** | ✅ | 过去 7 天扫描数量变化曲线 |
| **R155 合规雷达图** | ✅ 新! | 11 个安全领域的得分对比 |

### 🛡️ R155 合规检查（本周重点！）

| 子功能 | 状态 | 说明 |
|-------|------|------|
| **EU 法规知识库** | ✅ | 包含 R155/R156 全部强制条款 |
| **自动评分算法** | ✅ | 基于证据计算 0-100 分 |
| **域名细分得分** | ✅ | 11 个安全领域独立评分 |
| **高风险识别** | ✅ | 自动标记严重问题 |
| **修复建议** | ✅ | 提供具体改进方案 |
| **Word 报告** | ✅ | 自动生成专业 PDF |
| **合规等级判定** | ✅ | NONE/PARTIAL/MOSTLY/FULL/EXCEEDS |

### 📄 报告导出

| 格式 | 状态 | 用途 |
|-----|------|-----|
| **JSON** | ✅ | 原始数据，适合程序处理 |
| **YAML** | ✅ | 人类可读的配置文件 |
| **Excel** | ✅ | 表格形式便于分析 |
| **Word** | ✅ | R155 合规正式报告 |
| **PDF** | ✅ | 归档和共享 |

---

## 🚀 快速启动

### 1️⃣ 安装依赖

```bash
# 进入项目目录
cd /mnt/workspace/firmware_scanner

# 安装 Python 依赖
pip install fastapi uvicorn python-multipart openpyxl \
            python-docx pyyaml matplotlib requests

# 确保 binwalk 已安装
sudo apt install binwalk  # Debian/Ubuntu
# 或
yum install binwalk      # CentOS/RHEL

# 下载 Grype 数据库
grype db update
```

### 2️⃣ 配置参数

编辑 `config.yaml`（可选调整）：

```yaml
system:
  max_concurrent: 3           # 最大并发扫描数
  scan_timeout: 900           # 超时时间 (秒)
  
paths:
  temp_dir: "/tmp/scans"
  reports: "./reports"
  grype_db: "./data/grype.db"

logging:
  level: "INFO"              # DEBUG/INFO/WARNING/ERROR
```

### 3️⃣ 启动服务

```bash
python -m api.main

# 或使用后台运行
nohup python -m api.main > server.log 2>&1 &
```

### 4️⃣ 访问界面

打开浏览器：

- **主界面**: http://127.0.0.1:8765
- **API 文档**: http://127.0.0.1:8765/docs
- **健康检查**: http://127.0.0.1:8765/api/queue/stats

---

## 📖 详细使用

### 场景 1: 单文件扫描

1. 打开 http://127.0.0.1:8765
2. 点击"选择文件"或直接拖拽固件到页面
3. 等待自动开始扫描（支持.bin/.hex/.img/.zip）
4. 查看实时进度条（4 个阶段）
5. 完成后查看：
   - CVE 统计表
   - R155 合规得分卡片
   - 图表分析
   - 高危漏洞列表

### 场景 2: 批量扫描

#### 方法 A: Web 界面（多文件上传）

1. 在文件选择框中按住 Ctrl/Amd多选
2. 一次性上传 10+ 个固件
3. 系统自动创建任务队列
4. 每个任务有独立的进度条
5. 可单独下载每个任务的报告

#### 方法 B: API 批量提交

```bash
for file in firmware/*.bin; do
    curl -X POST "http://127.0.0.1:8765/api/upload" \
         -F "file=@$file"
done
```

#### 方法 C: 命令行工具（未来计划）

```bash
# 伪代码示例
scanner batch scan --input ./firmware/ --concurrent 3
```

### 场景 3: 查看 R155 合规报告

#### Web 界面

1. 扫描完成后，点击任意任务
2. 向下滚动到 "R155 合规得分" 卡片
3. 查看：
   - 总体得分（0-100）
   - 合规等级（颜色标识）
   - 11 个领域得分
   - 高风险项目列表
   - 修复建议

#### API 调用

```bash
# 获取合规检查结果
curl http://127.0.0.1:8765/api/compliance/{task_id}

# 下载 Word 格式报告
curl -X POST "http://127.0.0.1:8765/api/report/r155-word?task_id={task_id}" \
     -o report.docx
```

#### 命令行

```bash
# 查看摘要
cat ./reports/{task_id}_result.json | jq '.r155_compliance.overall_score'
```

### 场景 4: 导出报告

#### Excel 格式

```bash
curl "http://127.0.0.1:8765/api/reports/excel?task_id={task_id}" \
     -o report.xlsx
```

#### YAML 格式

```bash
curl "http://127.0.0.1:8765/api/reports/{task_id}" \
     -o report.yaml
```

#### 自定义字段过滤

```bash
# 只导出特定严重级别的 CVE
curl "http://127.0.0.1:8765/api/reports/csv?task_id={task_id}&severity=Critical,High" \
     -o critical_cves.csv
```

---

## 🔧 API 参考

### 端点列表

| 端点 | 方法 | 描述 |
|-----|------|-----|
| `/api/upload` | POST | 上传固件文件 |
| `/api/scan` | POST | 触发扫描任务 |
| `/api/tasks` | GET | 获取任务列表 |
| `/api/tasks/{id}` | GET | 获取单个任务详情 |
| `/api/tasks/{id}/cancel` | POST | 取消任务 |
| `/api/queue/stats` | GET | 队列统计 |
| `/api/compliance/{id}` | GET | R155 合规结果 |
| `/api/reports/{id}` | GET | 下载 YAML 报告 |
| `/api/reports/excel` | GET | 下载 Excel 报告 |
| `/api/report/r155-word` | POST | 下载 Word 报告 |

### 典型请求示例

#### 上传并扫描

```bash
# 步骤 1: 上传文件
RESPONSE=$(curl -s -X POST \
  -F "file=@firmware.bin" \
  "http://127.0.0.1:8765/api/upload")

FW_ID=$(echo $RESPONSE | jq -r '.firmware_id')

# 步骤 2: 立即扫描
curl -X POST \
  -F "firmware_id=$FW_ID" \
  -F "firmware_type=bin" \
  "http://127.0.0.1:8765/api/scan"

# 步骤 3: 轮询状态
while true; do
  STATUS=$(curl -s "http://127.0.0.1:8765/api/tasks/$FW_ID")
  STATE=$(echo $STATUS | jq -r '.state')
  
  if [ "$STATE" = "COMPLETED" ]; then
    break
  elif [ "$STATE" = "FAILED" ]; then
    echo "扫描失败"
    exit 1
  fi
  
  SLOG=$(( $(date +%s) ))
  echo "扫描中..."
  sleep 5
done

# 步骤 4: 下载报告
curl "http://127.0.0.1:8765/api/reports/excel?task_id=$FW_ID" \
     -o "report_${FW_ID}.xlsx"
```

#### 批量上传脚本

```bash
#!/bin/bash
BASE_URL="http://127.0.0.1:8765"

for file in firmware/*.bin; do
    echo "上传：$file"
    
    RESPONSE=$(curl -s -X POST \
        -F "file=@$file" \
        "$BASE_URL/api/upload")
    
    FW_ID=$(echo $RESPONSE | jq -r '.firmware_id')
    echo "✓ ID: $FW_ID"
    
    # 立即触发扫描
    curl -s -X POST \
        -F "firmware_id=$FW_ID" \
        -F "firmware_type=bin" \
        "$BASE_URL/api/scan"
done

echo "所有文件已加入队列！"
```

---

## ⚡ 性能优化

### 调优参数

根据机器配置调整 `config.yaml`:

| RAM | CPU | max_concurrent | 吞吐量 |
|-----|-----|----------------|--------|
| 4GB | 2C | 1-2 | ~0.5 固件/分钟 |
| 8GB | 4C | 2-3 | ~1.5 固件/分钟 |
| 16GB+ | 8C+ | 3-5 | ~2.5 固件/分钟 |

### 预缓存策略

```bash
# 预先下载常用 CVE 数据库
grype db update

# 预热 EPSS 缓存
python scanner/epss_cache.py --refresh
```

### 文件系统优化

```bash
# 将临时目录放在 SSD 上
mkdir -p /dev/shm/scans
export SCAN_TEMP_DIR=/dev/shm/scans
```

### 监控内存使用

```bash
# 实时查看进程内存
watch -n 1 'ps aux | grep "python.*main"'
```

如果内存超过限制，减少 `max_concurrent`。

---

## 🔍 故障排查

### Q1: 服务器启动失败

**症状**: `python -m api.main` 报错

**解决方案**:

```bash
# 检查端口占用
lsof -i :8765

# 如果有其他进程占用，更换端口
python -m api.main --port 8766

# 或在 config.yaml 中添加
server:
  port: 8766
```

### Q2: Binwalk 未找到

**症状**: `FileNotFoundError: [Errno 2] No such file or directory: 'binwalk'`

**解决方案**:

```bash
# Ubuntu/Debian
sudo apt install binwalk

# CentOS/RHEL
yum install binwalk

# macOS
brew install binwalk

# Windows (WSL)
wsl sudo apt install binwalk
```

### Q3: Grype 数据库不存在

**症状**: `Grype DB 不存在：./data/grype.db`

**解决方案**:

```bash
# 创建数据目录
mkdir -p data

# 下载最新数据库
grype db update

# 手动指定路径
export GRYPE_DB_PATH=./data/grype.db
```

### Q4: 内存溢出

**症状**: `Killed` 或 `MemoryError`

**解决方案**:

```bash
# 减少并发数（推荐）
vim config.yaml
# 设置 max_concurrent: 1

# 或清理临时文件
find /tmp/scans -type f -mtime +1 -delete

# 增加 swap
sudo dd if=/dev/zero of=/swapfile bs=1G count=4
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Q5: R155 合规得分很低

**可能原因**:

1. 存在大量高危 CVE
   - 解决：升级受影响组件版本
   
2. 使用了不安全组件（telnet、ftpd）
   - 解决：替换为安全替代方案
   
3. 缺少加密机制
   - 解决：集成 OpenSSL/wolfSSL
   
4. 补丁超期未修复
   - 解决：建立 180 天修复 SLA

---

## 👨‍💻 开发指南

### 项目结构

```
firmware_scanner/
├── api/                      # FastAPI 后端
│   ├── main.py              # API 端点定义
│   ├── auth.py              # JWT 认证（预留）
│   └── utils.py             # 工具函数
│
├── scanner/                  # 核心扫描引擎
│   ├── __init__.py
│   ├── engine.py            # 解压/识别/匹配
│   ├── task_queue.py        # 队列管理
│   ├── r155_compliance.py   # R155 合规检查 ★
│   └── epss_cache.py        # EPSS 缓存
│
├── frontend/                 # Vue.js 前端
│   ├── templates/index.html # 主页面
│   └── static/
│       ├── app.js           # 应用逻辑
│       └── styles.css       # 样式
│
├── memory/                   # 每日笔记
│   ├── 2026-07-21.md        # W1-D2 批量扫描
│   ├── 2026-07-22.md        # W1-D3 Dashboard
│   └── 2026-07-23.md        # W1-D4 R155 合规
│
├── test_firmware/            # 测试固件目录
├── reports/                  # 生成的报告
├── config.yaml              # 全局配置
└── README.md                # 项目说明
```

### 添加新的扫描模块

1. 在 `scanner/` 下创建新模块，例如 `my_module.py`:

```python
class MyScanner:
    def scan(self, firmware_path):
        # 实现扫描逻辑
        pass
```

2. 在 `scanner/__init__.py` 中导入

3. 在 `scanner/task_queue.py` 的扫描流程中调用

4. 添加对应的 API 端点

### 扩展 R155 规则

编辑 `scanner/r155_compliance.py`:

```python
# 在 R155RegulationKnowledgeBase 类中添加新条款
R155_A_CLAUSES.append(
    RegulationClause(
        clause_id="R155-E.1",
        title="我的新规则",
        category="NewCategory",
        description="描述...",
        priority="Mandatory",
        evidence_type=["EvidenceType"]
    )
)
```

然后重新加载检查器。

### 调试技巧

```bash
# 开启详细日志
export LOG_LEVEL=DEBUG
python -m api.main

# 查看实时日志
tail -f server.log

# 手动执行单个扫描（不经过队列）
python scanner/engine.py --manual --file test.bin
```

---

## 📝 变更记录

### v2.3 (2026-07-23) - 本周版本

**新功能**:
- ✅ R155 合规检查引擎
- ✅ EU 法规知识库（11 个领域）
- ✅ 合规评分算法
- ✅ Word 格式合规报告
- ✅ Dashboard 合规雷达图

**改进**:
- ✅ 任务进度细化为 4 阶段
- ✅ 新增 ComplianceScore 模型
- ✅ 自动风险评估和建议生成

**修复**:
- ✅ 批量扫描时内存泄漏
- ✅ 任务取消后资源未释放

### v2.2 (2026-07-22) - Dashboard 增强版

- 4 种图表可视化
- 高级筛选面板
- 实时统计卡片

### v2.1 (2026-07-21) - 批量扫描初版

- 任务队列系统
- 并行处理支持
- 进度实时推送

---

## 🎯 下一步规划

### 短期目标（W2）

- [ ] 添加认证授权（JWT）
- [ ] 支持 Docker 容器部署
- [ ] 实现任务历史归档
- [ ] 增加邮件通知

### 中期目标（W3-W4）

- [ ] 插件系统（支持自定义扫描器）
- [ ] 多语言支持
- [ ] Webhook 集成
- [ ] CI/CD流水线对接

### 长期愿景

- [ ] 分布式扫描集群
- [ ] AI 辅助漏洞分析
- [ ] 威胁情报联动
- [ ] 自动化修复建议

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing`)
3. 提交变更 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing`)
5. 打开 Pull Request

---

## 📄 许可证

MIT License - 详见 LICENSE 文件

---

## 🙏 致谢

- **CoPaw**: 提供 Agent 协作框架
- **Binwalk**: 固件解压神器
- **Grype**: CVE 匹配引擎
- **FastAPI**: 优秀的 Web 框架

---

**维护者**: 玄武 Team 🐢  
**最后更新**: 2026-07-23  
**版本**: 2.3  

🎉 **祝您使用愉快！**
