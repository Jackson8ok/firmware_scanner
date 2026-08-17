# 📄 PDF 报告生成使用指南

## ✨ 功能说明

玄武固件安全扫描平台 v2.3 支持自动生成专业的 PDF 安全分析报告，包含：

### 报告内容

1. **封面页**
   - 固件基本信息（名称、类型、大小）
   - R155 合规评分
   - 整体风险等级标识

2. **执行摘要**
   - 漏洞统计（严重/高危/中危/低危）
   - R155 合规状态
   - 关键发现概览

3. **R155 合规评估详情**
   - 总体合规评分
   - 各类别得分对比表
   - 违规项详细说明

4. **CVE 漏洞详情**
   - 按严重程度排序的漏洞列表
   - CVSS 评分
   - 组件信息和受影响范围

5. **修复建议**
   - 针对性的修复方案
   - 通用安全最佳实践

6. **附录：SBOM**
   - 软件物料清单
   - 组件版本和许可证信息

---

## 🔧 API 使用方法

### 1. 下载 PDF 报告

```bash
# 方式 1: 直接下载
curl -o report.pdf http://localhost:8000/api/task/{task_id}/report/pdf

# 方式 2: 使用浏览器访问
http://localhost:8000/api/task/{task_id}/report/pdf
```

**示例：**
```bash
# 获取任务 ID
TASK_ID="abc-123-def"

# 下载报告
curl -o firmware_report.pdf "http://localhost:8000/api/task/${TASK_ID}/report/pdf"

# 查看文件大小
ls -lh firmware_report.pdf
```

### 2. 重新生成报告（可选包含图表）

```bash
curl -X POST "http://localhost:8000/api/task/{task_id}/regenerate-report" \
  -H "Content-Type: application/json" \
  -d '{"include_charts": false}'
```

**注意**: 默认 `include_charts=false`，因为图表功能可能受字体影响。如果需要使用图表，请确保安装了中文字体。

---

## 🖥️ 前端集成示例

### HTML 添加下载按钮

在任务结果页面添加：

```html
<!-- 任务完成后显示 -->
<div id="downloadSection" style="display:none; margin-top: 20px;">
    <button onclick="downloadPDF()" class="btn btn-success">
        📄 下载 PDF 报告
    </button>
    <button onclick="regenerateReport()" class="btn btn-secondary">
        🔄 重新生成报告
    </button>
</div>

<script>
async function downloadPDF() {
    const taskId = currentScanId || urlParams.get('task');
    if (!taskId) return;
    
    // 下载 PDF
    window.open(`/api/task/${taskId}/report/pdf`, '_blank');
}

async function regenerateReport() {
    const taskId = currentScanId || urlParams.get('task');
    if (!taskId) return;
    
    try {
        const response = await fetch(`/api/task/${taskId}/regenerate-report`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({include_charts: false})
        });
        
        const result = await response.json();
        if (result.success) {
            alert('✅ PDF 报告已重新生成！');
            downloadPDF();
        } else {
            alert(`❌ 生成失败：${result.detail}`);
        }
    } catch (error) {
        alert(`❌ 请求失败：${error.message}`);
    }
}
</script>
```

---

## 📊 报告样式自定义

### 修改颜色主题

编辑 `report_generator/pdf_generator.py`：

```python
# 在第 35-50 行修改主色调
self.styles.add(ParagraphStyle(
    name='MainTitle',
    parent=self.styles['Heading1'],
    fontSize=24,
    textColor=colors.HexColor('#FF6B00'),  # 橙色主题
    spaceAfter=12,
    alignment=TA_CENTER
))
```

### 添加公司 Logo

```python
def _create_cover_page(self, scan_result: Dict) -> List:
    story = []
    
    # 添加 Logo
    logo_path = "path/to/logo.png"
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=2*inch, height=1*inch)
        story.append(logo)
        story.append(Spacer(1, 0.3*inch))
    
    # ... 其他内容
```

