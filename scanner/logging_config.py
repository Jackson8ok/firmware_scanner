#!/usr/bin/env python3
"""
日志配置模块 - 支持轮转、分级、多输出

功能:
- 控制台输出 (INFO 及以上)
- 文件轮转 (WARNING 及以上，单个文件最大 10MB，保留 5 个)
- 错误追踪 (ERROR 及以上单独记录)
- UTF-8 编码支持
"""

import os
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logging(
    log_dir: str = "./logs",
    console_level: int = logging.INFO,
    file_level: int = logging.WARNING,
    error_file: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """
    配置全局日志系统
    
    Args:
        log_dir: 日志目录
        console_level: 控制台日志级别
        file_level: 文件日志级别
        error_file: 是否单独记录错误日志
        max_bytes: 单个日志文件最大大小 (字节)
        backup_count: 保留的备份文件数量
    
    Returns:
        根 logger 实例
    """
    # 确保日志目录存在
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 获取根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 捕获所有级别的日志
    
    # 清除现有 handler（避免重复）
    root_logger.handlers.clear()
    
    # 创建 formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 1. 控制台 Handler (INFO 及以上)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 2. 普通日志轮转 (WARNING 及以上)
    normal_log_file = log_path / "scanner.log"
    file_handler = RotatingFileHandler(
        normal_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 3. 错误日志轮转 (ERROR 及以上)
    if error_file:
        error_log_file = log_path / "error.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
    
    # 4. 审计日志 (专门记录关键操作)
    audit_log_file = log_path / "audit.log"
    audit_handler = RotatingFileHandler(
        audit_log_file,
        maxBytes=max_bytes,
        backupCount=10,  # 审计日志保留更久
        encoding='utf-8'
    )
    audit_handler.setLevel(logging.INFO)
    audit_formatter = logging.Formatter(
        fmt='%(asctime)s | AUDIT | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    audit_handler.setFormatter(audit_formatter)
    
    # 创建专门的 audit logger
    audit_logger = logging.getLogger('audit')
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)
    
    # 添加快捷函数到 module
    root_logger.info(f"📝 日志系统已初始化")
    root_logger.info(f"   日志目录：{log_path.absolute()}")
    root_logger.info(f"   控制台级别：{logging.getLevelName(console_level)}")
    root_logger.info(f"   文件级别：{logging.getLevelName(file_level)}")
    root_logger.info(f"   单文件大小：{max_bytes / 1024 / 1024:.1f} MB")
    root_logger.info(f"   保留备份数：{backup_count}")
    
    return root_logger


def get_audit_logger():
    """获取审计日志 logger"""
    return logging.getLogger('audit')


def log_audit(message: str):
    """便捷函数：记录审计日志"""
    logger = get_audit_logger()
    logger.info(message)


# 快捷命令
def rotate_logs():
    """手动触发日志轮转（调试用）"""
    for handler in logging.root.handlers[:]:
        if isinstance(handler, RotatingFileHandler):
            handler.doRollover()
            print(f"✅ 已轮转日志：{handler.baseFilename}")


if __name__ == "__main__":
    # 测试日志配置
    setup_logging()
    logger = logging.getLogger(__name__)
    audit = get_audit_logger()
    
    logger.debug("这是一个 DEBUG 消息")
    logger.info("这是一个 INFO 消息")
    logger.warning("这是一个 WARNING 消息")
    logger.error("这是一个 ERROR 消息")
    
    audit.info("审计：用户登录成功")
    audit.info("审计：文件上传完成")
    
    # 生成大量日志测试轮转
    print("\n测试生成大量日志...")
    for i in range(1000):
        logger.info(f"测试日志 {i}")
    
    print("✅ 测试完成")
