/**
 * 固件漏洞扫描平台 - Node.js 报告生成服务
 * 支持 Word (docx) 和 PPT (pptx) 格式导出
 */

const express = require('express');
const cors = require('cors');
const fs = require('fs-extra');
const path = require('path');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType } = require('docx');
const PptxGenJS = require('pptxgenjs');

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json({ limit: '50mb' }));

// 确保输出目录存在
const reportsDir = path.join(__dirname, '../../reports');
fs.ensureDirSync(reportsDir);

/**
 * 生成 Word 报告
 */
app.post('/api/report/word', async (req, res) => {
    try {
        const { firmware_id, data } = req.body;
        
        if (!data || !data.vulnerabilities) {
            return res.status(400).json({ error: '无效的数据' });
        }
        
        const doc = new Document({
            sections: [{
                properties: {},
                children: [
                    // 标题
                    new Paragraph({
                        text: '固件漏洞扫描报告',
                        heading: 'Heading1',
                        alignment: AlignmentType.CENTER,
                        spacing: { before: 0, after: 200 }
                    }),
                    
                    // 基本信息
                    new Paragraph({
                        text: `固件 ID: ${firmware_id}`,
                        style: 'Normal',
                        spacing: { before: 100, after: 100 }
                    }),
                    new Paragraph({
                        text: `扫描时间: ${new Date(data.scan_time).toLocaleString('zh-CN')}`,
                        style: 'Normal'
                    }),
                    new Paragraph({ text: '' }),
                    
                    // 统计摘要
                    new Paragraph({
                        text: '漏洞统计',
                        heading: 'Heading2',
                        spacing: { before: 200, after: 100 }
                    }),
                    new Paragraph({
                        children: [
                            new TextRun(`总漏洞数: ${data.total_cves} | `),
                            new TextRun({ text: `严重: ${data.critical_count}`, color: 'DC3545', bold: true }),
                            new TextRun(` | `),
                            new TextRun({ text: `高危: ${data.high_count}`, color: 'FD7E14', bold: true }),
                            new TextRun(` | 中危: ${data.medium_count} | 低危: ${data.low_count}`),
                            new TextRun(` | R155 不合规: ${data.r155_non_compliant}`)
                        ]
                    }),
                    new Paragraph({ text: '' }),
                    
                    // 漏洞表格
                    new Paragraph({
                        text: '漏洞详情',
                        heading: 'Heading2',
                        spacing: { before: 200, after: 100 }
                    }),
                    createVulnerabilityTable(data.vulnerabilities)
                ]
            }]
        });
        
        const buffer = await Packer.toBuffer(doc);
        const outputPath = path.join(reportsDir, `${firmware_id}_report.docx`);
        await fs.writeFile(outputPath, buffer);
        
        res.json({ 
            success: true, 
            path: outputPath,
            filename: `${firmware_id}_report.docx`
        });
        
    } catch (error) {
        console.error('Word 报告生成失败:', error);
        res.status(500).json({ error: error.message });
    }
});

/**
 * 创建漏洞表格（Word）
 */
function createVulnerabilityTable(vulnerabilities) {
    const headerRow = new TableRow({
        children: ['CVE ID', '组件', '版本', '严重程度', 'CVSS', '优先级', '描述'].map(text =>
            new TableCell({
                children: [new Paragraph({ text, bold: true })],
                width: { size: 100 / 7, type: WidthType.PERCENTAGE },
            })
        ),
    });
    
    const tableRows = vulnerabilities.slice(0, 50).map(vuln => 
        new TableRow({
            children: [
                new TableCell({ children: [new Paragraph(vuln.cve_id)] }),
                new TableCell({ children: [new Paragraph(vuln.component)] }),
                new TableCell({ children: [new Paragraph(vuln.version)] }),
                new TableCell({ 
                    children: [new Paragraph({
                        text: vuln.severity,
                        color: getSeverityColor(vuln.severity)
                    })] 
                }),
                new TableCell({ children: [new Paragraph(vuln.cvss_score.toFixed(1))] }),
                new TableCell({ children: [new Paragraph(vuln.priority_score.toFixed(3))] }),
                new TableCell({ 
                    children: [new Paragraph({
                        text: vuln.description ? vuln.description.substring(0, 100) + '...' : '',
                        wrapRight: true
                    })] 
                }),
            ],
        })
    );
    
    return new Paragraph({
        children: [
            new Table({
                rows: [headerRow, ...tableRows],
                width: { size: 100, type: WidthType.PERCENTAGE },
            })
        ]
    });
}

