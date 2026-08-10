"""
固件漏洞扫描平台 - FastAPI Web API + Socket.IO 正确集成
版本：v2.3 (WebSocket 实时通知版)

修复说明:
- 使用 python-socketio 官方推荐的集成方式
- 避免 ASGIApp 包装导致的 Request 对象问题
- 确保模板渲染正常工作
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import logging
import json

# FastAPI 核心
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel

# Socket.IO
import socketio
from socketio import ASGIApp

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.engine import FirmwareExtractor, SBOMGenerator, CVEMatcher, Vulnerability
from scanner.task_queue import get_scan_queue, ScanTask, TaskStatus, ScanQueue
from scanner.logging_config import setup_logging, log_audit
from api.error_handler import (
    app_exception_handler, http_exception_handler, generic_exception_handler,
    AppException, ErrorCode, ErrorResponse
)
import yaml

# ============================================================
# 日志配置
# ============================================================
setup_logging(
    log_dir="./logs",
    console_level=logging.INFO,
    file_level=logging.WARNING,
    max_bytes=10*1024*1024,
    backup_count=5
)
logger = logging.getLogger(__name__)

# ============================================================
# 加载配置
# ============================================================
config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path, encoding='utf-8') as f:
    config = yaml.safe_load(f)

def resolve_env_var(value):
    """解析环境变量占位符"""
    if not isinstance(value, str):
        return value
    import re
    pattern = r'\$\{([^}:]+)(?::(.+))?\}'
    match = re.match(pattern, value)
    if match:
        env_name = match.group(1)
        default_value = match.group(2)
        return os.environ.get(env_name, default_value or '')
    return value

def process_config_values(cfg):
    """递归处理配置中的环境变量"""
    if isinstance(cfg, dict):
        return {k: process_config_values(v) for k, v in cfg.items()}
    elif isinstance(cfg, list):
        return [process_config_values(item) for item in cfg]
    else:
        return resolve_env_var(cfg)

config = process_config_values(config)

if 'paths' in config:
    for key in config['paths']:
        path_val = config['paths'][key]
        if isinstance(path_val, str) and path_val.startswith('~'):
            config['paths'][key] = str(Path(path_val).expanduser())

logger.info(f"Grype DB 路径：{config['paths'].get('grype_db', '未配置')}")

# ============================================================
# Socket.IO 服务器初始化
# ============================================================
sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    async_mode="asgi",
    logger=False,
    engineio_logger=False
)

# Socket.IO 事件处理器
@sio.event
async def connect(sid, environ, auth):
    """客户端连接"""
    logger.info(f"🔗 Socket.IO 客户端连接：{sid}")
    
    # 发送初始任务列表
    try:
        queue = get_queue()
        all_tasks = queue.get_all_tasks(limit=50)
        tasks_data = [
            {
                'task_id': t.task_id,
                'filename': t.filename,
                'status': t.status.value,
                'progress': t.progress,
                'created_at': t.created_at
            }
            for t in all_tasks
        ]
        await sio.emit('initial_tasks', {'tasks': tasks_data}, to=sid)
    except Exception as e:
        logger.error(f"发送初始任务失败：{e}")

@sio.event
async def disconnect(sid):
    """客户端断开"""
    logger.info(f"❌ Socket.IO 客户端断开：{sid}")

# ============================================================
# FastAPI 应用初始化
# ============================================================
app = FastAPI(title="固件漏洞扫描平台", version="2.3 (WebSocket)")

# 注册异常处理器
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# 模板和静态文件
templates_path = Path(__file__).parent.parent / "frontend" / "templates"
static_path = Path(__file__).parent.parent / "frontend" / "static"

# 标准方式初始化 Jinja2Templates（FastAPI 会自动启用 autoescape）
templates = Jinja2Templates(directory=str(templates_path))

# 确保目录存在
for dir_path in [config['paths']['uploads'], 
                 config['paths']['workspace'],
                 config['paths']['reports']]:
    Path(dir_path).mkdir(parents=True, exist_ok=True)

# ============================================================
# 获取扫描队列（注册 WebSocket 回调）
# ============================================================
MAX_CONCURRENT = config.get('queue', {}).get('max_concurrent', 3)
scan_queue_instance: Optional[ScanQueue] = None

def get_queue() -> ScanQueue:
    """获取扫描队列实例（单例）"""
    global scan_queue_instance
    
    if scan_queue_instance is None:
        scan_queue_instance = get_scan_queue(max_concurrent=MAX_CONCURRENT)
        
        # 注册 WebSocket 通知发送器
        def send_ws_notification(event_type: str, data: dict):
            """发送 WebSocket 通知"""
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(sio.emit(event_type, data))
                else:
                    loop.run_until_complete(sio.emit(event_type, data))
            except Exception as e:
                logger.error(f"WebSocket 通知发送失败：{e}")
        
        scan_queue_instance.set_notification_sender(send_ws_notification)
        logger.info("✅ WebSocket 通知系统已启用")
    
    return scan_queue_instance

# ============================================================
# Pydantic 模型（保持原有定义）
# ============================================================
class ScanRequest(BaseModel):
    firmware_id: str
    firmware_type: str

class BatchScanRequest(BaseModel):
    files: List[dict]

class TaskStatusResponse(BaseModel):
    task_id: str
    filename: str
    status: str
    progress: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

class QueueStatsResponse(BaseModel):
    total: int
    pending: int
    queued: int
    running: int
    completed: int
    failed: int
    active_workers: int
    max_concurrent: int

# ============================================================
# 路由定义
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """首页 - 使用底层模板渲染避免缓存 bug"""
    logger = logging.getLogger(__name__)
    
    try:
        # 直接获取模板环境并渲染（不经过 TemplateResponse 包装）
        template = templates.env.get_template("index.html")
        
        # 渲染模板
        html_content = template.render(request=request, now=datetime.now())
        
        logger.info("✅ 模板渲染成功（底层方式）")
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"❌ 模板渲染失败：{e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"模板渲染失败：{str(e)}")

@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": "2.3",
        "websocket": "enabled",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/dashboard")
async def dashboard_page(request: Request):
    """仪表板页面（兼容旧版本）"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.post("/api/upload")
