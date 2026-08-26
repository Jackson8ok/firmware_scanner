"""
报告模板 API - v2.6.0 新特性

提供 REST API 端点用于生成和管理报告模板

端点:
    GET  /api/reports/templates          - 列出所有可用模板
    GET  /api/reports/templates/:name     - 获取模板详情
    POST /api/reports/generate           - 生成报告 (支持模板选择)
    GET  /api/reports/:task_id/download  - 下载指定格式报告
"""

from flask import Blueprint, request, jsonify, send_file
from flask_cors import CORS
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

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

# 创建 Blueprint
reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')
CORS(reports_bp)

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


@reports_bp.route('/templates', methods=['GET'])
def list_templates():
    """
    列出所有可用模板
    
    Returns:
        JSON: 模板列表
    """
    if not TEMPLATE_AVAILABLE:
        return jsonify({"error": "模板模块不可用"}), 503
    
    generator = get_template_generator()
    templates = generator.list_templates()
    
    return jsonify({
        "success": True,
        "templates": templates,
        "count": len(templates)
    })


@reports_bp.route('/templates/<template_name>', methods=['GET'])
def get_template_info(template_name: str):
    """
    获取模板详细信息
    
    Args:
        template_name: 模板名称
    
    Returns:
        JSON: 模板详情
    """
    if not TEMPLATE_AVAILABLE:
        return jsonify({"error": "模板模块不可用"}), 503
    
    generator = get_template_generator()
    
    try:
        info = generator.get_template_info(template_name)
        return jsonify({
            "success": True,
            "template": info
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@reports_bp.route('/generate', methods=['POST'])
def generate_report():
    """
    生成报告
    
    Request Body:
        {
            "task_id": "扫描任务 ID",
            "template": "模板名称 (simple/standard/detailed/executive/technical/json)",
            "format": "输出格式 (html/pdf/json)",
            "save_to_file": true/false  (可选，默认 true)
        }
    
    Returns:
        JSON: 生成结果 + 下载链接
    """
    if not TEMPLATE_AVAILABLE:
        return jsonify({"error": "模板模块不可用"}), 503
    
    data = request.get_json()
    
    if not data or 'task_id' not in data:
        return jsonify({"error": "缺少 task_id"}), 400
    
    task_id = data['task_id']
    template_name = data.get('template', 'standard')
    output_format = data.get('format', 'html')
    save_to_file = data.get('save_to_file', True)
    
    # TODO: 从数据库加载扫描结果
    # 这里需要集成到实际的扫描结果存储
    # 暂时返回错误
    return jsonify({
        "error": "扫描结果未实现",
        "message": "需要实现从数据库加载 scan_result 的逻辑",
        "task_id": task_id,
        "template": template_name,
        "format": output_format
    }), 501


@reports_bp.route('/<task_id>/download', methods=['GET'])
def download_report(task_id: str):
    """
    下载报告
    
    Query Params:
        format: 报告格式 (html/pdf/json)，默认 html
        template: 模板名称，默认 standard
    
    Returns:
        File: 报告文件
    """
    # TODO: 实现报告下载
    return jsonify({
        "error": "未实现",
        "task_id": task_id
    }), 501


@reports_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "template_available": TEMPLATE_AVAILABLE,
        "version": "v2.6.0"
    })


# 注册 Blueprint
def register_reports_api(app):
    """将报告 API 注册到 Flask 应用"""
    if hasattr(app, 'register_blueprint'):
        app.register_blueprint(reports_bp)
        print("✅ 报告模板 API 已注册：/api/reports/*")
    else:
        print("⚠️ 无法注册报告 API - 应用对象无效")
