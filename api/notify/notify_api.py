"""
邮件通知 API - v2.6.0

提供 REST API 端点用于配置和发送邮件通知

端点:
    GET  /api/notify/config          - 获取邮件配置
    POST /api/notify/config          - 更新邮件配置
    POST /api/notify/send            - 发送扫描完成通知
    POST /api/notify/test            - 发送测试邮件
    GET  /api/notify/health          - 健康检查
"""

from flask import Blueprint, request, jsonify
from flask_cors import CORS
import os
import logging
from typing import Optional

try:
    from services.notification.email_service import (
        EmailService, EmailConfig, create_smtp_config
    )
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    print("⚠️ 邮件通知模块未加载")

# 创建 Blueprint
notify_bp = Blueprint('notify', __name__, url_prefix='/api/notify')
CORS(notify_bp)

# 全局配置
_email_config: Optional[EmailConfig] = None
_email_service: Optional[EmailService] = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_email_service() -> Optional[EmailService]:
    """获取邮件服务单例"""
    global _email_service, _email_config
    if not EMAIL_AVAILABLE:
        return None
    
    if _email_service is None:
        # 从环境变量或配置文件加载
        _email_config = _load_config_from_env()
        _email_service = EmailService(_email_config)
    
    return _email_service


def _load_config_from_env() -> EmailConfig:
    """从环境变量加载配置"""
    return EmailConfig(
        smtp_host=os.getenv("SMTP_HOST", "smtp.163.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        sender_email=os.getenv("SENDER_EMAIL", "zhu80k@163.com"),
        sender_name=os.getenv("SENDER_NAME", "玄武·AFVS"),
        use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    )


@notify_bp.route('/config', methods=['GET'])
def get_config():
    """获取邮件配置"""
    if not EMAIL_AVAILABLE:
        return jsonify({"error": "邮件模块不可用"}), 503
    
    config = _load_config_from_env()
    
    return jsonify({
        "success": True,
        "config": {
            "smtp_host": config.smtp_host,
            "smtp_port": config.smtp_port,
            "smtp_user": config.smtp_user[:3] + "***" if config.smtp_user else "",
            "sender_email": config.sender_email,
            "sender_name": config.sender_name,
            "use_tls": config.use_tls
        }
    })


@notify_bp.route('/config', methods=['POST'])
def update_config():
    """更新邮件配置"""
    if not EMAIL_AVAILABLE:
        return jsonify({"error": "邮件模块不可用"}), 503
    
    data = request.get_json()
    
    # 更新环境变量
    if 'smtp_host' in data:
        os.environ['SMTP_HOST'] = data['smtp_host']
    if 'smtp_port' in data:
        os.environ['SMTP_PORT'] = str(data['smtp_port'])
    if 'smtp_user' in data:
        os.environ['SMTP_USER'] = data['smtp_user']
    if 'smtp_password' in data:
        os.environ['SMTP_PASSWORD'] = data['smtp_password']
    if 'sender_email' in data:
        os.environ['SENDER_EMAIL'] = data['sender_email']
    if 'sender_name' in data:
        os.environ['SENDER_NAME'] = data['sender_name']
    
    # 重新加载服务
    global _email_service, _email_config
    _email_config = _load_config_from_env()
    _email_service = EmailService(_email_config)
    
    return jsonify({
        "success": True,
        "message": "配置已更新"
    })


@notify_bp.route('/send', methods=['POST'])
def send_notification():
    """
    发送扫描完成通知
    
    Request Body:
        {
            "scan_result": {...},
            "recipients": ["user@example.com"],
            "report_url": "https://...",
            "attachments": ["/path/to/report.pdf"]
        }
    """
    if not EMAIL_AVAILABLE:
        return jsonify({"error": "邮件模块不可用"}), 503
    
    data = request.get_json()
    
    if 'scan_result' not in data or 'recipients' not in data:
        return jsonify({"error": "缺少 scan_result 或 recipients"}), 400
    
    service = get_email_service()
    
    try:
        success = service.send_scan_complete(
            scan_result=data['scan_result'],
            recipients=data['recipients'],
            report_url=data.get('report_url'),
            attachments=data.get('attachments')
        )
        
        if success:
            return jsonify({
                "success": True,
                "message": "邮件发送成功"
            })
        else:
            return jsonify({
                "error": "邮件发送失败"
            }), 500
    
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@notify_bp.route('/test', methods=['POST'])
def send_test_email():
    """发送测试邮件"""
    if not EMAIL_AVAILABLE:
        return jsonify({"error": "邮件模块不可用"}), 503
    
    data = request.get_json()
    recipients = data.get('recipients', [])
    
    if not recipients:
        return jsonify({"error": "请提供收件人列表"}), 400
    
    service = get_email_service()
    
    test_result = {
        "batch_id": "test_batch_001",
        "firmware_name": "测试固件",
        "status": "completed",
        "risk_score": 75.5,
        "severity_stats": {
            "Critical": 2,
            "High": 5,
            "Medium": 10,
            "Low": 15
        },
        "error": ""
    }
    
    success = service.send_scan_complete(
        scan_result=test_result,
        recipients=recipients,
        report_url="https://github.com/Jackson8ok/afvs"
    )
    
    if success:
        return jsonify({
            "success": True,
            "message": "测试邮件已发送"
        })
    else:
        return jsonify({
            "error": "测试邮件发送失败"
        }), 500


@notify_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "email_available": EMAIL_AVAILABLE,
        "version": "v2.6.0"
    })


# 注册 Blueprint
def register_notify_api(app):
    """将邮件通知 API 注册到 Flask 应用"""
    if hasattr(app, 'register_blueprint'):
        app.register_blueprint(notify_bp)
        print("✅ 邮件通知 API 已注册：/api/notify/*")
    else:
        print("⚠️ 无法注册邮件通知 API - 应用对象无效")
