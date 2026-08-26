"""
报告生成器模块 - 玄武固件安全扫描平台
"""

try:
    from .pdf_generator import PDFReportGenerator, generate_pdf_report
    __all__ = ['PDFReportGenerator', 'generate_pdf_report']
except ImportError:
    # PDF 依赖未安装时使用降级模式
    PDFReportGenerator = None
    generate_pdf_report = None
    __all__ = []
