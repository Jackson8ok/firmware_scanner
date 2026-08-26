"""
批量扫描 API - v2.6.0 新特性

提供 REST API 端点用于批量上传和扫描固件

端点:
    POST   /api/scan/batch            - 批量上传固件
    GET    /api/scan/batch            - 列出所有批量任务
    GET    /api/scan/batch/:id        - 获取批量任务状态
    GET    /api/scan/batch/:id/result - 获取批量扫描结果
    DELETE /api/scan/batch/:id        - 删除批量任务
    POST   /api/scan/batch/:id/cancel - 取消批量任务
    GET    /api/scan/queue            - 查看队列状态
    WS     /ws/progress               - WebSocket 进度推送
"""

from flask import Blueprint, request, jsonify, send_file
from flask_cors import CORS
import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from scanner.batch_queue import BatchScanQueue
    BATCH_AVAILABLE = True
except ImportError:
    BATCH_AVAILABLE = False
    print("⚠️ 批量扫描模块未加载")

# 创建 Blueprint
batch_bp = Blueprint('batch_scan', __name__, url_prefix='/api/scan')
CORS(batch_bp)

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


@batch_bp.route('/batch', methods=['POST'])
def upload_batch():
    """
    批量上传固件并创建扫描任务
    
    Request Body (multipart/form-data):
        files: 固件文件列表（支持 10+ 个文件）
        priority: 优先级（可选，默认 5）
    
    Returns:
        JSON: {
            "success": true,
            "batch_id": "batch_xxx",
            "task_count": 10,
            "task_ids": ["task_1", "task_2", ...]
        }
    """
    if not BATCH_AVAILABLE:
        return jsonify({"error": "批量扫描模块不可用"}), 503
    
    queue = get_batch_queue()
    
    # 获取上传的文件
    files = request.files.getlist('files')
    if not files:
        return jsonify({"error": "请上传至少一个固件文件"}), 400
    
    # 获取优先级
    priority = int(request.form.get('priority', 5))
    
    # 保存文件并创建任务
    upload_dir = Path("/mnt/workspace/firmware_scanner/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    firmware_list = []
    for file in files:
        if file.filename:
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_name = f"{timestamp}_{uuid.uuid4().hex[:8]}_{file.filename}"
            file_path = upload_dir / unique_name
            
            # 保存文件
            file.save(str(file_path))
            
            # 添加到列表
            firmware_list.append({
                "path": str(file_path),
                "type": "auto",  # 自动检测类型
                "priority": priority
            })
    
    # 创建批量任务
    batch_id = queue.add_batch(firmware_list, base_priority=priority)
    
    # 返回结果
    return jsonify({
        "success": True,
        "batch_id": batch_id,
        "task_count": len(firmware_list),
        "message": f"已创建 {len(firmware_list)} 个扫描任务"
    })


@batch_bp.route('/batch', methods=['GET'])
def list_batches():
    """
    列出所有批量任务
    
    Query Params:
        status: 状态过滤（pending/running/completed/failed）
    
    Returns:
        JSON: {
            "success": true,
            "batches": [...],
            "count": 10
        }
    """
    if not BATCH_AVAILABLE:
        return jsonify({"error": "批量扫描模块不可用"}), 503
    
    queue = get_batch_queue()
    status_filter = request.args.get('status')
    
    batches = queue.list_batches(status_filter)
    
    return jsonify({
        "success": True,
        "batches": batches,
        "count": len(batches)
    })


@batch_bp.route('/batch/<batch_id>', methods=['GET'])
def get_batch_status(batch_id: str):
    """
    获取批量任务状态
    
    Args:
        batch_id: 批量任务 ID
    
    Returns:
        JSON: {
            "success": true,
            "batch_id": "batch_xxx",
            "status": "running",
            "progress": 45,
            "total": 10,
            "completed": 4,
            "failed": 0,
            "running": 2,
            "pending": 4
        }
    """
    if not BATCH_AVAILABLE:
        return jsonify({"error": "批量扫描模块不可用"}), 503
    
    queue = get_batch_queue()
    status = queue.get_batch_status(batch_id)
    
    if not status:
        return jsonify({"error": "批量任务不存在"}), 404
    
    return jsonify({
        "success": True,
        **status
    })


@batch_bp.route('/batch/<batch_id>/result', methods=['GET'])
def get_batch_result(batch_id: str):
    """
    获取批量扫描结果（聚合报告）
    
    Args:
        batch_id: 批量任务 ID
    
    Returns:
        JSON: 聚合扫描结果
    """
    if not BATCH_AVAILABLE:
        return jsonify({"error": "批量扫描模块不可用"}), 503
    
    queue = get_batch_queue()
    
    # 检查任务是否完成
    status = queue.get_batch_status(batch_id)
    if not status or status["status"] != "completed":
        return jsonify({
            "error": "任务未完成",
            "status": status["status"] if status else "not_found"
        }), 400
    
    # 获取聚合结果
    result = queue.get_batch_results(batch_id)
    
    return jsonify({
        "success": True,
        "result": result
    })


@batch_bp.route('/batch/<batch_id>', methods=['DELETE'])
def delete_batch(batch_id: str):
    """
    删除批量任务
    
    Args:
        batch_id: 批量任务 ID
    
    Returns:
        JSON: {
            "success": true,
            "message": "任务已删除"
        }
    """
    if not BATCH_AVAILABLE:
        return jsonify({"error": "批量扫描模块不可用"}), 503
    
    queue = get_batch_queue()
    
    # 先取消任务
    queue.cancel_batch(batch_id)
    
    # TODO: 从数据库删除记录
    
    return jsonify({
        "success": True,
        "message": "任务已删除"
    })


@batch_bp.route('/batch/<batch_id>/cancel', methods=['POST'])
def cancel_batch(batch_id: str):
    """
    取消批量任务
    
    Args:
        batch_id: 批量任务 ID
    
    Returns:
        JSON: {
            "success": true,
            "cancelled_count": 8
        }
    """
    if not BATCH_AVAILABLE:
        return jsonify({"error": "批量扫描模块不可用"}), 503
    
    queue = get_batch_queue()
    success = queue.cancel_batch(batch_id)
    
    if success:
        return jsonify({
            "success": True,
            "message": "任务已取消"
        })
    else:
        return jsonify({
            "error": "取消失败"
        }), 400


@batch_bp.route('/queue', methods=['GET'])
def get_queue_status():
    """
    查看队列状态
    
    Returns:
        JSON: {
            "success": true,
            "queue_size": 5,
            "running_count": 3,
            "max_concurrent": 3,
            "tasks": [...]
        }
    """
    if not BATCH_AVAILABLE:
        return jsonify({"error": "批量扫描模块不可用"}), 503
    
    queue = get_batch_queue()
    
    # 获取队列统计
    stats = {
        "queue_size": len(queue.task_queue),
        "running_count": len(queue.active_tasks),
        "max_concurrent": queue.max_concurrent,
        "completed_count": queue.completed_count,
        "failed_count": queue.failed_count
    }
    
    return jsonify({
        "success": True,
        "stats": stats
    })


@batch_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "batch_available": BATCH_AVAILABLE,
        "version": "v2.6.0"
    })


