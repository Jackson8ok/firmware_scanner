# 📄 PDF 高级定制功能 - 实施计划

**功能模块**: v2.5.0-A1  
**预计工时**: 7 天开发 + 2 天测试  
**状态**: 🟡 规划中 → 准备开始  
**负责人**: Jackson8ok / 超梦虾

---

## 🎯 功能目标

在现有客户端 PDF 导出基础上，增加以下高级定制功能：

### 核心功能列表

| 功能项 | 描述 | 优先级 |
|-------|------|--------|
| **模板选择器** | 简洁版/详细版/合规版三种预设模板 | 🔴 P0 |
| **Logo 上传** | 用户上传公司 Logo 添加到页眉 | 🔴 P0 |
| **水印功能** | 添加"Confidential"/"Internal Use Only"等水印 | 🟡 P1 |
| **品牌色配置** | 自定义报告主色调 | 🟢 P2 |
| **页面布局优化** | 多页长表格自动分页 | 🔴 P0 |

---

## 📐 UI 设计方案

### 1. PDF 导出按钮增强

**当前**: 
```html
<button id="exportPdfBtn" class="btn btn-primary">📄 导出 PDF 报告</button>
```

**改进后**:
```html
<div class="pdf-export-controls">
    <button id="exportPdfBtn" class="btn btn-primary">📄 导出 PDF</button>
    
    <!-- 展开的选项面板 -->
    <div id="pdfOptionsPanel" class="dropdown-content" style="display: none;">
        <div class="option-group">
            <label>📋 报告模板</label>
            <select id="templateSelector">
                <option value="detailed">详细版（推荐）</option>
                <option value="simple">简洁版</option>
                <option value="compliance">R155 合规版</option>
            </select>
        </div>
        
        <div class="option-group">
            <label>🏢 公司标识</label>
            <input type="file" id="logoUpload" accept="image/*">
            <small>支持 PNG/JPG，建议尺寸 200x60px</small>
        </div>
        
        <div class="option-group">
            <label>💧 添加水印</label>
            <select id="watermarkSelector">
                <option value="">无水印</option>
                <option value="confidential">机密 (CONFIDENTIAL)</option>
                <option value="internal">内部使用 (INTERNAL USE ONLY)</option>
                <option value="draft">草稿 (DRAFT)</option>
            </select>
        </div>
        
        <div class="option-group">
            <label>🎨 主题颜色</label>
            <input type="color" id="brandColorPicker" value="#2c3e50">
        </div>
        
        <div class="option-actions">
            <button id="saveAsDefault" class="btn btn-secondary">💾 保存为默认</button>
            <button id="generatePdfCustom" class="btn btn-success">✅ 生成并下载</button>
        </div>
    </div>
</div>
```

---

### 2. 三种模板对比

#### **详细版 (detailed)** - 默认
- ✅ 完整的仪表板统计
- ✅ 所有图表（严重程度、优先级、趋势、雷达图）
- ✅ 完整的漏洞列表（所有字段）
- ✅ 组件识别清单
- ✅ R155 合规分析详情
- ✅ 执行摘要和建议
- **适用场景**: 全面安全评估报告

#### **简洁版 (simple)**
- ✅ 关键统计数据（CVE 总数、严重/高危数）
- ✅ 简要图表（仅饼图）
- ✅ 前 10 个高优先级漏洞
- ✅ 关键发现摘要
- ❌ 移除次要信息
- **适用场景**: 快速预览、高层汇报

#### **合规版 (compliance)**
- ✅ R155/R156法规重点突出
- ✅ 合规得分和等级
- ✅ 违规项详细分析
- ✅ 整改建议
- ✅ 符合性矩阵
- ❌ 移除非合规相关的技术细节
- **适用场景**: 合规审计、政府申报

---

## 🛠️ 技术实现方案

### 架构调整

