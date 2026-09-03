"""
模板报告生成器 - v2.6.0 新特性

基于 Jinja2 模板引擎，支持客户自定义报告格式
支持 3+ 预设模板（简版/标准/详细）
支持 HTML/PDF/JSON 导出

使用方式:
    generator = TemplateReportGenerator()
    generator.set_template("standard")
    html = generator.generate_html(scan_result)
    pdf = generator.generate_pdf(scan_result)
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    print("⚠️ Jinja2 未安装，请运行：pip install jinja2")

try:
    from .pdf_generator import PDFReportGenerator
    PDF_AVAILABLE = True
except ImportError:
    PDFReportGenerator = None
    PDF_AVAILABLE = False


class TemplateType(Enum):
    """报告模板类型"""
    SIMPLE = "simple"          # 简版 - 仅关键 CVE
    STANDARD = "standard"      # 标准版 - 完整 CVE 列表
    DETAILED = "detailed"      # 详细版 - 含建议 + 图表
    EXECUTIVE = "executive"    # 高管版 - 摘要 + 风险评分
    TECHNICAL = "technical"    # 技术版 - 完整技术细节


@dataclass
class ScanResult:
    """扫描结果数据结构"""
    task_id: str
    firmware_name: str
    firmware_hash: str
    scan_date: str
    duration: float
    total_components: int
    total_vulns: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    cvss_avg: Optional[float]
    epss_avg: Optional[float]
    vulnerabilities: List[Dict[str, Any]]
    components: List[Dict[str, Any]]


@dataclass
class TemplateConfig:
    """模板配置"""
    name: str
    display_name: str
    description: str
    format: str  # html, pdf, json
    sections: List[str]
    filters: Dict[str, Any]
    include_charts: bool = False
    include_recommendations: bool = False
    min_severity: str = "Low"


class TemplateReportGenerator:
    """模板报告生成器（v2.6.0）"""
    
    def __init__(self, templates_dir: str = "./report_generator/templates"):
        """
        初始化模板报告生成器
        
        Args:
            templates_dir: 模板目录路径
        """
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前模板配置
        self.current_template: Optional[TemplateConfig] = None
        self.current_template_name: str = "standard"
        
        # PDF 生成器（用于 PDF 导出）
        if PDF_AVAILABLE:
            self.pdf_generator = PDFReportGenerator()
        else:
            self.pdf_generator = None
        
        # 初始化 Jinja2 环境
        if JINJA2_AVAILABLE:
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
        else:
            self.jinja_env = None
        
        # 加载预设模板配置
        self.template_configs = self._load_preset_templates()
        
        # 设置默认模板
        self.set_template("standard")
        
        print(f"✅ TemplateReportGenerator 初始化完成")
        print(f"   - 模板目录：{self.templates_dir}")
        print(f"   - 可用模板：{list(self.template_configs.keys())}")
        print(f"   - 默认模板：{self.current_template_name}")
    
    def _load_preset_templates(self) -> Dict[str, TemplateConfig]:
        """加载预设模板配置"""
        return {
            "simple": TemplateConfig(
                name="simple",
                display_name="简版报告",
                description="仅关键 CVE 摘要，适合快速浏览",
                format="html",
                sections=["summary", "critical_vulns"],
                filters={"min_severity": "High", "limit": 50},
                include_charts=False,
                include_recommendations=False
            ),
            "standard": TemplateConfig(
                name="standard",
                display_name="标准报告",
                description="完整 CVE 列表，适合技术团队",
                format="html",
                sections=["summary", "all_vulns", "components"],
                filters={"min_severity": "Low"},
                include_charts=True,
                include_recommendations=False
            ),
            "detailed": TemplateConfig(
                name="detailed",
                display_name="详细报告",
                description="含修复建议 + 统计图表，适合审计",
                format="html",
                sections=["summary", "all_vulns", "components", "charts", "recommendations"],
                filters={"min_severity": "Low"},
                include_charts=True,
                include_recommendations=True
            ),
            "executive": TemplateConfig(
                name="executive",
                display_name="高管摘要",
                description="风险评分 + 关键发现，适合管理层",
                format="html",
                sections=["executive_summary", "risk_score", "top_10_vulns"],
                filters={"min_severity": "Critical", "limit": 10},
                include_charts=True,
                include_recommendations=True
            ),
            "technical": TemplateConfig(
                name="technical",
                display_name="技术报告",
                description="完整技术细节 + PoC，适合安全团队",
                format="html",
                sections=["summary", "all_vulns", "components", "technical_details", "poc"],
                filters={"min_severity": "Low"},
                include_charts=False,
                include_recommendations=False
            ),
            "json": TemplateConfig(
                name="json",
                display_name="JSON 数据",
                description="原始 JSON 数据，适合机器处理",
                format="json",
                sections=["all_data"],
                filters={},
                include_charts=False,
                include_recommendations=False
            )
        }
    
    def set_template(self, template_name: str):
        """
        设置当前使用的模板
        
        Args:
            template_name: 模板名称（simple/standard/detailed/executive/technical/json）
        """
        if template_name not in self.template_configs:
            raise ValueError(f"未知模板：{template_name}，可用：{list(self.template_configs.keys())}")
        
        self.current_template_name = template_name
        self.current_template = self.template_configs[template_name]
        print(f"📋 已切换模板：{self.current_template.display_name}")
    
    def _filter_vulns(self, vulns: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
        """根据过滤器筛选漏洞"""
        severity_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "Unknown": 0}
        min_severity = filters.get("min_severity", "Low")
        min_level = severity_order.get(min_severity, 0)
        
        filtered = []
        for vuln in vulns:
            vuln_severity = vuln.get("severity", "Unknown")
            if severity_order.get(vuln_severity, 0) >= min_level:
                filtered.append(vuln)
        
        # 限制数量
        if "limit" in filters:
            filtered = filtered[:filters["limit"]]
        
        return filtered
    
    def _calculate_risk_score(self, scan_result: ScanResult) -> float:
        """计算风险评分（0-100）"""
        # 简化算法：基于 CVE 数量和严重性
        score = 0
        score += scan_result.critical_count * 10
        score += scan_result.high_count * 5
        score += scan_result.medium_count * 2
        score += scan_result.low_count * 0.5
        
        # 归一化到 0-100
        score = min(100, score)
        return round(score, 1)
    
    def _prepare_context(self, scan_result: ScanResult) -> Dict[str, Any]:
        """准备模板上下文"""
        # 筛选漏洞
        filtered_vulns = self._filter_vulns(
            scan_result.vulnerabilities,
            self.current_template.filters
        )
        
        # 统计数据
        severity_stats = {
            "Critical": scan_result.critical_count,
            "High": scan_result.high_count,
            "Medium": scan_result.medium_count,
            "Low": scan_result.low_count
        }
        
        # 风险评分
        risk_score = self._calculate_risk_score(scan_result)
        
        # 修复建议
        recommendations = []
        if self.current_template.include_recommendations:
            if scan_result.critical_count > 0:
                recommendations.append("🔴 立即修复 {scan_result.critical_count} 个严重漏洞")
            if scan_result.high_count > 0:
                recommendations.append("🟠 优先修复 {scan_result.high_count} 个高危漏洞")
            if scan_result.cvss_avg and scan_result.cvss_avg > 7.0:
                recommendations.append("⚠️ 平均 CVSS 评分较高 ({scan_result.cvss_avg})，建议全面审查")
        
        context = {
            "scan": scan_result,
            "vulns": filtered_vulns,
            "severity_stats": severity_stats,
            "risk_score": risk_score,
            "recommendations": recommendations,
            "template": self.current_template,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "v2.6.0"
        }
        
        return context
    
    def generate_html(self, scan_result: ScanResult) -> str:
        """
        生成 HTML 报告
        
        Args:
            scan_result: 扫描结果
        
        Returns:
            HTML 字符串
        """
        if not JINJA2_AVAILABLE:
            raise RuntimeError("Jinja2 未安装，无法生成 HTML 报告")
        
        if not self.jinja_env:
            raise RuntimeError("Jinja2 环境未初始化")
        
        # 加载模板
        template_file = f"{self.current_template_name}.html"
        try:
            template = self.jinja_env.get_template(template_file)
        except Exception:
            # 如果模板不存在，使用默认模板
            print(f"⚠️ 模板 {template_file} 不存在，使用默认模板")
            template = self._get_default_template()
        
        # 准备上下文
        context = self._prepare_context(scan_result)
        
        # 渲染
        html = template.render(**context)
        return html
    
    def generate_pdf(self, scan_result: ScanResult, output_path: Optional[str] = None) -> bytes:
        """
        生成 PDF 报告
        
        Args:
            scan_result: 扫描结果
            output_path: 输出路径（可选）
        
        Returns:
            PDF 二进制数据
        """
        if not PDF_AVAILABLE:
            raise RuntimeError("PDF 生成依赖未安装，无法生成 PDF 报告")
        
        if not self.pdf_generator:
            raise RuntimeError("PDF 生成器未初始化")
        
        # 使用现有 PDF 生成器
        # TODO: 集成模板系统
        pdf_bytes = self.pdf_generator.generate_full_report(
            scan_result.task_id,
            scan_result.firmware_name,
            scan_result.vulnerabilities
        )
        
        if output_path:
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)
        
        return pdf_bytes
    
    def generate_json(self, scan_result: ScanResult, pretty: bool = True) -> str:
        """
        生成 JSON 报告
        
        Args:
            scan_result: 扫描结果
            pretty: 是否格式化
        
        Returns:
            JSON 字符串
        """
        data = {
            "version": "2.6.0",
            "template": self.current_template_name,
            "generated_at": datetime.now().isoformat(),
            "scan_result": asdict(scan_result),
            "filtered_vulns": self._filter_vulns(
                scan_result.vulnerabilities,
                self.current_template.filters
            ),
            "risk_score": self._calculate_risk_score(scan_result),
            "statistics": {
                "severity": {
                    "Critical": scan_result.critical_count,
                    "High": scan_result.high_count,
                    "Medium": scan_result.medium_count,
                    "Low": scan_result.low_count
                },
                "total_vulns": scan_result.total_vulns,
                "total_components": scan_result.total_components,
                "cvss_avg": scan_result.cvss_avg,
                "epss_avg": scan_result.epss_avg
            }
        }
        
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(data, ensure_ascii=False)
    
    def generate(self, scan_result: ScanResult, output_format: Optional[str] = None, 
                 output_path: Optional[str] = None) -> Any:
        """
        通用报告生成接口
        
        Args:
            scan_result: 扫描结果
            output_format: 输出格式（html/pdf/json），为 None 时使用模板默认格式
            output_path: 输出路径（可选）
        
        Returns:
            报告内容（str 或 bytes）
        """
        fmt = output_format or self.current_template.format
        
        if fmt == "html":
            content = self.generate_html(scan_result)
            if output_path:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
            return content
        
        elif fmt == "pdf":
            content = self.generate_pdf(scan_result, output_path)
            return content
        
        elif fmt == "json":
            content = self.generate_json(scan_result)
            if output_path:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
            return content
        
        else:
            raise ValueError(f"不支持的格式：{fmt}")
    
    def _get_default_template(self):
        """获取默认 HTML 模板（内嵌）"""
        from jinja2 import Template
        
        default_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>玄武·AFVS 扫描报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #1a237e; }
        .summary { background: #f5f5f5; padding: 20px; border-radius: 8px; }
        .vuln { border: 1px solid #ddd; padding: 10px; margin: 10px 0; }
        .critical { border-left: 4px solid #d32f2f; }
        .high { border-left: 4px solid #f57c00; }
        .medium { border-left: 4px solid #fbc02d; }
        .low { border-left: 4px solid #388e3c; }
    </style>
</head>
<body>
    <h1>🐢 玄武·AFVS 扫描报告</h1>
    <div class="summary">
        <h2>摘要</h2>
        <p><strong>固件:</strong> {{ scan.firmware_name }}</p>
        <p><strong>扫描时间:</strong> {{ scan.scan_date }}</p>
        <p><strong>总漏洞数:</strong> {{ scan.total_vulns }}</p>
        <p><strong>风险评分:</strong> {{ risk_score }}/100</p>
    </div>
    
    <h2>漏洞列表</h2>
    {% for vuln in vulns %}
    <div class="vuln {{ vuln.severity|lower }}">
        <h3>{{ vuln.cve_id }} ({{ vuln.severity }})</h3>
        <p><strong>组件:</strong> {{ vuln.component_name }} {{ vuln.component_version }}</p>
        <p><strong>CVSS:</strong> {{ vuln.cvss_score or 'N/A' }}</p>
        <p><strong>EPSS:</strong> {{ vuln.epss_score or 'N/A' }}</p>
        <p>{{ vuln.description }}</p>
    </div>
    {% endfor %}
    
    <footer>
        <p>生成时间：{{ generated_at }} | AFVS v{{ version }}</p>
    </footer>
</body>
</html>
        """
        
        return Template(default_html)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有可用模板"""
        return [
            {
                "name": config.name,
                "display_name": config.display_name,
                "description": config.description,
                "format": config.format
            }
            for config in self.template_configs.values()
        ]
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """获取模板详细信息"""
        if template_name not in self.template_configs:
            raise ValueError(f"未知模板：{template_name}")
        
        config = self.template_configs[template_name]
        return {
            "name": config.name,
            "display_name": config.display_name,
            "description": config.description,
            "format": config.format,
            "sections": config.sections,
            "filters": config.filters,
            "include_charts": config.include_charts,
            "include_recommendations": config.include_recommendations
        }


# 便捷函数
def generate_report(scan_result: ScanResult, template: str = "standard", 
                    format: str = "html", output_path: Optional[str] = None) -> Any:
    """
    便捷函数：生成报告
    
    Args:
        scan_result: 扫描结果
        template: 模板名称（simple/standard/detailed/executive/technical/json）
        format: 输出格式（html/pdf/json）
        output_path: 输出路径（可选）
    
    Returns:
        报告内容
    """
    generator = TemplateReportGenerator()
    generator.set_template(template)
    return generator.generate(scan_result, output_format=format, output_path=output_path)
