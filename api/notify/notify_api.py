"""
邮件通知 API - v2.6.0 新特性 (FastAPI 版本)

提供 REST API 端点用于配置和发送邮件通知

端点:
    GET  /api/notify/config          - 获取邮件配置
    POST /api/notify/config          - 更新邮件配置
    POST /api/notify/send            - 发送扫描完成通知
    POST /api/notify/test            - 发送测试邮件
    GET  /api/notify/health          - 健康检查
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import os
import logging
from typing import Optional, List, Dict, Any

try:
    from services.notification.email_service import (
        EmailService, EmailConfig, create_smtp_config
    )
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    print("⚠️ 邮件通知模块未加载")

# 创建 FastAPI Router
notify_router = APIRouter(prefix="/api/notify", tags=["notify"])

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


@notify_router.get("/config")
async def get_config():
    """获取邮件配置"""
    if not EMAIL_AVAILABLE:
        raise HTTPException(status_code=503, detail="邮件模块不可用")
    
    config = _load_config_from_env()
    
    return {
        "success": True,
        "config": {
            "smtp_host": config.smtp_host,
            "smtp_port": config.smtp_port,
            "smtp_user": config.smtp_user[:3] + "***" if config.smtp_user else "",
            "sender_email": config.sender_email,
            "sender_name": config.sender_name,
            "use_tls": config.use_tls
        }
    }


@notify_router.post("/config")
async def update_config(request_data: Dict[str, Any]):
    """更新邮件配置"""
    if not EMAIL_AVAILABLE:
        raise HTTPException(status_code=503, detail="邮件模块不可用")
    
    # 更新环境变量
    if 'smtp_host' in request_data:
        os.environ['SMTP_HOST'] = request_data['smtp_host']
    if 'smtp_port' in request_data:
        os.environ['SMTP_PORT'] = str(request_data['smtp_port'])
    if 'smtp_user' in request_data:
        os.environ['SMTP_USER'] = request_data['smtp_user']
    if 'smtp_password' in request_data:
        os.environ['SMTP_PASSWORD'] = request_data['smtp_password']
    if 'sender_email' in request_data:
        os.environ['SENDER_EMAIL'] = request_data['sender_email']
    if 'sender_name' in request_data:
        os.environ['SENDER_NAME'] = request_data['sender_name']
    
    # 重新加载服务
    global _email_service, _email_config
    _email_config = _load_config_from_env()
    _email_service = EmailService(_email_config)
    
    return {
        "success": True,
        "message": "配置已更新"
    }


@notify_router.post("/send")
async def send_notification(request_data: Dict[str, Any]):
    """发送扫描完成通知"""
    if not EMAIL_AVAILABLE:
        raise HTTPException(status_code=503, detail="邮件模块不可用")
    
    if 'scan_result' not in request_data or 'recipients' not in request_data:
        raise HTTPException(status_code=400, detail="缺少 scan_result 或 recipients")
    
    service = get_email_service()
    
    try:
        success = service.send_scan_complete(
            scan_result=request_data['scan_result'],
            recipients=request_data['recipients'],
            report_url=request_data.get('report_url'),
            attachments=request_data.get('attachments')
        )
        
        if success:
            return {"success": True, "message": "邮件发送成功"}
        else:
            raise HTTPException(status_code=500, detail="邮件发送失败")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@notify_router.post("/test")
async def send_test_email(request_data: Dict[str, Any]):
    """发送测试邮件"""
    if not EMAIL_AVAILABLE:
        raise HTTPException(status_code=503, detail="邮件模块不可用")
    
    recipients = request_data.get('recipients', [])
    if not recipients:
        raise HTTPException(status_code=400, detail="请提供收件人列表")
    
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
        report_url="https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner"
    )
    
    if success:
        return {"success": True, "message": "测试邮件已发送"}
    else:
        raise HTTPException(status_code=500, detail="测试邮件发送失败")


@notify_router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "email_available": EMAIL_AVAILABLE,
        "version": "v2.6.0"
    }


# 注册函数（供 main.py 调用）
def register_notify_api(app):
    """将邮件通知 API 注册到 FastAPI 应用"""
    app.include_router(notify_router)
    print("✅ 邮件通知 API 已注册：/api/notify/*")