```javascript
// 重构前（单一函数）
async function generateClientSidePDF(scanId) {
    // ...固定逻辑
}

// 重构后（模块化）
class PDFGenerator {
    constructor(options = {}) {
        this.template = options.template || 'detailed';
        this.logoUrl = options.logoUrl;
        this.watermark = options.watermark;
        this.brandColor = options.brandColor || '#2c3e50';
    }
    
    async generate(scanId) {
        const doc = this.createDocument();
        await this.renderHeader(doc);
        await this.renderSections(doc, scanId);
        await this.renderFooter(doc);
        return doc.save();
    }
    
    createDocument() { /* ... */ }
    renderHeader(doc) { /* ... */ }
    renderSections(doc, scanId) { /* template-specific logic */ }
    renderFooter(doc) { /* ... */ }
}
```

### 代码文件结构

```
frontend/static/
├── pdf-generator.js       # 新增：PDF 生成核心类
├── pdf-templates.js       # 新增：三种模板定义
├── pdf-ui.js              # 新增：UI 交互逻辑
└── app.js                 # 修改：集成新的 PDF 系统
```

---

## 📝 详细实施步骤

### Phase 1: 基础重构 (Day 1-2)

#### Task 1.1: 创建 PDF Generator 基类
- [ ] 拆分现有 `generateClientSidePDF()` 为独立类
- [ ] 提取通用方法（createDocument, renderHeader, renderFooter）
- [ ] 确保向后兼容，不影响现有功能

**代码示例**:
```javascript
// frontend/static/pdf-generator.js

class PDFGenerator {
    constructor(options = {}) {
        this.options = {
            template: 'detailed',
            logoUrl: null,
            watermark: '',
            brandColor: '#2c3e50',
            includeCharts: true,
            maxVulnsPerPage: 20
        };
        
        Object.assign(this.options, options);
    }
    
    async generate(scanId) {
        try {
            showGeneratingIndicator();
            
            // 获取扫描数据
            const data = await this.fetchScanData(scanId);
            
            // 创建 PDF 文档
            const doc = this.createPDFDocument();
            
            // 渲染各个部分
            await this.renderTitlePage(doc, data);
            await this.renderExecutiveSummary(doc, data);
            await this.renderStatistics(doc, data);
            await this.renderVulnerabilities(doc, data);
            
            if (this.options.includeCharts) {
                await this.renderCharts(doc, data);
            }
            
            await this.renderFooter(doc, data);
            
            return doc.save(`xuanwu_report_${scanId}_${this.options.template}.pdf`);
        } finally {
            hideGeneratingIndicator();
        }
    }
    
    createPDFDocument() {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF('p', 'mm', 'a4');
        
        // 设置字体
        doc.setFont('helvetica');
        
        return doc;
    }
}

// 导出供外部使用
window.PDFGenerator = PDFGenerator;
```

---

### Phase 2: 模板实现 (Day 3-4)

#### Task 2.1: 实现三种模板引擎
- [ ] `SimpleTemplate` - 简洁版渲染逻辑
- [ ] `DetailedTemplate` - 详细版渲染逻辑（基于现有代码）
- [ ] `ComplianceTemplate` - R155 合规版专用

**代码结构**:
```javascript
// frontend/static/pdf-templates.js

class DetailedTemplate {
    async render(doc, data) {
        // 1. 执行摘要
        await this.renderExecutiveSummary(doc, data);
        
        // 2. 仪表盘统计
        await this.renderDashboard(doc, data);
        
        // 3. 图表区域（4 个图表）
        await this.renderChartsSection(doc, data);
        
        // 4. 完整漏洞列表
        await this.renderFullVulnerabilityTable(doc, data);
        
        // 5. 组件清单
        await this.renderComponents(doc, data);
        
        // 6. R155 合规分析
        await this.renderComplianceAnalysis(doc, data);
        
        // 7. 附录
        await this.renderAppendices(doc, data);
    }
    
    renderChartsSection(doc, data) {
        // 生成 4 个图表的 canvas
        const charts = await this.generateAllCharts(data);
        
        // 分页处理
        let yPos = 50;
        charts.forEach((chart, index) => {
            if (index % 2 === 0 && index > 0) {
                doc.addPage();
                yPos = 20;
            }
            
            doc.addImage(chart, 'PNG', 15, yPos, 90, 60);
            yPos += 65;
        });
    }
}

class ComplianceTemplate {
    async render(doc, data) {
        // 突出显示合规相关章节
        await this.renderComplianceScore(doc, data);
        await this.renderViolationMatrix(doc, data);
        await this.renderRemediationPlan(doc, data);
        // 移除非必要的技术细节
    }
}
```

