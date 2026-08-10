"""
FastAPI + Socket.IO 正确集成方案
参考：https://python-socketio.github.io/python-socketio/5.11/integrations.html#fastapi
"""

import socketio
from fastapi import FastAPI
from starlette.routing import Mount, Route
from socketio import ASGIApp

# 创建 Socket.IO 服务器
sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    async_mode="asgi"
)

# Socket.IO 事件处理器
@sio.event
async def connect(sid, environ, auth):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

# 方式 1: 创建独立的 ASGI 应用用于 Socket.IO
socketio_app = ASGIApp(sio)

# 创建 FastAPI 应用
fastapi_app = FastAPI()

# 将 Socket.IO 挂载为路由
routes = [
    Route("/", endpoint=home),  # 首页
    Mount("/socket.io/", app=socketio_app),  # Socket.IO 端点
]

fastapi_app.router.routes = routes

def home(request):
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content="<h1>Hello World</h1>")

# 最终的应用是 FastAPI + Socket.IO 的组合
app = fastapi_app


# 或者方式 2: 更简洁的直接包装
def create_app_with_socketio(fastapi_app, sio_server):
    """将 Socket.IO 和 FastAPI 包装成统一 ASGI 应用"""
    
    async def app(scope, receive, send):
        if scope["type"] == "http":
            await fastapi_app(scope, receive, send)
        elif scope["type"] == "websocket":
            # 处理 WebSocket 请求（Socket.IO）
            await sio_server.handle_connection(scope, receive, send)
        else:
            await fastapi_app(scope, receive, send)
    
    return app