### 添加水印

```python
from reportlab.platypus import Canvas

def add_watermark(canvas, page_num, total_pages):
    canvas.saveState()
    canvas.setFont('Helvetica', 12)
    canvas.setFillColorRGB(0.9, 0.9, 0.9, alpha=0.5)
    canvas.drawString(100, 400, "CONFIDENTIAL - 内部使用")
    canvas.restoreState()

# 在 doc.build 时添加 callback
doc.build(story, onFirstPage=add_watermark, onLaterPages=add_watermark)
```

---

## 🐛 常见问题排查

### Q1: 中文显示为乱码
**原因**: 缺少中文字体  
**解决**:
```bash
# Ubuntu/Debian
sudo apt-get install fonts-wqy-microhei fonts-wqy-zenhei

# CentOS/RHEL
sudo yum install wenquanyi-fonts

# 或者在代码中使用英文替代
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']  # 使用非中文字体
```

### Q2: 图表生成失败
**原因**: matplotlib 配置问题  
**解决**:
```python
# 临时禁用图表（推荐生产环境）
pdf_path = generate_pdf_report(task_id, result, include_charts=False)

# 或修复 matplotlib 配置
from matplotlib import rcParams
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['DejaVu Sans']
```

### Q3: 报告文件太大 (>10MB)
**优化**:
- 减少图表数量
- 压缩图片质量
- 移除不必要的附录

### Q4: PDF 无法打开或损坏
**检查**:
```bash
# 验证 PDF 格式
pdftk input.pdf dump_data | head -20

# 重新生成
rm input.pdf && python regenerate_script.py
```

---

## 🚀 性能优化建议

### 1. 异步生成报告
```python
@app.post("/api/task/{task_id}/generate-report-async")
async def generate_report_async(task_id: str):
    """后台任务生成报告"""
    task_id = uuid.uuid4()
    asyncio.create_task(generate_pdf_background(task_id))
    return {"task_id": task_id, "status": "generating"}
```

### 2. 缓存已生成的报告
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_report(task_id: str):
    pdf_path = generate_pdf_report(task_id, scan_result)
    return pdf_path
```

### 3. 批量导出多个报告
```bash
# 脚本示例
for task_id in $(cat task_ids.txt); do
    curl -o "${task_id}.pdf" "http://localhost:8000/api/task/${task_id}/report/pdf"
done
```

---

## 📈 报告数据示例

以下是生成 PDF 所需的 `scan_result` 数据结构：

```python
{
    'filename': 'firmware.bin',
    'firmware_type': 'squashfs',
    'file_size': '45.2 MB',
    'compliance_score': 72.5,
    'cves': [
        {
            'cve_id': 'CVE-2024-1234',
            'cvss_score': 9.8,
            'component': 'OpenSSL 1.1.1',
            'description': '缓冲区溢出漏洞...'
        }
    ],
    'category_scores': {
        'Authentication & Access Control': 55.0,
        'Secure Boot': 82.0,
        'Supply Chain Security': 72.5
    },
    'violations': [
        {
            'rule_id': 'R155-A1',
            'cve_id': 'CVE-2024-1234',
            'component': 'OpenSSL',
            'penalty_score': 10
        }
    ],
    'recommendations': [
        '升级到 OpenSSL 3.0',
        '实施代码签名'
    ]
}
```

---

## 🎯 下一步扩展

### 计划中的功能

- [ ] Word 格式报告 (.docx)
- [ ] Excel 漏洞明细表 (.xlsx)
- [ ] HTML 交互式报告
- [ ] 多语言支持（中英文切换）
- [ ] 自定义模板引擎
- [ ] 自动邮件发送报告
- [ ] 报告版本管理和对比
- [ ] 一键分享链接

---

**最后更新**: 2026-08-10  
**版本**: v2.3  
**作者**: 攻城狮阿信