# WebSocket 处理（需要 Flask-SocketIO）
def setup_websocket(app):
    """
    设置 WebSocket 实时推送
    
    使用方式:
        from flask_socketio import SocketIO
        socketio = SocketIO(app, cors_allowed_origins="*")
        setup_websocket(socketio)
    """
    try:
        from flask_socketio import SocketIO, emit
        
        if isinstance(app, SocketIO):
            socketio = app
        else:
            socketio = SocketIO(app, cors_allowed_origins="*")
        
        @socketio.on('connect')
        def handle_connect():
            print(f"🔌 客户端已连接：{request.sid}")
        
        @socketio.on('disconnect')
        def handle_disconnect():
            print(f"🔌 客户端已断开：{request.sid}")
        
        # 设置队列的 WebSocket 回调
        queue = get_batch_queue()
        if queue:
            def ws_callback(event_type: str, data: dict):
                socketio.emit(event_type, data)
            queue.set_ws_callback(ws_callback)
        
        print("✅ WebSocket 已设置")
        return socketio
        
    except ImportError:
        print("⚠️ Flask-SocketIO 未安装，WebSocket 不可用")
        return None


# 注册 Blueprint
def register_batch_api(app):
    """将批量扫描 API 注册到 Flask 应用"""
    if hasattr(app, 'register_blueprint'):
        app.register_blueprint(batch_bp)
        print("✅ 批量扫描 API 已注册：/api/scan/*")
    else:
        print("⚠️ 无法注册批量扫描 API - 应用对象无效")
