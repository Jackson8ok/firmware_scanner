# 📄 PDF 导出功能说明

## 功能概述

玄武固件安全扫描平台支持两种 PDF 报告生成方式：

1. **服务器端生成**（优先）- 通过后端 API 生成专业格式的 PDF
2. **客户端生成**（备用）- 使用浏览器直接生成 PDF，无需依赖后端

---

## 使用方法

### 方法一：通过界面前端按钮

1. **上传并扫描固件**
   - 在首页点击"选择文件"
   - 上传固件文件
   - 点击"开始分析"进行扫描

2. **等待扫描完成**
   - 扫描进度会通过 WebSocket 实时显示
   - 完成后会自动展示漏洞详情和统计图表

3. **点击"📄 导出 PDF 报告"按钮**
   - 位于"漏洞详情"区域上方
   - 与 Excel 导出按钮并排
   - 系统会优先使用服务器端生成
   - 如果服务器不可用，自动切换到客户端生成

4. **下载 PDF 报告**
   - 文件命名格式：`xuanwu_scan_report_{scan_id}.pdf`
   - 包含完整的扫描结果、统计图表和漏洞列表

### 方法二：程序化调用

如果您需要编程方式生成 PDF，可以使用以下代码：

```javascript
// 前提：currentScanId 已设置（扫描 ID）
await generateClientSidePDF(currentScanId);
```

---

## 技术实现

### 客户端 PDF 生成技术栈

| 库 | 用途 | CDN 地址 |
|---|------|---------|
| **jsPDF** | PDF 文档创建和操作 | https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js |
| **html2canvas** | HTML 元素截图转 Canvas | https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js |

### 工作流程

```
用户点击导出按钮
    ↓
检查服务器端 API 是否可用
    ↓
┌──────────────┬─────────────────┐
│   服务器可用  │   服务器不可用   │
│              │                 │
│ ↓            │ ↓               │
│调用          │执行客户端生成     │
│/api/report/pdf│                │
│              │ 1. 获取内容      │
│              │ 2. html2canvas  │
│              │ 3. jsPDF 合成    │
│              │ 4. 触发下载      │
└──────────────┴─────────────────┘
    ↓
下载 PDF 文件到本地
```

### 生成的 PDF 内容

导出的 PDF 报告包含：

- ✨ **报告标题**: "玄武固件安全扫描报告"
- 📅 **扫描时间**: 准确的扫描日期和时间
- 📊 **仪表盘数据**: 
  - CVE 总数
  - 严重/高危漏洞数
  - R155 合规得分
  - 合规等级
- 📈 **图表可视化**:
  - 严重程度分布饼图
  - 优先级分布柱状图
  - 风险趋势折线图
  - R155 合规雷达图
- 📋 **漏洞详细列表**:
  - CVE ID
  - 组件名称和版本
  - 严重程度和 CVSS 评分
  - 优先级
  - R155 合规状态
- 🧩 **识别的组件**: 固件中检测到的所有软件组件

---

## 测试方法

### 1. 运行自动化测试脚本

打开浏览器开发者工具（F12），在 Console 中运行：

```javascript
// 加载测试脚本（如果在页面中未自动加载）
// <script src="/static/test-pdf-export.js"></script>

// 运行完整测试
testPDFExport();
```

测试结果包括：
- ✅ jsPDF 库加载检查
- ✅ html2canvas 库加载检查
- ✅ 导出按钮存在性检查
- ✅ PDF 生成功能测试

### 2. 手动测试步骤

1. 确保有扫描数据（已完成一次固件扫描）
2. 打开控制台
3. 运行 `testGeneratePDF()`
4. 检查是否成功下载 PDF

### 3. 常见问题排查

**问题：点击按钮后没有反应**

解决步骤：
```javascript
// 1. 检查是否有当前扫描 ID
console.log('Current Scan ID:', currentScanId);

// 2. 检查库是否加载
console.log('jsPDF:', window.jspdf);
console.log('html2canvas:', window.html2canvas);

// 3. 检查按钮是否存在
console.log('Export Button:', document.getElementById('exportPdfBtn'));
```

**问题：PDF 生成失败**

常见原因：
- ❌ 网络问题导致 CDN 库加载失败
  - 解决：检查网络连接，尝试刷新页面
  
- ❌ 没有扫描数据
  - 解决：先完成一次固件扫描
  
- ❌ 浏览器兼容性
  - 解决：使用 Chrome/Edge/Firefox 等现代浏览器
  
- ❌ Content-Security-Policy 限制
  - 解决：检查 CSP 配置，允许加载 CDN 资源

**问题：PDF 图像模糊**

已在代码中优化：
```javascript
// 使用了 scale: 2 提高清晰度
const canvas = await html2canvas(exportContainer, {
    scale: 2, // 2 倍分辨率
    useCORS: true,
    logging: false
});
```