---

### Phase 3: UI 交互 (Day 5)

#### Task 3.1: 创建选项面板组件
- [ ] HTML 结构实现
- [ ] CSS 样式美化
- [ ] 展开/折叠交互
- [ ] 表单控件绑定

#### Task 3.2: 实现用户操作
- [ ] Logo 上传与预览
- [ ] 水印选择效果
- [ ] 颜色选择器
- [ ] "保存为默认"功能（localStorage）

**代码示例**:
```javascript
// frontend/static/pdf-ui.js

class PDFExportUI {
    constructor() {
        this.initElements();
        this.bindEvents();
        this.loadUserPreferences();
    }
    
    initElements() {
        this.exportBtn = document.getElementById('exportPdfBtn');
        this.optionsPanel = document.getElementById('pdfOptionsPanel');
        this.templateSelect = document.getElementById('templateSelector');
        this.logoInput = document.getElementById('logoUpload');
        this.watermarkSelect = document.getElementById('watermarkSelector');
        this.colorPicker = document.getElementById('brandColorPicker');
        this.generateBtn = document.getElementById('generatePdfCustom');
        this.saveDefaultBtn = document.getElementById('saveAsDefault');
    }
    
    bindEvents() {
        // 点击按钮展开/折叠选项
        this.exportBtn.addEventListener('click', () => {
            this.optionsPanel.style.display = 
                this.optionsPanel.style.display === 'none' ? 'block' : 'none';
        });
        
        // Logo 上传预览
        this.logoInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    this.previewLogo(event.target.result);
                };
                reader.readAsDataURL(file);
            }
        });
        
        // 生成 PDF
        this.generateBtn.addEventListener('click', () => {
            this.generateWithCustomizations();
        });
        
        // 保存默认设置
        this.saveDefaultBtn.addEventListener('click', () => {
            this.saveUserPreferences();
        });
    }
    
    async generateWithCustomizations() {
        const options = {
            template: this.templateSelect.value,
            logoUrl: this.currentLogoUrl,
            watermark: this.watermarkSelect.value,
            brandColor: this.colorPicker.value
        };
        
        const generator = new PDFGenerator(options);
        await generator.generate(currentScanId);
        
        this.optionsPanel.style.display = 'none';
    }
    
    saveUserPreferences() {
        localStorage.setItem('pdfDefaults', JSON.stringify({
            template: this.templateSelect.value,
            watermark: this.watermarkSelect.value,
            brandColor: this.colorPicker.value,
            lastLogoUsed: this.currentLogoUrl
        }));
        
        showToast('✅ 已保存为默认设置');
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    new PDFExportUI();
});
```

---

### Phase 4: 测试与优化 (Day 6-7)

#### Task 4.1: 单元测试
- [ ] PDFGenerator 类方法测试
- [ ] 各模板渲染逻辑测试
- [ ] 水印生成测试
- [ ] Logo 嵌入测试

#### Task 4.2: 集成测试
- [ ] 完整用户流程测试
- [ ] 不同浏览器兼容性
- [ ] 大尺寸报告分页测试
- [ ] 内存泄漏检测

#### Task 4.3: 性能优化
- [ ] 减少图片处理时间
- [ ] 优化 canvas 渲染
- [ ] 压缩输出文件大小
- [ ] 缓存策略实现

