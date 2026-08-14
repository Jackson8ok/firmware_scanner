"""
PDF 报告生成器 - 玄武固件安全扫描平台
生成专业的 R155 合规审计报告和 CVE 详细报告
"""

import io
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
import matplotlib.pyplot as plt
import numpy as np

# 导入项目模块
try:
    from scanner.task_queue import ScanQueue
except ImportError:
    pass


class PDFReportGenerator:
    """PDF 报告生成器"""
    
    def __init__(self, output_dir: str = "./data/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 样式初始化
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """自定义样式"""
        # 标题样式
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # 副标题样式
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#3949ab'),
            spaceAfter=12,
            alignment=TA_CENTER
        ))
        
        # 小标题样式
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#5c6bc0'),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))
        
        # 正文样式
        self.styles.add(ParagraphStyle(
            name='BodyTextCustom',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            alignment=TA_LEFT
        ))
        
        # 警告样式
        self.styles.add(ParagraphStyle(
            name='Warning',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#d32f2f'),
            fontName='Helvetica-BoldOblique'
        ))
        
        # 成功样式
        self.styles.add(ParagraphStyle(
            name='Success',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#388e3c'),
            fontName='Helvetica-Bold'
        ))

    def generate_full_report(
        self,
        task_id: str,
        scan_result: Dict,
        include_charts: bool = False  # 默认关闭图表，避免字体问题
    ) -> str:
        """
        生成完整的 PDF 报告
        
        Args:
            task_id: 任务 ID
            scan_result: 扫描结果数据
            include_charts: 是否包含图表
            
        Returns:
            PDF 文件路径
        """
        filename = f"scan_report_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = self.output_dir / filename
        
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        # 封面页
        story.extend(self._create_cover_page(scan_result))
        story.append(PageBreak())
        
        # 执行摘要
        story.extend(self._create_executive_summary(scan_result))
        story.append(PageBreak())
        
        # R155 合规评分详情
        story.extend(self._create_r155_compliance_section(scan_result))
        
        if include_charts:
            story.append(PageBreak())
            story.extend(self._create_charts_section(scan_result))
        
        story.append(PageBreak())
        
        # CVE 详细列表
        story.extend(self._create_cve_details_section(scan_result))
        
        story.append(PageBreak())
        
        # 建议措施
        story.extend(self._create_recommendations_section(scan_result))
        
        story.append(PageBreak())
        
        # 附录：SBOM
        if 'sbom' in scan_result and scan_result['sbom']:
            story.extend(self._create_sbom_section(scan_result))
        
        # 页脚信息
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(
            "本报告由 <b>玄武固件安全扫描平台</b> 自动生成",
            self.styles['BodyTextCustom']
        ))
        story.append(Paragraph(
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles['BodyTextCustom']
        ))
        
        doc.build(story)
        
        return str(filepath)

    def _create_cover_page(self, scan_result: Dict) -> List:
        """创建封面页"""
        story = []
        
        # 标题
        story.append(Paragraph("🐢 玄武", self.styles['MainTitle']))
        story.append(Paragraph("固件安全分析报告", self.styles['Subtitle']))
        
        story.append(Spacer(1, 0.5*inch))
        
        # Logo/图标（简化为文字）
        story.append(Paragraph("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", self.styles['BodyTextCustom']))
        story.append(Spacer(1, 0.3*inch))
        
        # 报告信息
        info_data = [
            ["固件名称", scan_result.get('filename', 'N/A')],
            ["固件类型", scan_result.get('firmware_type', 'N/A')],
            ["文件大小", scan_result.get('file_size', 'N/A')],
            ["扫描时间", scan_result.get('scan_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))],
            ["R155 合规评分", f"{scan_result.get('compliance_score', 'N/A')}%"],
        ]
        
        table = Table(info_data, colWidths=[2*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.9, 0.9, 0.9)),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.5*inch))
        
        # 危险等级标识
        compliance_score = scan_result.get('compliance_score', 0)
        if compliance_score < 50:
            level_text = "🔴 高风险"
            level_color = colors.red
        elif compliance_score < 70:
            level_text = "🟡 中等风险"
            level_color = colors.orange
        else:
            level_text = "🟢 低风险"
            level_color = colors.green
        
        story.append(Paragraph(
            f"整体风险等级：<span color='{level_color.hexval()}'>{level_text}</span>",
            self.styles['BodyTextCustom']
        ))
        
        return story

    def _create_executive_summary(self, scan_result: Dict) -> List:
        """创建执行摘要"""
        story = []
        
        story.append(Paragraph("1. 执行摘要", self.styles['SectionHeader']))
        story.append(Spacer(1, 0.2*inch))
        
        # 关键发现
        story.append(Paragraph("<b>关键发现：</b>", self.styles['BodyTextCustom']))
        
        cves = scan_result.get('cves', [])
        critical_cves = [c for c in cves if c.get('cvss_score', 0) >= 9.0]
        high_cves = [c for c in cves if 7.0 <= c.get('cvss_score', 0) < 9.0]
        
        summary_points = [
            f"• 共发现 {len(cves)} 个已知漏洞",
        ]
        
        if critical_cves:
            summary_points.append(f"• <span color='red'>⚠️ {len(critical_cves)} 个严重漏洞 (CVSS ≥ 9.0)</span>")
        if high_cves:
            summary_points.append(f"• <span color='orange'>⚠️ {len(high_cves)} 个高危漏洞 (CVSS 7.0-8.9)</span>")
        
        # R155 合规状态
        compliance_score = scan_result.get('compliance_score', 0)
        violating_cves = scan_result.get('violating_cves', [])
        
        # 兼容列表和数字两种格式
        if isinstance(violating_cves, list):
            violations = len(violating_cves)
        elif isinstance(violating_cves, (int, float)):
            violations = int(violating_cves)
        else:
            violations = 0
        
        if compliance_score >= 80:
            status_text = "✅ 基本符合 R155 要求"
        elif compliance_score >= 60:
            status_text = "⚠️ 需要部分改进"
        else:
            status_text = "❌ 不符合 R155 要求"
        
        summary_points.append(f"• R155 合规评分：{compliance_score}% - {status_text}")
        summary_points.append(f"• 发现 {violations} 个合规违规项")
        
        for point in summary_points:
            story.append(Paragraph(point, self.styles['BodyTextCustom']))
        
        return story

    def _create_r155_compliance_section(self, scan_result: Dict) -> List:
        """创建 R155 合规章节"""
        story = []
        
        story.append(Paragraph("2. R155 合规评估详情", self.styles['SectionHeader']))
        story.append(Spacer(1, 0.2*inch))
        
        # 总体评分
        story.append(Paragraph("<b>总体合规评分：</b>", self.styles['BodyTextCustom']))
        
        score = scan_result.get('compliance_score', 0)
        score_bar = self._create_score_bar(score)
        story.append(score_bar)
        story.append(Spacer(1, 0.3*inch))
        
        # 类别得分表格
        category_scores = scan_result.get('category_scores', {})
        if category_scores:
            story.append(Paragraph("<b>各分类得分：</b>", self.styles['BodyTextCustom']))
            
            data = [['分类', '得分', '评级']]
            for cat, sc in category_scores.items():
                rating = '优秀' if sc >= 80 else ('良好' if sc >= 60 else ('需改进' if sc >= 40 else '较差'))
                data.append([cat[:30] + '...' if len(cat) > 30 else cat, f"{sc:.1f}%", rating])
            
            table = Table(data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.8)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.3*inch))
        
        # 违规详情
        violations = scan_result.get('violations', [])
        if violations:
            story.append(Paragraph("<b>违规项详情：</b>", self.styles['BodyTextCustom']))
            
            for i, v in enumerate(violations[:10], 1):  # 最多显示 10 条
                story.append(Paragraph(
                    f"{i}. <b>{v.get('rule_id', 'N/A')}</b>: {v.get('cve_id', 'N/A')} - "
                    f"{v.get('component', 'N/A')} (扣分：{v.get('penalty_score', 0)})",
                    self.styles['BodyTextCustom']
                ))
            
            if len(violations) > 10:
                story.append(Paragraph(
                    f"... 还有 {len(violations) - 10} 个违规项",
                    self.styles['Warning']
                ))
        
        return story

    def _create_score_bar(self, score: float) -> Paragraph:
        """创建评分进度条"""
        # 计算颜色
        if score >= 80:
            color = '#4caf50'  # 绿色
        elif score >= 60:
            color = '#ff9800'  # 橙色
        else:
            color = '#f44336'  # 红色
        
        bar_html = f'''
        <table border="0" cellpadding="0" cellspacing="0">
            <tr>
                <td width="{score}%" bgcolor="{color}" height="20"></td>
                <td width="{100-score}%" bgcolor="#e0e0e0" height="20"></td>
            </tr>
            <tr>
                <td colspan="2" align="center"><font size="3"><b>{score:.1f}%</b></font></td>
            </tr>
        </table>
        '''
        return Paragraph(bar_html, self.styles['Normal'])

    def _create_charts_section(self, scan_result: Dict) -> List:
        """创建图表章节"""
        story = []
        
        story.append(Paragraph("3. 数据可视化", self.styles['SectionHeader']))
        story.append(Spacer(1, 0.2*inch))
        
        # 创建饼图
        category_scores = scan_result.get('category_scores', {})
        if category_scores:
            story.append(Paragraph("<b>R155 分类得分分布：</b>", self.styles['BodyTextCustom']))
            story.append(Spacer(1, 0.2*inch))
            
            # 使用 matplotlib 创建饼图
            chart_path = self._create_pie_chart(category_scores)
            if chart_path:
                try:
                    img = Image(chart_path, width=4*inch, height=3*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.3*inch))
                    # 删除临时图片
                    os.remove(chart_path)
                except Exception as e:
                    story.append(Paragraph(f"图表生成失败：{e}", self.styles['Warning']))
        
        # 创建雷达图（如果数据足够）
        if len(category_scores) >= 3:
            story.append(Paragraph("<b>R155 能力雷达图：</b>", self.styles['BodyTextCustom']))
            story.append(Spacer(1, 0.2*inch))
            
            chart_path = self._create_radar_chart(category_scores)
            if chart_path:
                try:
                    img = Image(chart_path, width=4*inch, height=3*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.3*inch))
                    os.remove(chart_path)
                except Exception as e:
                    story.append(Paragraph(f"图表生成失败：{e}", self.styles['Warning']))
        
        return story

    def _create_pie_chart(self, data: Dict) -> Optional[str]:
        """创建饼图"""
        try:
            # 设置中文字体（避免乱码）
            import matplotlib.pyplot as plt
            from matplotlib import rcParams
            
            # 尝试使用中文字体
            try:
                rcParams['font.family'] = 'sans-serif'
                rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS', 'SimHei', 'WenQuanYi Micro Hei']
                rcParams['axes.unicode_minus'] = False
            except:
                pass
            
            labels = list(data.keys())[:5]  # 最多 5 个分类
            values = [data[l] for l in labels]
            
            fig, ax = plt.subplots(figsize=(6, 6))
            colors_map = ['#4caf50', '#ff9800', '#f44336', '#2196f3', '#9c27b0']
            wedges, texts, autotexts = ax.pie(
                values, 
                labels=labels, 
                autopct='%1.1f%%',
                colors=colors_map[:len(labels)]
            )
            ax.set_title('R155 分类得分分布', fontsize=12)
            plt.tight_layout()
            
            # 使用绝对路径
            temp_path = str((self.output_dir / f"pie_chart_{datetime.now().timestamp()}.png").resolve())
            plt.savefig(temp_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            
            return temp_path
        except Exception as e:
            print(f"饼图生成失败：{e}")
            return None

    def _create_radar_chart(self, data: Dict) -> Optional[str]:
        """创建雷达图"""
        try:
            import numpy as np
            import matplotlib.pyplot as plt
            from matplotlib import rcParams
            
            # 尝试使用中文字体
            try:
                rcParams['font.family'] = 'sans-serif'
                rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS', 'SimHei', 'WenQuanYi Micro Hei']
                rcParams['axes.unicode_minus'] = False
            except:
                pass
            
            categories = list(data.keys())
            values = list(data.values())
            
            angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
            values += values[:1]
            angles += angles[:1]
            
            fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
            ax.plot(angles, values, 'o-', linewidth=2, color='#1a237e')
            ax.fill(angles, values, alpha=0.25, color='#1a237e')
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, fontsize=8)
            ax.set_ylim(0, 100)
            ax.set_title('R155 能力雷达图', fontsize=12, pad=20)
            plt.tight_layout()
            
            # 使用绝对路径
            temp_path = str((self.output_dir / f"radar_chart_{datetime.now().timestamp()}.png").resolve())
            plt.savefig(temp_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            
            return temp_path
        except Exception as e:
            print(f"雷达图生成失败：{e}")
            return None

    def _create_cve_details_section(self, scan_result: Dict) -> List:
        """创建 CVE 详细列表"""
        story = []
        
        story.append(Paragraph("4. CVE 漏洞详情", self.styles['SectionHeader']))
        story.append(Spacer(1, 0.2*inch))
        
        cves = scan_result.get('cves', [])
        if not cves:
            story.append(Paragraph("✅ 未发现已知漏洞", self.styles['Success']))
            return story
        
        # 按严重程度排序
        sorted_cves = sorted(cves, key=lambda x: x.get('cvss_score', 0), reverse=True)
        
        # CVE 表格
        data = [['CVE ID', '组件', 'CVSS', '描述']]
        for cve in sorted_cves[:15]:  # 最多显示 15 条
            cvss = cve.get('cvss_score', 0)
            severity = '🔴 严重' if cvss >= 9.0 else ('🟠 高危' if cvss >= 7.0 else ('🟡 中危' if cvss >= 4.0 else '🟢 低危'))
            
            desc = cve.get('description', '')[:50] + '...' if len(cve.get('description', '')) > 50 else cve.get('description', '')
            
            data.append([
                cve.get('cve_id', 'N/A'),
                cve.get('component', 'N/A')[:20],
                f"{cvss} {severity}",
                desc
            ])
        
        table = Table(data, colWidths=[1.5*inch, 2*inch, 1*inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.8)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        story.append(table)
        
        if len(cves) > 15:
            story.append(Paragraph(
                f"注：仅显示前 15 条，共 {len(cves)} 个漏洞",
                self.styles['Warning']
            ))
        
        return story

    def _create_recommendations_section(self, scan_result: Dict) -> List:
        """创建建议措施"""
        story = []
        
        story.append(Paragraph("5. 修复建议", self.styles['SectionHeader']))
        story.append(Spacer(1, 0.2*inch))
        
        recommendations = scan_result.get('recommendations', [])
        if recommendations:
            for i, rec in enumerate(recommendations[:5], 1):
                story.append(Paragraph(
                    f"{i}. {rec}",
                    self.styles['BodyTextCustom']
                ))
        else:
            story.append(Paragraph("暂无特定建议", self.styles['BodyTextCustom']))
        
        # 通用建议
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("<b>通用安全建议：</b>", self.styles['BodyTextCustom']))
        general_recs = [
            "• 定期更新固件依赖库",
            "• 启用安全启动和签名验证",
            "• 实施最小权限原则",
            "• 定期进行安全审计",
            "• 建立漏洞响应机制"
        ]
        
        for rec in general_recs:
            story.append(Paragraph(rec, self.styles['BodyTextCustom']))
        
        return story

    def _create_sbom_section(self, scan_result: Dict) -> List:
        """创建 SBOM 附录"""
        story = []
        
        story.append(Paragraph("附录 A: 软件物料清单 (SBOM)", self.styles['SectionHeader']))
        story.append(Spacer(1, 0.2*inch))
        
        sbom = scan_result.get('sbom', {})
        components = sbom.get('components', [])
        
        if components:
            story.append(Paragraph(f"共识别 {len(components)} 个软件组件", self.styles['BodyTextCustom']))
            story.append(Spacer(1, 0.2*inch))
            
            # 组件列表
            data = [['组件名', '版本', '许可证']]
            for comp in components[:20]:  # 最多显示 20 个
                data.append([
                    comp.get('name', 'N/A')[:25],
                    comp.get('version', 'N/A'),
                    comp.get('license', 'Unknown')
                ])
            
            table = Table(data, colWidths=[2.5*inch, 2*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.8)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            
            story.append(table)
            
            if len(components) > 20:
                story.append(Paragraph(
                    f"注：仅显示前 20 个组件，共 {len(components)} 个",
                    self.styles['Warning']
                ))
        else:
            story.append(Paragraph("未检测到软件组件", self.styles['BodyTextCustom']))
        
        return story


def generate_pdf_report(task_id: str, scan_result: Dict) -> str:
    """便捷函数：生成 PDF 报告"""
    generator = PDFReportGenerator()
    return generator.generate_full_report(task_id, scan_result)


if __name__ == "__main__":
    # 测试代码
    test_result = {
        'filename': 'test_firmware.bin',
        'firmware_type': 'squashfs',
        'file_size': '45.2 MB',
        'compliance_score': 68.5,
        'cves': [
            {'cve_id': 'CVE-2021-44228', 'cvss_score': 10.0, 'component': 'Apache Log4j', 'description': 'Log4Shell 远程代码执行漏洞'},
            {'cve_id': 'CVE-2021-3156', 'cvss_score': 8.8, 'component': 'sudo', 'description': '堆缓冲区溢出漏洞'}
        ],
        'category_scores': {
            'Authentication & Access Control': 55.0,
            'Secure Boot': 82.0,
            'Supply Chain Security': 72.5,
            'Vulnerability Management': 60.0,
            'Encryption': 75.0
        },
        'violating_cves': 2,
        'recommendations': ['升级到 Apache Log4j 2.17.0 或更高版本', '更新 sudo 到最新补丁版本']
    }
    
    pdf_path = generate_pdf_report('test_001', test_result)
    print(f"PDF 报告已生成：{pdf_path}")
