"""
报告模板 API - v2.6.0 新特性 (FastAPI 版本)

提供 REST API 端点用于生成和管理报告模板

端点:
    GET  /api/reports/templates          - 列出所有可用模板
    GET  /api/reports/templates/:name    - 获取模板详情
    POST /api/reports/generate           - 生成报告 (支持模板选择)
    GET  /api/reports/:task_id/download - 下载指定格式报告
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

try:
    from report_generator.template_report import (
        TemplateReportGenerator,
        ScanResult,
        TemplateType
    )
    TEMPLATE_AVAILABLE = True
except ImportError:
    TEMPLATE_AVAILABLE = False
    print("⚠️ 模板报告模块未加载")

# 创建 FastAPI Router
reports_router = APIRouter(prefix="/api/reports", tags=["reports"])

# 全局生成器实例
_template_generator: Optional[TemplateReportGenerator] = None


def get_template_generator() -> Optional[TemplateReportGenerator]:
    """获取模板生成器单例"""
    global _template_generator
    if not TEMPLATE_AVAILABLE:
        return None
    if _template_generator is None:
        _template_generator = TemplateReportGenerator()
    return _template_generator


@reports_router.get("/templates")
async def list_templates():
    """列出所有可用模板"""
    if not TEMPLATE_AVAILABLE:
        raise HTTPException(status_code=503, detail="模板模块不可用")
    
    generator = get_template_generator()
    templates = generator.list_templates()
    
    return {
        "success": True,
        "templates": templates,
        "count": len(templates)
    }


@reports_router.get("/templates/{template_name}")
async def get_template_info(template_name: str):
    """获取模板详细信息"""
    if not TEMPLATE_AVAILABLE:
        raise HTTPException(status_code=503, detail="模板模块不可用")
    
    generator = get_template_generator()
    
    try:
        info = generator.get_template_info(template_name)
        return {
            "success": True,
            "template": info
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@reports_router.post("/generate")
async def generate_report(request_data: Dict[str, Any]):
    """
    生成报告
    
    Request Body:
        {
            "task_id": "扫描任务 ID",
            "template": "模板名称 (simple/standard/detailed/executive/technical/json)",
            "format": "输出格式 (html/pdf/json)",
            "save_to_file": true/false
        }
    """
    if not TEMPLATE_AVAILABLE:
        raise HTTPException(status_code=503, detail="模板模块不可用")
    
    task_id = request_data.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="缺少 task_id")
    
    template_name = request_data.get("template", "standard")
    output_format = request_data.get("format", "html")
    save_to_file = request_data.get("save_to_file", True)
    
    # TODO: 从数据库加载扫描结果
    # 暂时返回占位响应
    return {
        "success": True,
        "message": "报告生成功能待实现",
        "task_id": task_id,
        "template": template_name,
        "format": output_format
    }


@reports_router.get("/{task_id}/download")
async def download_report(task_id: str, format: str = "html"):
    """下载指定格式报告"""
    # TODO: 实现报告下载
    raise HTTPException(status_code=501, detail="报告下载待实现")


@reports_router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "template_available": TEMPLATE_AVAILABLE,
        "version": "v2.6.0"
    }


# 注册函数（供 main.py 调用）
def register_reports_api(app):
    """将报告模板 API 注册到 FastAPI 应用"""
    app.include_router(reports_router)
    print("✅ 报告模板 API 已注册：/api/reports/*")