function getSeverityColor(severity) {
    const colors = {
        critical: 'DC3545',
        high: 'FD7E14',
        medium: 'FFC72C',
        low: '28A745'
    };
    return colors[severity.toLowerCase()] || '000000';
}

/**
 * 生成 PPT 报告
 */
app.post('/api/report/ppt', async (req, res) => {
    try {
        const { firmware_id, data } = req.body;
        
        if (!data || !data.vulnerabilities) {
            return res.status(400).json({ error: '无效的数据' });
        }
        
        const pptx = new PptxGenJS();
        
        // 封面页
        let slide = pptx.addSlide();
        slide.addText('固件漏洞扫描报告', { 
            x: 1, y: 2, w: '80%', h: 1, 
            fontSize: 36, bold: true, 
            align: 'center', color: '667eea' 
        });
        slide.addText(`固件：${firmware_id}`, { 
            x: 1, y: 3.5, w: '80%', h: 0.5, 
            fontSize: 18, align: 'center' 
        });
        slide.addText(`扫描时间：${new Date(data.scan_time).toLocaleString('zh-CN')}`, { 
            x: 1, y: 4.2, w: '80%', h: 0.5, 
            fontSize: 14, align: 'center' 
        });
        
        // 统计页
        slide = pptx.addSlide();
        slide.addText('漏洞统计概览', { 
            x: 0.5, y: 0.3, w: '90%', h: 0.6, 
            fontSize: 24, bold: true, color: '333333' 
        });
        
        const stats = [
            { label: '总漏洞数', value: data.total_cves, color: '667eea' },
            { label: '严重', value: data.critical_count, color: 'dc3545' },
            { label: '高危', value: data.high_count, color: 'fd7e14' },
            { label: '中危', value: data.medium_count, color: 'ffc107' },
            { label: '低危', value: data.low_count, color: '28a745' },
            { label: 'R155 不合规', value: data.r155_non_compliant, color: 'e83e8c' }
        ];
        
        stats.forEach((stat, idx) => {
            const row = 1.5 + Math.floor(idx / 3) * 1.2;
            const col = (idx % 3) * 3 + 0.5;
            
            slide.addShape(pptx.ShapeType.rect, {
                x: col, y: row, w: 2.5, h: 0.8,
                fill: { color: stat.color.replace('#', ''), transparency: 80 },
                line: { color: stat.color, width: 1 }
            });
            
            slide.addText(stat.label, {
                x: col, y: row + 0.2, w: 2.5, h: 0.3,
                fontSize: 12, align: 'center', color: '333333'
            });
            
            slide.addText(String(stat.value), {
                x: col, y: row + 0.45, w: 2.5, h: 0.4,
                fontSize: 20, bold: true, align: 'center', color: stat.color
            });
        });
        
        // Top 10 漏洞页
        if (data.vulnerabilities.length > 0) {
            slide = pptx.addSlide();
            slide.addText('Top 10 高优先级漏洞', { 
                x: 0.5, y: 0.3, w: '90%', h: 0.6, 
                fontSize: 24, bold: true, color: '333333' 
            });
            
            const top10 = data.vulnerabilities.slice(0, 10);
            let yPos = 1.2;
            
            top10.forEach((vuln, idx) => {
                slide.addText(`${idx + 1}. ${vuln.cve_id}`, {
                    x: 0.5, y: yPos, w: 3, h: 0.4,
                    fontSize: 12, bold: true, color: '333333'
                });
                
                slide.addText(`优先级: ${vuln.priority_score.toFixed(3)} | CVSS: ${vuln.cvss_score}`, {
                    x: 3.8, y: yPos, w: 3.5, h: 0.4,
                    fontSize: 10, color: getSeverityColorHex(vuln.severity)
                });
                
                yPos += 0.45;
            });
        }
        
        const outputPath = path.join(reportsDir, `${firmware_id}_report.pptx`);
        await pptx.writeFile({ fileName: outputPath });
        
        res.json({ 
            success: true, 
            path: outputPath,
            filename: `${firmware_id}_report.pptx`
        });
        
    } catch (error) {
        console.error('PPT 报告生成失败:', error);
        res.status(500).json({ error: error.message });
    }
});

function getSeverityColorHex(severity) {
    const colors = {
        critical: 'dc3545',
        high: 'fd7e14',
        medium: 'ffc107',
        low: '28a745'
    };
    return colors[severity.toLowerCase()] || '333333';
}

// 健康检查
app.get('/health', (req, res) => {
    res.json({ status: 'ok', service: 'report-generator' });
});

// 启动服务
app.listen(PORT, () => {
    console.log(`🚀 报告生成服务已启动：http://localhost:${PORT}`);
});
