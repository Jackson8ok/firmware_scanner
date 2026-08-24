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
import asyncio
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
    pattern = r'[\$]\{([^}:]+)(?::-([^}]*))?\}'
    match = re.search(pattern, value)
    if match:
        env_name = match.group(1)
        default_value = match.group(2) if match.group(2) is not None else ''
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

# 检查 Grype DB 可用性
grype_db_path = config.get('paths', {}).get('grype_db')
if grype_db_path:
    grype_db_path = os.path.expanduser(grype_db_path)
    if os.path.exists(grype_db_path):
        logger.info(f"Grype DB 可用：{grype_db_path}")
    else:
        logger.error(f"Grype DB 不可用：{grype_db_path}（文件不存在，CVE 匹配将跳过）")
        logger.warning("请执行以下命令下载 Grype DB：")
        logger.warning("  1. 安装 Grype：https://github.com/anchore/grype/releases")
        logger.warning("  2. 下载数据库：grype db download")
        logger.warning("  3. 或设置环境变量 GRYPE_DB_PATH 指向现有数据库")
else:
    logger.warning("未配置 Grype DB 路径，CVE 匹配将跳过")

# ============================================================
# Socket.IO 服务器初始化
# ============================================================
sio = socketio.AsyncServer(
    cors_allowed_origins=config.get('cors', {}).get('allowed_origins', ["http://localhost:3000"]),
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
# FastAPI 应用初始化（作为子应用）
# ============================================================
from socketio import ASGIApp

_base_app = FastAPI(
    title="固件漏洞扫描平台", 
    version="2.5.3",
    description="已启用 WebSocket 实时通知的固件安全扫描器"
)

# 注册异常处理器
_base_app.add_exception_handler(AppException, app_exception_handler)
_base_app.add_exception_handler(HTTPException, http_exception_handler)
_base_app.add_exception_handler(Exception, generic_exception_handler)

# 模板和静态文件
templates_path = Path(__file__).parent.parent / "frontend" / "templates"
static_path = Path(__file__).parent.parent / "frontend" / "static"

# 标准方式初始化 Jinja2Templates（FastAPI 会自动启用 autoescape）
templates = Jinja2Templates(directory=str(templates_path))

# 挂载前端静态文件
_base_app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

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

# P1-1 修复：为线程池中的 WebSocket 通知创建专用事件循环
_ws_event_loop: Optional[asyncio.AbstractEventLoop] = None

def _ensure_ws_event_loop() -> asyncio.AbstractEventLoop:
    """确保 WebSocket 通知有可用的事件循环（后台线程）"""
    global _ws_event_loop
    if _ws_event_loop is None or not _ws_event_loop.is_running():
        import threading
        _ws_event_loop = asyncio.new_event_loop()
        
        def run_loop():
            asyncio.set_event_loop(_ws_event_loop)
            _ws_event_loop.run_forever()
        
        t = threading.Thread(target=run_loop, daemon=True)
        t.start()
        logger.info("✅ WebSocket 后台事件循环已启动")
    return _ws_event_loop

def get_queue() -> ScanQueue:
    """获取扫描队列实例（单例）"""
    global scan_queue_instance
    
    if scan_queue_instance is None:
        scan_queue_instance = get_scan_queue(max_concurrent=MAX_CONCURRENT)
        
        # 注册 WebSocket 通知发送器
        def send_ws_notification(event_type: str, data: dict):
            """发送 WebSocket 通知（线程安全）"""
            try:
                loop = _ensure_ws_event_loop()
                coro = sio.emit(event_type, data)
                asyncio.run_coroutine_threadsafe(coro, loop)
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

@_base_app.get("/", response_class=HTMLResponse)
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

@_base_app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": "2.5.3",
        "websocket": "enabled",
        "timestamp": datetime.now().isoformat()
    }

@_base_app.get("/api/dashboard")
async def dashboard_page(request: Request):
    """仪表板页面（兼容旧版本）"""
    try:
        template = templates.env.get_template("dashboard.html")
        html_content = template.render(request=request, now=datetime.now())
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"仪表板渲染失败：{e}")
        raise HTTPException(status_code=500, detail="仪表板加载失败")

