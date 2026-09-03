"""
批量扫描 API - v2.6.0 新特性 (FastAPI 版本)

提供 REST API 端点用于批量上传和扫描固件

端点:
    POST   /api/scan/batch            - 批量上传固件
    GET    /api/scan/batch            - 列出所有批量任务
    GET    /api/scan/batch/:id        - 获取批量任务状态
    GET    /api/scan/batch/:id/result - 获取批量扫描结果
    DELETE /api/scan/batch/:id        - 删除批量任务
    POST   /api/scan/batch/:id/cancel - 取消批量任务
    GET    /api/scan/queue            - 查看队列状态
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

try:
    from scanner.batch_queue import BatchScanQueue
    BATCH_AVAILABLE = True
except ImportError:
    BATCH_AVAILABLE = False
    print("⚠️ 批量扫描模块未加载")

# 创建 FastAPI Router
batch_router = APIRouter(prefix="/api/scan", tags=["batch_scan"])

# 全局队列实例
_batch_queue: Optional[BatchScanQueue] = None


def get_batch_queue() -> Optional[BatchScanQueue]:
    """获取批量扫描队列单例"""
    global _batch_queue
    if not BATCH_AVAILABLE:
        return None
    if _batch_queue is None:
        _batch_queue = BatchScanQueue(max_concurrent=3)
        _batch_queue.start()
    return _batch_queue


@batch_router.post("/batch")
async def upload_batch(
    files: List[UploadFile] = File(..., description="固件文件列表"),
    priority: int = Form(default=5, description="优先级")
):
    """批量上传固件并创建扫描任务"""
    if not BATCH_AVAILABLE:
        raise HTTPException(status_code=503, detail="批量扫描模块不可用")
    
    queue = get_batch_queue()
    
    if not files:
        raise HTTPException(status_code=400, detail="请上传至少一个固件文件")
    
    # 保存文件并创建任务
    upload_dir = Path("/mnt/workspace/firmware_scanner/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    firmware_list = []
    for file in files:
        if file.filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_name = f"{timestamp}_{uuid.uuid4().hex[:8]}_{file.filename}"
            file_path = upload_dir / unique_name
            
            content = await file.read()
            with open(file_path, 'wb') as f:
                f.write(content)
            
            firmware_list.append({
                "path": str(file_path),
                "type": "auto"
            })
    
    batch_id = queue.add_batch(firmware_list)
    
    return {
        "success": True,
        "batch_id": batch_id,
        "task_count": len(firmware_list),
        "message": f"已创建 {len(firmware_list)} 个扫描任务"
    }


@batch_router.get("/batch")
async def list_batches(status: Optional[str] = Query(None, description="状态过滤")):
    """列出所有批量任务"""
    if not BATCH_AVAILABLE:
        raise HTTPException(status_code=503, detail="批量扫描模块不可用")
    
    queue = get_batch_queue()
    batches = queue.list_batches(status_filter=status)
    
    return {
        "success": True,
        "batches": batches,
        "count": len(batches)
    }


@batch_router.get("/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """获取批量任务状态"""
    if not BATCH_AVAILABLE:
        raise HTTPException(status_code=503, detail="批量扫描模块不可用")
    
    queue = get_batch_queue()
    status = queue.get_batch_status(batch_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="批量任务不存在")
    
    return {
        "success": True,
        **status
    }


@batch_router.get("/batch/{batch_id}/result")
async def get_batch_result(batch_id: str):
    """获取批量扫描结果（聚合报告）"""
    if not BATCH_AVAILABLE:
        raise HTTPException(status_code=503, detail="批量扫描模块不可用")
    
    queue = get_batch_queue()
    
    status = queue.get_batch_status(batch_id)
    if not status or status["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"任务未完成，当前状态：{status['status'] if status else 'not_found'}"
        )
    
    result = queue.get_batch_results(batch_id)
    
    return {
        "success": True,
        "result": result
    }


@batch_router.delete("/batch/{batch_id}")
async def delete_batch(batch_id: str):
    """删除批量任务"""
    if not BATCH_AVAILABLE:
        raise HTTPException(status_code=503, detail="批量扫描模块不可用")
    
    queue = get_batch_queue()
    queue.cancel_batch(batch_id)
    
    return {
        "success": True,
        "message": "任务已删除"
    }


@batch_router.post("/batch/{batch_id}/cancel")
async def cancel_batch(batch_id: str):
    """取消批量任务"""
    if not BATCH_AVAILABLE:
        raise HTTPException(status_code=503, detail="批量扫描模块不可用")
    
    queue = get_batch_queue()
    success = queue.cancel_batch(batch_id)
    
    if success:
        return {"success": True, "message": "任务已取消"}
    else:
        raise HTTPException(status_code=400, detail="取消失败")


@batch_router.get("/queue")
async def get_queue_status():
    """查看队列状态"""
    if not BATCH_AVAILABLE:
        raise HTTPException(status_code=503, detail="批量扫描模块不可用")
    
    queue = get_batch_queue()
    
    stats = {
        "queue_size": len(queue.task_queue) if hasattr(queue, 'task_queue') else 0,
        "running_count": len(queue.active_tasks) if hasattr(queue, 'active_tasks') else 0,
        "max_concurrent": queue.max_concurrent,
        "completed_count": queue.completed_count if hasattr(queue, 'completed_count') else 0,
        "failed_count": queue.failed_count if hasattr(queue, 'failed_count') else 0
    }
    
    return {
        "success": True,
        "stats": stats
    }


@batch_router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "batch_available": BATCH_AVAILABLE,
        "version": "v2.6.0"
    }


# 注册函数（供 main.py 调用）
def register_batch_api(app):
    """将批量扫描 API 注册到 FastAPI 应用"""
    app.include_router(batch_router)
    print("✅ 批量扫描 API 已注册：/api/scan/*")