---

## 🧪 测试用例

### 测试场景 1: 默认详细模板
```
1. 打开页面 → 点击"导出 PDF"
2. 不修改任何选项，直接点击"生成并下载"
3. 验证：
   ✓ PDF 包含所有区块
   ✓ 4 个图表正确显示
   ✓ 所有漏洞记录在列
   ✓ 文件格式正确
```

### 测试场景 2: 自定义 Logo
```
1. 上传公司 Logo 文件
2. 预览检查尺寸合适
3. 生成 PDF
4. 验证：
   ✓ Logo 出现在页眉
   ✓ 位置居中且清晰
   ✓ 不会遮挡其他内容
   ✓ 打印效果良好
```

### 测试场景 3: 合规模板
```
1. 选择"R155 合规版"模板
2. 不添加其他选项
3. 生成 PDF
4. 验证：
   ✓ 只有合规相关章节
   ✓ 合规得分醒目显示
   ✓ 违规项详细分析
   ✓ 没有多余的技术细节
```

### 测试场景 4: 水印功能
```
1. 选择"机密"水印
2. 生成 PDF
3. 验证：
   ✓ 每页都有半透明水印
   ✓ 文字可读性不受影响
   ✓ 旋转角度美观（通常 45 度）
   ✓ 颜色适中不刺眼
```

### 测试场景 5: 批量长表
```
1. 选择一个有 200+ CVE 的扫描结果
2. 使用详细模板
3. 生成 PDF
4. 验证：
   ✓ 表格正确分页
   ✓ 每页都有表头重复
   ✓ 没有截断的记录
   ✓ 总页数正确
```

---

## 📊 验收标准

### 功能完整性 (Must Have)
- ✅ 三种模板正常工作
- ✅ Logo 上传和嵌入
- ✅ 水印添加功能
- ✅ 品牌色应用
- ✅ 多页长表格正确分页
- ✅ 保持原有 PDF 导出功能

### 质量标准 (Should Have)
- ✅ PDF 文件大小 < 5MB（典型场景）
- ✅ 生成时间 < 10 秒（中等规模数据）
- ✅ 内存占用 < 200MB
- ✅ 所有主流浏览器支持

### 用户体验 (Nice to Have)
- ✅ 选项面板响应流畅
- ✅ Logo 预览即时
- ✅ 进度指示清晰
- ✅ 错误提示友好

---

## 🚀 上线检查清单

- [ ] 代码审查通过
- [ ] 所有测试用例通过
- [ ] 性能基准测试完成
- [ ] 文档更新完成
  - [ ] 用户手册新增 PDF 定制章节
  - [ ] API 文档更新
  - [ ] README 功能亮点更新
- [ ] Release Notes 撰写
- [ ] GitHub Issue 关闭
- [ ] 演示视频录制（可选）

---

## 💡 扩展功能预留

如果时间充裕，可考虑添加：
- [ ] 页面预览功能（生成前查看效果）
- [ ] 模板编辑器和自定义
- [ ] 批量应用同一设置到多个报告
- [ ] 导出设置分享（JSON 配置文件）
- [ ] A/B 测试不同的模板效果

---

## 📝 备注

### 技术依赖
- jsPDF 2.5.1+
- html2canvas 1.4.1+
- Chart.js（已有）

### 已知限制
- Logo 文件大小限制：≤ 2MB
- 水印透明度：固定 30%（后续可调优）
- 颜色自定义：仅限主色调，副色系待扩展

### 注意事项
- 避免过大的 Logo 导致 PDF 体积暴增
- 水印文字长度需控制
- 某些特殊字符需要转义

---

**最后更新**: 2026-08-10  
**负责人**: Jackson8ok  
**预计开始日期**: 待定  
**预计完成日期**: 待定  

下一步：等待确认后创建 GitHub Issues 并开始编码！🚀