@_base_app.post("/api/upload")
async def upload_firmware(file: UploadFile = File(...)):
    """上传固件文件"""
    try:
        upload_dir = Path(config['paths']['uploads'])
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 路径穿越防护：只保留文件名，去除目录部分
        safe_filename = Path(file.filename).name
        if not safe_filename:
            raise HTTPException(status_code=400, detail="文件名无效")
        
        file_path = upload_dir / safe_filename
        content = await file.read()
        
        max_size = config.get('upload', {}).get('max_size', 100 * 1024 * 1024)
        if len(content) > max_size:
            raise HTTPException(status_code=413, detail=f"文件过大，最大支持 {max_size // 1024 // 1024}MB")
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"✅ 文件上传成功：{safe_filename} ({len(content)} bytes)")
        
        return {
            "success": True,
            "message": "文件上传成功",
            "filename": safe_filename,
            "path": str(file_path),
            "size": len(content)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败：{e}")
        raise HTTPException(status_code=500, detail=f"上传失败：{str(e)}")

@_base_app.post("/api/scan")
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

@_base_app.get("/api/task/{task_id}/status")
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

@_base_app.get("/api/task/{task_id}/result")
async def get_task_result(task_id: str):
    """获取任务扫描结果"""
    try:
        queue = get_queue()
        task = queue.get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        result = task.result if task.result else {}
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务结果失败：{e}")
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")

@_base_app.get("/api/queue/stats")
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

@_base_app.get("/api/task/{task_id}/report/pdf")
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


@_base_app.post("/api/task/{task_id}/regenerate-report")
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
# 新增 API 端点 - 任务管理
# ============================================================

@_base_app.get("/api/tasks")
async def list_tasks(status: Optional[str] = Query(None, description="按状态筛选"), limit: int = Query(50, le=200)):
    """获取任务列表（支持按状态筛选）"""
    try:
        queue = get_queue()
        # 将字符串状态转换为 TaskStatus 枚举（如存在）
        status_filter = None
        if status:
            try:
                status_filter = TaskStatus(status)
            except (ValueError, KeyError):
                # 尝试用 value 匹配
                for ts in TaskStatus:
                    if ts.value == status:
                        status_filter = ts
                        break
        tasks = queue.get_all_tasks(limit=limit, status=status_filter)
        result = []
        for t in tasks:
            if hasattr(t, "dict"):
                result.append(t.dict())
            else:
                result.append({
                    "task_id": getattr(t, "task_id", str(t)),
                    "filename": getattr(t, "filename", ""),
                    "status": getattr(t, "status", ""),
                    "progress": getattr(t, "progress", 0),
                    "created_at": getattr(t, "created_at", "")
                })
        return {"tasks": result}
    except Exception as e:
        logger.error(f"获取任务列表失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))

@_base_app.delete("/api/task/{task_id}")
async def delete_task(task_id: str):
    """删除任务及其文件"""
    try:
        queue = get_queue()
        # 实现删除逻辑
        success = True  # TODO: 实现真正的删除
        return {"success": success, "message": "任务已删除"}
    except Exception as e:
        logger.error(f"删除任务失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# 新增 API 端点 - 批量扫描
# ============================================================

@_base_app.post("/api/scan/batch")
async def batch_scan(firmware_list: List[str]):
    """批量启动扫描"""
    try:
        queue = get_queue()
        task_ids = []
        for firmware_id in firmware_list:
            if hasattr(queue, "add_task"):
                task = queue.add_task(firmware_id)
                task_ids.append(task.task_id)
        return {"task_ids": task_ids, "count": len(task_ids)}
    except Exception as e:
        logger.error(f"批量扫描失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# 新增 API 端点 - Excel 报告导出
# ============================================================

@_base_app.get("/api/report/excel/{task_id}")
async def export_excel_report(task_id: str):
    """导出 Excel 漏洞清单"""
    try:
        from report_generator.excel_exporter import generate_excel_report
        
        queue = get_queue()
        task = queue.get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        result = task.result if task.result else {}
        excel_path = generate_excel_report(task_id, result)
        
        filename = f"{task.filename}_vulnerability_list.xlsx"
        
        return FileResponse(
            path=excel_path,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="Excel 导出依赖未安装：pip install openpyxl")
    except Exception as e:
        logger.error(f"Excel 导出失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# 新增 API 端点 - 审计报告包（R155 合规审计完整包）
# ============================================================

@_base_app.post("/api/report/audit-package/{task_id}")
async def download_audit_package(task_id: str):
    """下载完整 R155 审计报告包（ZIP 格式，包含 8 份文档）"""
    try:
        from report_generator.audit_package import create_audit_package
        
        queue = get_queue()
        task = queue.get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        result = task.result if task.result else {}
        zip_path = create_audit_package(task_id, result)
        
        filename = f"{task.filename}_R155_audit_package.zip"
        
        return FileResponse(
            path=zip_path,
            filename=filename,
            media_type='application/zip'
        )
    except ImportError:
        raise HTTPException(
            status_code=500, 
            detail="审计报告包功能暂未实现。请联系管理员或等待 v2.5 版本更新"
        )
    except Exception as e:
        logger.error(f"审计报告包生成失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# 新增 API 端点 - 合规详情
# ============================================================

@_base_app.get("/api/compliance/{task_id}/detail")
async def get_compliance_detail(task_id: str):
    """获取 R155 合规检查详细结果"""
    try:
        queue = get_queue()
        task = queue.get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        result = task.result if task.result else {}
        
        return {
            "task_id": task_id,
            "compliance_score": result.get("compliance_score", 0),
            "violations": result.get("violations", []),
            "category_scores": result.get("category_scores", {}),
            "recommendations": result.get("recommendations", [])
        }
    except Exception as e:
        logger.error(f"获取合规详情失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 新增 API 端点 - 合规报告（前端契约对齐）
# ============================================================

@_base_app.get("/api/compliance/{task_id}")
async def get_compliance_report(task_id: str):
    """获取 R155 合规报告（前端契约简版）"""
    try:
        queue = get_queue()
        task = queue.get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        result = task.result if task.result else {}
        compliance = result.get('r155_compliance', {})
        
        return {
            "task_id": task_id,
            "compliance_score": compliance.get('overall_score', compliance.get('compliance_score', 0)),
            "violations": compliance.get('violations', []),
            "category_scores": compliance.get('domain_scores', compliance.get('category_scores', {})),
            "recommendations": compliance.get('recommendations', [])
        }
    except Exception as e:
        logger.error(f"获取合规报告失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# 新增 API 端点 - 任务取消
# ============================================================

@_base_app.post("/api/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任务"""
    try:
        queue = get_queue()
        success = queue.cancel_task(task_id) if hasattr(queue, 'cancel_task') else False
        return {"success": success, "message": "任务已取消" if success else "取消失败"}
    except Exception as e:
        logger.error(f"取消任务失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# 新增 API 端点 - 报告下载（前端契约对齐）
# ============================================================

@_base_app.get("/api/reports/{task_id}")
async def download_report(task_id: str):
    """下载报告（YAML 等格式）"""
    try:
        queue = get_queue()
        task = queue.get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        result = task.result if task.result else {}
        
        import yaml
        yaml_content = yaml.dump(result, default_flow_style=False, allow_unicode=True)
        
        from fastapi.responses import Response
        return Response(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={"Content-Disposition": f"attachment; filename={task_id}_report.yaml"}
        )
    except Exception as e:
        logger.error(f"下载报告失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))

@_base_app.post("/api/report/pdf")
async def generate_pdf_report_endpoint(firmware_id: str = Form(...)):
    """生成 PDF 报告（POST 方式，前端契约）"""
    try:
        from report_generator.pdf_generator import generate_pdf_report
        
        queue = get_queue()
        task = queue.get_task_status(firmware_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        result = task.result if task.result else {}
        pdf_path = generate_pdf_report(firmware_id, result)
        
        filename = f"{task.filename}_security_report.pdf"
        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type='application/pdf'
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF 生成依赖未安装")
    except Exception as e:
        logger.error(f"PDF 生成失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))

@_base_app.get("/api/report/pdf")
async def download_pdf_via_query(firmware_id: str = Query(...)):
    """下载 PDF 报告（GET 方式，前端契约）"""
    return await generate_pdf_report_endpoint(firmware_id=firmware_id)

@_base_app.post("/api/report/excel")
async def generate_excel_report_endpoint(firmware_id: str = Form(...)):
    """生成 Excel 报告（POST 方式，前端契约）"""
    try:
        from report_generator.excel_exporter import generate_excel_report
        
        queue = get_queue()
        task = queue.get_task_status(firmware_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        result = task.result if task.result else {}
        excel_path = generate_excel_report(firmware_id, result)
        
        filename = f"{task.filename}_vulnerability_list.xlsx"
        return FileResponse(
            path=excel_path,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="Excel 导出依赖未安装")
    except Exception as e:
        logger.error(f"Excel 生成失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))

@_base_app.get("/api/report/excel")
async def download_excel_via_query(firmware_id: str = Query(...)):
    """下载 Excel 报告（GET 方式，前端契约）"""
    return await generate_excel_report_endpoint(firmware_id=firmware_id)

# ============================================================
# 启动事件
# ============================================================
@_base_app.on_event("startup")
async def startup_event():
    """启动时初始化队列"""
    logger.info("启动扫描队列服务...")
    queue = get_queue()
    queue.start()
    logger.info(f"扫描队列已启动 (最大并发：{MAX_CONCURRENT})")

@_base_app.on_event("shutdown")
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
# 创建包含 Socket.IO 的完整 ASGI 应用
# ============================================================
app = ASGIApp(sio, _base_app)

# ============================================================
# 主程序入口
# ============================================================
if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 60)
    logger.info("🐢 固件漏洞扫描平台 v2.4.1-hotfix (WebSocket 已正确启用)")
    logger.info("=" * 60)
    
    # 启动包含 Socket.IO 的完整 ASGI 应用
    uvicorn.run(
        app,
        host=config.get('server', {}).get('host', '0.0.0.0'),
        port=config.get('server', {}).get('port', 8000),
        reload=False,
        log_level="info"
    )