async def upload_firmware(file: UploadFile = File(...)):
    """上传固件文件"""
    try:
        upload_dir = Path(config['paths']['uploads'])
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"✅ 文件上传成功：{file.filename} ({len(content)} bytes)")
        
        return {
            "success": True,
            "message": "文件上传成功",
            "filename": file.filename,
            "path": str(file_path),
            "size": len(content)
        }
    except Exception as e:
        logger.error(f"文件上传失败：{e}")
        raise HTTPException(status_code=500, detail=f"上传失败：{str(e)}")

@app.post("/api/scan")
async def start_scan(firmware_id: str = Form(...), firmware_type: str = Form(...)):
    """开始扫描"""
    try:
        queue = get_queue()
        
        # 这里需要根据 firmware_id 找到文件路径
        upload_dir = Path(config['paths']['uploads'])
        firmware_path = upload_dir / firmware_id
        
        if not firmware_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        task_id = queue.add_task(str(firmware_path), firmware_type)
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "扫描任务已提交"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"扫描启动失败：{e}")
        raise HTTPException(status_code=500, detail=f"启动失败：{str(e)}")

@app.get("/api/task/{task_id}/status")
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        queue = get_queue()
        task = queue.get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return {
            "task_id": task.task_id,
            "filename": task.filename,
            "status": task.status.value,
            "progress": task.progress,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "error_message": task.error_message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败：{e}")
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")

@app.get("/api/queue/stats")
async def get_queue_stats():
    """获取队列统计"""
    try:
        queue = get_queue()
        stats = queue.get_queue_stats()
        
        return QueueStatsResponse(**stats).dict()
    except Exception as e:
        logger.error(f"获取队列统计失败：{e}")
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


# ============================================================
# PDF 报告相关路由
# ============================================================

@app.get("/api/task/{task_id}/report/pdf")
async def download_pdf_report(task_id: str):
    """
    下载任务 PDF 报告
    
    Args:
        task_id: 任务 ID
        
    Returns:
        PDF 文件下载
    """
    try:
        from report_generator.pdf_generator import generate_pdf_report
        
        queue = get_queue()
        task = queue.get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail=f"任务未完成，当前状态：{task.status.value}"
            )
        
        # 获取扫描结果
        result = task.result if task.result else {}
        
        # 生成 PDF 报告
        logger.info(f"📄 正在为任务 {task_id} 生成 PDF 报告...")
        pdf_path = generate_pdf_report(task_id, result)
        
        logger.info(f"✅ PDF 报告已生成：{pdf_path}")
        
        # 返回 PDF 文件
        filename = f"{task.filename}_security_report.pdf"
        
        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type='application/pdf'
        )
        
    except HTTPException:
        raise
    except ModuleNotFoundError as e:
        logger.error(f"PDF 生成模块未安装：{e}")
        raise HTTPException(
            status_code=500, 
            detail="PDF 生成依赖未安装。请运行：pip install reportlab matplotlib numpy"
        )
    except Exception as e:
        logger.error(f"生成 PDF 报告失败：{e}")
        raise HTTPException(status_code=500, detail=f"生成失败：{str(e)}")


@app.post("/api/task/{task_id}/regenerate-report")
async def regenerate_pdf_report(task_id: str, include_charts: bool = False):
    """
    重新生成 PDF 报告（可选包含图表）
    
    Args:
        task_id: 任务 ID
        include_charts: 是否包含图表（默认关闭以提高兼容性）
        
    Returns:
        生成的 PDF 文件路径
    """
    try:
        from report_generator.pdf_generator import generate_pdf_report
        
        queue = get_queue()
        task = queue.get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail=f"任务未完成，当前状态：{task.status.value}"
            )
        
        result = task.result if task.result else {}
        
        logger.info(f"🔄 重新生成 PDF 报告 (包含图表={include_charts})")
        pdf_path = generate_pdf_report(task_id, result, include_charts=False)
        
        return {
            "success": True,
            "message": "PDF 报告已重新生成",
            "pdf_path": pdf_path,
            "download_url": f"/api/task/{task_id}/report/pdf"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新生成 PDF 报告失败：{e}")
        raise HTTPException(status_code=500, detail=f"生成失败：{str(e)}")

# ============================================================
# 启动事件
# ============================================================
@app.on_event("startup")
async def startup_event():
    """启动时初始化队列"""
    logger.info("启动扫描队列服务...")
    queue = get_queue()
    queue.start()
    logger.info(f"扫描队列已启动 (最大并发：{MAX_CONCURRENT})")

@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理资源"""
    logger.info("正在停止扫描队列...")
    try:
        queue = get_queue()
        queue.stop(wait=True, timeout=60)
        logger.info("扫描队列已停止")
    except Exception as e:
        logger.error(f"停止队列失败：{e}")

# ============================================================
# 主程序入口
# ============================================================
if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 60)
    logger.info("🦞 固件漏洞扫描平台 v2.3 (带 WebSocket 实时通知)")
    logger.info("=" * 60)
    
    # 直接启动 FastAPI 应用
    uvicorn.run(
        app,
        host=config.get('server', {}).get('host', '0.0.0.0'),
        port=config.get('server', {}).get('port', 8000),
        reload=False,
        log_level="info"
    )