---

## 性能优化

### 当前实现的优势

✅ **无需等待服务器处理** - 客户端即时生成  
✅ **降低服务器负载** - 不消耗后端计算资源  
✅ **离线可用** - 只要有扫描数据就能生成  
✅ **隐私保护** - 数据不离开用户浏览器  

### 文件大小控制

- 默认使用 PNG 格式，质量平衡
- 自动计算图片尺寸，避免过大
- A4 纸张比例，标准打印格式

### 内存管理

```javascript
// 使用临时容器，生成后立即移除
document.body.removeChild(exportContainer);

// 清理 Object URL
window.URL.revokeObjectURL(url);
```

---

## 高级定制

### 修改 PDF 样式

编辑 `app.js` 中的 `generateClientSidePDF()` 函数：

```javascript
// 更改标题
doc.text('您的自定义标题', 105, 15, { align: 'center' });

// 更改字体大小
doc.setFontSize(你的字号);

// 更改颜色
doc.setTextColor(红值，绿值，蓝值);

// 添加页脚
doc.setFontSize(8);
doc.text('第 1 页', 105, 280, { align: 'center' });
```

### 添加公司 Logo

```javascript
// 在顶部添加 Logo
doc.addImage('logo.png', 'PNG', 10, 10, 30, 10);
doc.text('公司名称', 45, 15);
```

### 选择性导出

只导出特定部分：

```javascript
// 只导出漏洞表格
const tableSection = document.querySelector('.vulnerabilities-section');
// ... 然后处理该区域
```

---

## 故障排除

### 诊断命令

```javascript
// 检查所有必要的元素和函数
function diagnose() {
    console.group('PDF 导出诊断');
    console.log('1. jsPDF 加载:', !!window.jspdf);
    console.log('2. html2canvas 加载:', !!window.html2canvas);
    console.log('3. PDF 函数定义:', typeof generateClientSidePDF);
    console.log('4. 当前扫描 ID:', currentScanId);
    console.log('5. 导出按钮:', document.getElementById('exportPdfBtn'));
    console.groupEnd();
}

// 运行诊断
diagnose();
```

### 日志级别

开发环境下启用详细日志：

```javascript
const canvas = await html2canvas(exportContainer, {
    logging: true,  // 启用日志
    onProgress: (value) => {
        console.log(`Canvas 渲染进度: ${value * 100}%`);
    }
});
```

---

## 兼容性

### 浏览器支持

| 浏览器 | 最低版本 | 状态 |
|-------|---------|------|
| Chrome | 65+ | ✅ 完全支持 |
| Edge | 79+ | ✅ 完全支持 |
| Firefox | 60+ | ✅ 完全支持 |
| Safari | 12.1+ | ✅ 完全支持 |
| IE 11 | ❌ | 不支持 |

### 移动端支持

- iOS Safari 12.1+ : ⚠️ 可用但可能较慢
- Android Chrome 65+: ✅ 良好

---

## 未来改进计划

### 短期（v2.4）

- [ ] 添加 PDF 模板选择功能（简洁版/详细版）
- [ ] 支持自定义导出范围（仅图表/仅表格）
- [ ] 添加水印功能
- [ ] 支持批量导出多个扫描报告

### 中期（v2.5）

- [ ] 增加电子签名功能
- [ ] 支持加密 PDF
- [ ] 添加目录索引
- [ ] 支持多语言报告

### 长期

- [ ] 与服务器端生成合并，智能选择最优方案
- [ ] 支持 Word、Markdown 等其他格式
- [ ] 云存储集成（自动保存到 Google Drive/Dropbox）

---

## 相关资源

### 官方文档

- **jsPDF 文档**: https://cdnjs.github.io/jspdf/
- **html2canvas 文档**: https://html2canvas.hertzen.com/
- **GitHub 仓库**: https://github.com/eKoopmans/html2canvas

### 技术文章

- [使用 jsPDF 生成 PDF](https://medium.com/@your-repo)
- [前端导出 PDF 最佳实践](https://dev.to/pdf-best-practices)

---

## 更新日志

### v2.3.1 (2026-08-10)

- ✨ 新增客户端 PDF 生成功能
- 🔧 添加 jsPDF 和 html2canvas CDN 引用
- 🐛 修复服务器 API 不可用时的降级处理
- 📝 创建测试脚本和使用文档

### v2.3.0 (2026-08-07)

- ✨ 初始 PDF 导出按钮 UI 实现
- 🔗 集成服务器端 PDF API

---

## 技术支持

遇到问题？请提供以下信息：

1. 浏览器版本和信息
2. 错误控制台输出
3. 扫描数据规模（CVE 数量）
4. 复现步骤

🦞 **玄武固件安全扫描平台** | 安全 · 可靠 · 高效
