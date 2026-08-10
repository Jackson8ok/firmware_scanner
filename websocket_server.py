#!/usr/bin/env python3
"""
固件漏洞扫描平台 - WebSocket 实时通知服务器

功能:
- 任务进度实时更新
- 队列状态同步
- 扫描结果推送
- 多房间管理（每个任务一个房间）
- 断线重连支持

技术栈:
- FastAPI + WebSockets
- asyncio
- starlette.websockets.WebSocket
"""

import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 项目根目录
ROOT_DIR = Path(__file__).parent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("websocket_server")


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # 所有活跃连接
        self.active_connections: Set[WebSocket] = set()
        
        # 按任务 ID 分组的连接
        self.task_connections: Dict[str, Set[WebSocket]] = {}
        
        # 用户会话映射（可选）
        self.user_sessions: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, task_id: Optional[str] = None):
        """接受 WebSocket 连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if task_id:
            if task_id not in self.task_connections:
                self.task_connections[task_id] = set()
            self.task_connections[task_id].add(websocket)
        
        logger.info(f"✅ WebSocket 连接建立，任务：{task_id}, 总连接数：{len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket, task_id: Optional[str] = None):
        """断开连接并清理"""
        self.active_connections.discard(websocket)
        
        if task_id and task_id in self.task_connections:
            self.task_connections[task_id].discard(websocket)
            if not self.task_connections[task_id]:
                del self.task_connections[task_id]
        
        logger.info(f"❌ WebSocket 断开，任务：{task_id}, 剩余连接数：{len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息给单个连接"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送消息失败：{e}")
            self.disconnect(websocket)
    
    async def broadcast_to_task(self, task_id: str, message: dict):
        """广播消息到特定任务的所有连接"""
        if task_id not in self.task_connections:
            return
        
        disconnected = []
        for websocket in self.task_connections[task_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"发送失败，标记为断开：{e}")
                disconnected.append(websocket)
        
        # 清理断开的连接
        for ws in disconnected:
            self.disconnect(ws, task_id)
    
    async def broadcast_all(self, message: dict):
        """广播消息到所有连接"""
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"广播失败：{e}")
                disconnected.append(websocket)
        
        for ws in disconnected:
            self.disconnect(ws)
    
    def get_task_connection_count(self, task_id: str) -> int:
        """获取特定任务的连接数"""
        if task_id not in self.task_connections:
            return 0
        return len(self.task_connections[task_id])
    
    def get_total_connection_count(self) -> int:
        """获取总连接数"""
        return len(self.active_connections)


# 全局连接管理器
manager = ConnectionManager()


async def handle_websocket_messages(websocket: WebSocket, task_id: Optional[str]):
    """处理 WebSocket 消息循环"""
    try:
        while True:
            # 等待客户端消息
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                msg_type = message.get('type', 'ping')
                
                # 响应不同类型的消息
                if msg_type == 'ping':
                    await manager.send_personal_message({
                        'type': 'pong',
                        'timestamp': datetime.now().isoformat()
                    }, websocket)
                
                elif msg_type == 'subscribe':
                    new_task_id = message.get('task_id')
                    if new_task_id:
                        # 订阅新任务
                        await manager.broadcast_to_task(
                            new_task_id,
                            {
                                'type': 'subscribed',
                                'task_id': new_task_id,
                                'message': f'已订阅任务 {new_task_id}'
                            }
                        )
                
                elif msg_type == 'unsubscribe':
                    # 取消订阅（逻辑上移除即可）
                    pass
                
                else:
                    logger.debug(f"收到消息类型：{msg_type}")
                    
            except json.JSONDecodeError:
                logger.warning(f"无效 JSON 消息：{data}")
            except Exception as e:
                logger.error(f"处理消息失败：{e}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, task_id)
    except Exception as e:
        logger.error(f"WebSocket 错误：{e}")
        manager.disconnect(websocket, task_id)


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="Firmware Scanner WebSocket Server",
        description="实时推送扫描任务进度和状态",
        version="1.0.0"
    )
    
    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应该限制
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("🚀 WebSocket 服务器启动...")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("⬇️ WebSocket 服务器关闭中...")
        # 关闭所有连接
        for websocket in list(manager.active_connections):
            await websocket.close()
    
    @app.websocket("/ws/{task_id}")
    async def websocket_endpoint(websocket: WebSocket, task_id: str):
        """WebSocket 端点"""
        await manager.connect(websocket, task_id)
        await handle_websocket_messages(websocket, task_id)
    
    @app.websocket("/ws")
    async def websocket_general_endpoint(websocket: WebSocket):
        """通用 WebSocket 端点（不绑定任务）"""
        await manager.connect(websocket, None)
        await handle_websocket_messages(websocket, None)
    
    @app.get("/ws/stats")
    async def get_ws_stats():
        """获取 WebSocket 统计信息"""
        return {
            "total_connections": manager.get_total_connection_count(),
            "active_tasks": len(manager.task_connections),
            "task_stats": {
                task_id: len(conns) 
                for task_id, conns in manager.task_connections.items()
            }
        }
    
    @app.get("/")
    async def root():
        """健康检查"""
        return {
            "status": "healthy",
            "service": "Firmware Scanner WebSocket",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
    
    return app


# 创建应用实例
app = create_app()


# ============================================================
# 辅助函数：从其他地方调用 WebSocket 广播
# ============================================================

async def notify_task_progress(task_id: str, progress: int, message: str, details: dict = None):
    """通知任务进度更新"""
    await manager.broadcast_to_task(task_id, {
        'type': 'progress_update',
        'task_id': task_id,
        'progress': progress,
        'message': message,
        'details': details or {},
        'timestamp': datetime.now().isoformat()
    })


async def notify_task_status(task_id: str, status: str, result: dict = None):
    """通知任务状态变更"""
    await manager.broadcast_to_task(task_id, {
        'type': 'status_change',
        'task_id': task_id,
        'status': status,  # 'pending', 'queued', 'running', 'completed', 'failed'
        'result': result or {},
        'timestamp': datetime.now().isoformat()
    })


async def notify_queue_stats(stats: dict):
    """通知队列统计更新"""
    await manager.broadcast_all({
        'type': 'queue_stats',
        'stats': stats,
        'timestamp': datetime.now().isoformat()
    })


async def notify_scan_error(task_id: str, error_message: str):
    """通知扫描错误"""
    await manager.broadcast_to_task(task_id, {
        'type': 'error',
        'task_id': task_id,
        'error': error_message,
        'timestamp': datetime.now().isoformat()
    })


# ============================================================
# 独立运行模式（用于测试）
# ============================================================

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║     固件漏洞扫描平台 - WebSocket 实时通知服务器              ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  📡 端口：8765                                             ║
    ║  🔗 连接地址：ws://localhost:8765/ws/{task_id}             ║
    ║  📊 统计地址：http://localhost:8765/ws/stats               ║
    ║  ❤️  健康检查：http://localhost:8765                       ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8765,
        log_level="info"
    )


# ============================================================
# 集成示例：如何在现有代码中使用
# ============================================================

"""
# 在 scanner/task_queue.py 或其他地方集成:

from websocket_server import (
    notify_task_progress,
    notify_task_status,
    notify_scan_error
)

# 在扫描过程中更新进度
async def scan_firmware(task):
    # ...
    await notify_task_progress(
        task_id=task.id,
        progress=50,
        message="正在提取固件组件...",
        details={"current_stage": "extracting"}
    )
    # ...
    await notify_task_progress(
        task_id=task.id,
        progress=100,
        message="扫描完成！",
        details={"vulnerabilities_found": 15}
    )
    
    # 完成任务
    await notify_task_status(
        task_id=task.id,
        status="completed",
        result=task.result
    )
"""
