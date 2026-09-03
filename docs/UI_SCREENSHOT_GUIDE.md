# AFVS UI 截图指南

**日期**: 2026-09-03  
**版本**: v2.7.1  
**状态**: ⏳ 待执行  

---

## 📸 截图清单

### 1. 首页 - 上传界面

**URL**: `http://localhost:8765/`

**内容**:
- 🐢 Logo + 标题
- 📤 单文件上传区域
- 📦 批量扫描区域
- 🔌 WebSocket 状态指示器

**预期效果**:
```
┌─────────────────────────────────────────┐
│  🐢 玄武·AFVS - 汽车固件漏洞扫描器         │
│  基于 Grype + Syft 的多架构固件安全分析   │
├─────────────────────────────────────────┤
│  📤 固件扫描                             │
│  ┌─────────────────────────────────┐   │
│  │  📁 选择固件文件                 │   │
│  │  [SquashFS ▼] [上传并扫描]      │   │
│  └─────────────────────────────────┘   │
│                                         │
│  📦 批量扫描                             │
│  [📂 选择多个文件] [🚀 开始批量扫描]    │
└─────────────────────────────────────────┘
```

---

### 2. 仪表板 - 统计卡片

**URL**: `http://localhost:8765/?scan=test_123`

**内容**:
- 📊 7 个统计卡片（总漏洞/严重/高危/中危/低危/R155 不合规/R155 合规得分）
- 🔍 数据筛选面板
- 📊 Excel/PDF导出按钮

**预期效果**:
```
┌─────────────────────────────────────────┐
│  📊 扫描结果仪表板                        │
├─────────────────────────────────────────┤
│  ┌─────┐┌─────┐┌─────┐┌─────┐┌─────┐  │
│  │总数 ││严重 ││高危 ││中危 ││低危 │  │
│  │ 475 ││ 43  ││ 22  ││ 156 ││ 254 │  │
│  └─────┘└─────┘└─────┘└─────┘└─────┘  │
│                                         │
│  ┌───────────┐ ┌───────────┐           │
│  │R155 不合规│ │R155 合规得分│           │
│  │    89     │ │   85/100  │           │
│  │           │ │  (优秀)   │           │
│  └───────────┘ └───────────┘           │
└─────────────────────────────────────────┘
```

---

### 3. 图表展示

**内容**:
- 📊 漏洞严重程度分布（柱状图）
- 🥧 CVE 优先级分布（饼图）
- 📈 扫描趋势（折线图）
- 🎯 R155 合规雷达图

**预期效果**:
```
┌──────────────────┐ ┌──────────────────┐
│ 严重程度分布     │ │ CVE 优先级分布     │
│                  │ │                  │
│ ████ Critical    │ │     ████ P0     │
│ ██ High          │ │   ██████ P1     │
│ ██████ Medium    │ │     ████ P2     │
│ ████████ Low     │ │       ██ P3     │
└──────────────────┘ └──────────────────┘
```

---

### 4. 漏洞详情表格

**内容**:
- CVE ID、组件、版本、严重程度、CVSS、优先级、R155 合规、操作

**预期效果**:
```
┌─────────────────────────────────────────┐
│ CVE ID    │ 组件     │ 严重程度│ CVSS │
├───────────┼──────────┼─────────┼──────┤
│ CVE-2023…│ FreeRTOS │ 🔴 严重  │ 9.8  │
│ CVE-2022…│ lwIP     │ 🟠 高危  │ 8.5  │
│ CVE-2021…│ busybox  │ 🟡 中危  │ 5.3  │
└─────────────────────────────────────────┘
```

---

### 5. HTML 详细报告

**URL**: `/api/reports/{task_id}/html?template=detailed`

**内容**:
- 📝 执行摘要
- 📊 统计卡片
- 📈 可视化图表
- 📋 完整漏洞清单
- 💡 修复建议

---

## 🔧 执行步骤

### 步骤 1: 启动服务

```bash
cd /mnt/workspace/firmware_scanner

# 清理旧数据
rm -rf db/*.db uploads/* workspace/*
mkdir -p db uploads/sbom workspace logs reports

# 启动服务
python3 -m uvicorn api.main:_base_app \
  --host 0.0.0.0 \
  --port 8765
```

### 步骤 2: 验证服务

```bash
# 健康检查
curl http://localhost:8765/api/health
# 应返回：{"version": "2.7.1", ...}

# 访问首页
open http://localhost:8765/
```

### 步骤 3: 使用 browser_visible 截图

```python
# 使用 browser_visible skill
from browser_visible import Browser

browser = Browser(headless=False)
browser.open("http://localhost:8765/")

# 截图 1: 首页
browser.snapshot("ui-screenshots/01-homepage.png")

# 上传测试固件
browser.click("#firmwareFile")
# ... 继续操作

# 截图 2: 仪表板
browser.snapshot("ui-screenshots/02-dashboard.png")

# 截图 3: 图表
browser.snapshot("ui-screenshots/03-charts.png")

# 截图 4: 漏洞表格
browser.snapshot("ui-screenshots/04-vuln-table.png")

# 截图 5: HTML 报告
browser.open("http://localhost:8765/api/reports/test_123/html?template=detailed")
browser.snapshot("ui-screenshots/05-html-report.png")
```

---

## 📁 截图保存位置

```
/mnt/workspace/firmware_scanner/docs/ui-screenshots/
├── 01-homepage.png       # 首页上传界面
├── 02-dashboard.png      # 仪表板总览
├── 03-charts.png         # 图表展示
├── 04-vuln-table.png     # 漏洞表格
└── 05-html-report.png    # HTML 详细报告
```

---

## 🎨 截图要求

### 技术要求
- 分辨率：1920x1080 或更高
- 格式：PNG（无损压缩）
- 质量：高（用于文档展示）

### 内容要求
- 包含完整浏览器窗口（地址栏可见）
- 数据清晰可读
- 颜色准确（严重程度颜色编码）
- 无敏感信息（使用测试数据）

---

## ⏭️ 后续使用

截图完成后，用于：
1. 更新 `UI_SHOWCASE_v2.7.0.md`
2. 创建产品宣传材料
3. 客户演示文档
4. GitHub README 插图

---

## 📞 注意事项

1. **Grype DB**: 如无 Grype DB，CVE 匹配会跳过，但不影响 UI 展示
2. **测试数据**: 使用预设的测试固件样本
3. **WebSocket**: 确保 WebSocket 正常连接（状态指示器显示绿色）
4. **浏览器**: 使用 Chrome/Edge 等现代浏览器

---

**维护者**: 攻城狮阿信 [Jackson]  
**邮箱**: zhu80k@163.com

---

⟦ UI 截图指南创建完成｜包含 5 个截图场景/执行步骤/技术要求；下一步：实际执行截图或继续任务 A（Git 推送）｜锚点：UI 截图指南，browser_visible, v2.7.1 ⟧
