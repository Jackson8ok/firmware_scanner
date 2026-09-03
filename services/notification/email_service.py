"""
邮件通知模块 - v2.6.0

在扫描完成后自动发送邮件通知
支持 SMTP/IMAP，邮件模板渲染

使用方式:
    from services.notification.email_service import EmailService
    
    service = EmailService(config)
    service.send_scan_complete({
        "batch_id": "batch_xxx",
        "status": "completed",
        "total_vulns": 47,
        "risk_score": 75.5
    }, ["user@example.com"])
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email import encoders
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass

try:
    from jinja2 import Environment, BaseLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """邮件服务配置"""
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    use_tls: bool = True
    sender_email: str = ""
    sender_name: str = "玄武·AFVS"
    reply_to: str = ""


class EmailService:
    """邮件通知服务（v2.6.0）"""
    
    # 内嵌邮件模板
    TEMPLATE_SCAN_COMPLETE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>扫描完成通知</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #1a237e, #3949ab); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }
        .stat-card { display: inline-block; background: white; padding: 15px 25px; border-radius: 8px; margin: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }
        .stat-value { font-size: 28px; font-weight: bold; color: #1a237e; }
        .stat-label { font-size: 12px; color: #666; margin-top: 5px; }
        .critical { color: #d32f2f; }
        .high { color: #f57c00; }
        .medium { color: #fbc02d; }
        .low { color: #388e3c; }
        .risk-score { font-size: 42px; font-weight: bold; background: linear-gradient(135deg, #1a237e, #3949ab); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .footer { text-align: center; color: #999; font-size: 12px; margin-top: 30px; }
        .btn { display: inline-block; background: #1a237e; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐢 玄武·AFVS 通知</h1>
            <p>Auto Firmware Vulnerability Scanner</p>
        </div>
        <div class="content">
            <h2>扫描任务 {{ status | upper }}</h2>
            <p>尊敬的用户，您的固件扫描任务已完成。</p>
            
            <p><strong>任务信息：</strong></p>
            <ul>
                <li>任务 ID: {{ batch_id }}</li>
                <li>固件名称: {{ firmware_name }}</li>
                <li>完成时间: {{ completed_at }}</li>
            </ul>
            
            {% if status == 'completed' %}
            <div style="text-align: center; margin: 30px 0;">
                <div class="stat-card">
                    <div class="stat-value risk-score">{{ risk_score }}</div>
                    <div class="stat-label">风险评分</div>
                </div>
            </div>
            
            <div style="text-align: center;">
                <div class="stat-card">
                    <div class="stat-value critical">{{ critical_count }}</div>
                    <div class="stat-label">严重漏洞</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value high">{{ high_count }}</div>
                    <div class="stat-label">高危漏洞</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value medium">{{ medium_count }}</div>
                    <div class="stat-label">中危漏洞</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value low">{{ low_count }}</div>
                    <div class="stat-label">低危漏洞</div>
                </div>
            </div>
            
            <p style="text-align: center;">
                <a href="{{ report_url }}" class="btn">查看完整报告</a>
            </p>
            {% else %}
            <p style="color: #d32f2f;"><strong>⚠️ 扫描过程中出现错误</strong></p>
            <p>{{ error_message }}</p>
            {% endif %}
            
            <div class="footer">
                <p>玄武·AFVS v2.6.0</p>
                <p>Auto Firmware Vulnerability Scanner</p>
                <p>联系我们: zhu80k@163.com</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    def __init__(self, config: EmailConfig):
        """
        初始化邮件服务
        
        Args:
            config: 邮件配置
        """
        self.config = config
        self._server: Optional[smtplib.SMTP] = None
        
        # 初始化 Jinja2
        if JINJA2_AVAILABLE:
            self.jinja_env = Environment(loader=BaseLoader())
            self.template = self.jinja_env.from_string(self.TEMPLATE_SCAN_COMPLETE)
        else:
            self.jinja_env = None
            self.template = None
            logger.warning("⚠️ Jinja2 未安装，邮件模板将使用基础渲染")
        
        logger.info(f"✅ EmailService 初始化完成 (SMTP: {config.smtp_host}:{config.smtp_port})")
    
    def connect(self):
        """连接 SMTP 服务器"""
        try:
            self._server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
            
            if self.config.use_tls:
                self._server.starttls()
            
            if self.config.smtp_user and self.config.smtp_password:
                self._server.login(self.config.smtp_user, self.config.smtp_password)
            
            logger.info("✅ SMTP 服务器连接成功")
        except Exception as e:
            logger.error(f"❌ SMTP 连接失败：{e}")
            raise
    
    def disconnect(self):
        """断开 SMTP 连接"""
        if self._server:
            try:
                self._server.quit()
                logger.info("✅ SMTP 服务器已断开")
            except Exception:
                pass
            finally:
                self._server = None
    
    def send_scan_complete(self, scan_result: Dict[str, Any], 
                          recipients: List[str],
                          report_url: Optional[str] = None,
                          attachments: Optional[List[str]] = None) -> bool:
        """
        发送扫描完成通知
        
        Args:
            scan_result: 扫描结果字典
            recipients: 收件人列表
            report_url: 报告下载链接（可选）
            attachments: 附件路径列表（可选）
        
        Returns:
            是否发送成功
        """
        if not self._server:
            self.connect()
        
        try:
            # 准备模板上下文
            context = self._prepare_context(scan_result, report_url)
            
            # 渲染 HTML 邮件
            if self.template:
                html_body = self.template.render(**context)
            else:
                html_body = self._render_fallback(context)
            
            # 构建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{context['status'].upper()}] 玄武·AFVS 扫描结果 - {context['firmware_name']}"
            msg['From'] = f"{self.config.sender_name} <{self.config.sender_email}>"
            msg['To'] = ", ".join(recipients)
            
            if self.config.reply_to:
                msg['Reply-To'] = self.config.reply_to
            
            # 添加 HTML 正文
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            # 添加附件
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            attach = MIMEApplication(f.read(), _subtype=file_path.split('.')[-1])
                            attach.add_header(
                                'Content-Disposition',
                                'attachment',
                                filename=os.path.basename(file_path)
                            )
                            msg.attach(attach)
            
            # 发送邮件
            self._server.send_message(msg)
            logger.info(f"✅ 邮件已发送至 {', '.join(recipients)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 邮件发送失败：{e}")
            return False
    
    def _prepare_context(self, scan_result: Dict[str, Any], 
                        report_url: Optional[str]) -> Dict[str, Any]:
        """准备邮件模板上下文"""
        severity_stats = scan_result.get("severity_stats", {})
        
        return {
            "batch_id": scan_result.get("batch_id", "unknown"),
            "firmware_name": scan_result.get("firmware_name", "未知固件"),
            "status": scan_result.get("status", "completed"),
            "risk_score": scan_result.get("risk_score", "N/A"),
            "critical_count": severity_stats.get("Critical", 0),
            "high_count": severity_stats.get("High", 0),
            "medium_count": severity_stats.get("Medium", 0),
            "low_count": severity_stats.get("Low", 0),
            "completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "report_url": report_url or "https://github.com/Jackson8ok/afvs",
            "error_message": scan_result.get("error", ""),
        }
    
    def _render_fallback(self, context: Dict[str, Any]) -> str:
        """基础邮件渲染（不依赖 Jinja2）"""
        risk_score = context.get("risk_score", "N/A")
        return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>扫描完成通知</title></head>
<body>
    <h1>🐢 玄武·AFVS 通知</h1>
    <h2>扫描任务 {context['status'].upper()}</h2>
    <p><strong>任务 ID:</strong> {context['batch_id']}</p>
    <p><strong>固件名称:</strong> {context['firmware_name']}</p>
    <p><strong>完成时间:</strong> {context['completed_at']}</p>
    <p><strong>风险评分:</strong> {risk_score}/100</p>
    <p><strong>严重漏洞:</strong> {context['critical_count']}</p>
    <p><strong>高危漏洞:</strong> {context['high_count']}</p>
    <p><a href="{context['report_url']}">查看完整报告</a></p>
</body>
</html>
"""


# 便捷函数
def create_smtp_config(host: str, user: str, password: str, 
                       sender: str, port: int = 587) -> EmailConfig:
    """创建 SMTP 邮件配置"""
    return EmailConfig(
        smtp_host=host,
        smtp_port=port,
        smtp_user=user,
        smtp_password=password,
        sender_email=sender
    )


def send_notification(config: EmailConfig, result: Dict, 
                     recipients: List[str], **kwargs) -> bool:
    """便捷函数：发送通知"""
    service = EmailService(config)
    return service.send_scan_complete(result, recipients, **kwargs)
