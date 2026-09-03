#!/usr/bin/env python3
"""
统一错误处理模块 - 结构化错误响应

提供:
- 标准化错误码
- 结构化错误响应模型
- 异常拦截器
- 用户友好的错误消息
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging
import traceback

logger = logging.getLogger(__name__)


# ============================================================
# 错误码定义
# ============================================================
class ErrorCode:
    """错误码常量"""
    # 通用错误 (1000-1999)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    
    # 文件相关 (2000-2999)
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    FILE_UPLOAD_FAILED = "FILE_UPLOAD_FAILED"
    FILE_PROCESS_FAILED = "FILE_PROCESS_FAILED"
    
    # 扫描相关 (3000-3999)
    SCAN_FAILED = "SCAN_FAILED"
    SCAN_TIMEOUT = "SCAN_TIMEOUT"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_CANCELLED = "TASK_CANCELLED"
    QUEUE_FULL = "QUEUE_FULL"
    
    # 报告相关 (4000-4999)
    REPORT_GENERATION_FAILED = "REPORT_GENERATION_FAILED"
    REPORT_NOT_FOUND = "REPORT_NOT_FOUND"
    REPORT_FORMAT_UNSUPPORTED = "REPORT_FORMAT_UNSUPPORTED"
    
    # 依赖相关 (5000-5999)
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"


# ============================================================
# 错误响应模型
# ============================================================
class ErrorResponse(BaseModel):
    """标准化错误响应"""
    code: str           # 错误码
    message: str        # 用户友好消息
    details: Optional[str] = None  # 技术详情（调试用）
    suggestion: Optional[str] = None  # 解决建议
    task_id: Optional[str] = None   # 关联的任务 ID
    timestamp: str = None  # 时间戳
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "FILE_TOO_LARGE",
                "message": "文件大小超过限制 (最大 500MB)",
                "details": "上传的文件大小为 650MB",
                "suggestion": "请压缩固件文件或联系管理员增加限制",
                "task_id": None,
                "timestamp": "2026-08-03T15:30:45Z"
            }
        }


# ============================================================
# 自定义异常类
# ============================================================
class AppException(Exception):
    """应用基础异常"""
    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[str] = None,
        suggestion: Optional[str] = None,
        status_code: int = 500,
        task_id: Optional[str] = None
    ):
        self.code = code
        self.message = message
        self.details = details
        self.suggestion = suggestion
        self.status_code = status_code
        self.task_id = task_id
        super().__init__(message)


class FileUploadError(AppException):
    """文件上传错误"""
    def __init__(self, message: str, details: str = None, size_limit: int = None):
        super().__init__(
            code=ErrorCode.FILE_UPLOAD_FAILED,
            message=message,
            details=details,
            suggestion=f"确保文件大小不超过 {size_limit or 500}MB"
        )


class ScanError(AppException):
    """扫描错误"""
    def __init__(self, message: str, details: str = None, task_id: str = None):
        super().__init__(
            code=ErrorCode.SCAN_FAILED,
            message=message,
            details=details,
            suggestion="检查固件格式是否正确或联系技术支持",
            task_id=task_id
        )


class TaskNotFoundError(AppException):
    """任务不存在"""
    def __init__(self, task_id: str):
        super().__init__(
            code=ErrorCode.TASK_NOT_FOUND,
            message=f"任务 {task_id} 不存在",
            suggestion="请检查任务 ID 是否正确",
            task_id=task_id,
            status_code=404
        )


# ============================================================
# 异常处理器
# ============================================================
async def app_exception_handler(request: Request, exc: AppException):
    """应用异常处理器"""
    logger.error(f"[{exc.code}] {exc.message}")
    if exc.details:
        logger.debug(f"Details: {exc.details}")
    
    response_data = ErrorResponse(
        code=exc.code,
        message=exc.message,
        details=exc.details if request.url.path.endswith('/debug') else None,
        suggestion=exc.suggestion,
        task_id=exc.task_id,
        timestamp=datetime.utcnow().isoformat()
    ).dict()
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 异常处理器"""
    # 将 FastAPI 的 HTTPException 转换为标准化格式
    from datetime import datetime
    
    # 如果是我们的自定义错误，保持原样
    if isinstance(exc.detail, dict) and 'code' in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    
    # 否则转换为标准格式
    response_data = ErrorResponse(
        code=getattr(exc, 'code', ErrorCode.INTERNAL_ERROR),
        message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        suggestion="请稍后重试或联系技术支持",
        timestamp=datetime.utcnow().isoformat()
    ).dict()
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """通用异常处理器（兜底）"""
    logger.exception(f"未捕获异常：{str(exc)}")
    
    # 记录完整堆栈
    stack_trace = traceback.format_exc()
    
    response_data = ErrorResponse(
        code=ErrorCode.INTERNAL_ERROR,
        message="服务器内部错误，请联系技术支持",
        details=stack_trace if request.url.path.endswith('/debug') else None,
        suggestion="请提供请求 ID 和技术支持",
        timestamp=datetime.utcnow().isoformat()
    ).dict()
    
    return JSONResponse(
        status_code=500,
        content=response_data
    )


# ============================================================
# 便捷函数
# ============================================================
def raise_file_not_found(filename: str, suggestion: str = None):
    """抛出文件未找到异常"""
    raise AppException(
        code=ErrorCode.FILE_NOT_FOUND,
        message=f"文件不存在：{filename}",
        details=f"路径：{Path(filename).absolute()}",
        suggestion=suggestion or "请检查文件路径是否正确",
        status_code=404
    )


def raise_file_too_large(filename: str, file_size: int, limit: int = 500 * 1024 * 1024):
    """抛出文件过大异常"""
    raise AppException(
        code=ErrorCode.FILE_TOO_LARGE,
        message=f"文件大小超过限制 ({limit / 1024 / 1024:.0f}MB)",
        details=f"{filename}: {file_size / 1024 / 1024:.1f}MB",
        suggestion=f"请使用小于 {limit / 1024 / 1024:.0f}MB 的固件文件",
        status_code=413
    )


def raise_invalid_format(filename: str, expected_formats: list):
    """抛出格式无效异常"""
    raise AppException(
        code=ErrorCode.INVALID_FILE_FORMAT,
        message="不支持的固件格式",
        details=f"文件 {filename} 不是有效的固件格式",
        suggestion=f"支持的格式：{', '.join(expected_formats)}",
        status_code=400
    )


def raise_scan_timeout(task_id: str, duration: int):
    """抛出扫描超时异常"""
    raise AppException(
        code=ErrorCode.SCAN_TIMEOUT,
        message=f"扫描超时 ({duration}s)",
        task_id=task_id,
        suggestion="固件可能过大或系统负载较高，请稍后重试",
        status_code=408
    )


# 导入 datetime 用于时间戳
from datetime import datetime
from pathlib import Path
