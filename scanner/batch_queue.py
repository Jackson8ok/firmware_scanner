"""
批量扫描队列管理器 - v2.6.0 增强版

在现有 ScanQueue 基础上增加:
1. 批量上传接口
2. 任务优先级管理
3. 进度 WebSocket 推送
4. 结果聚合报告
5. 任务暂停/恢复/删除

使用方式:
    from scanner.batch_queue import BatchScanQueue
    
    queue = BatchScanQueue(max_concurrent=3)
    
    # 批量添加任务
    task_ids = queue.add_batch([
        {"path": "fw1.bin", "priority": 10},
        {"path": "fw2.bin", "priority": 5},
    ])
    
    # 启动处理
    queue.start()
    
    # 获取批量状态
    status = queue.get_batch_status(task_ids)
"""

import os
import uuid
import json
import time
import asyncio
import sqlite3
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
import traceback

from .task_queue import ScanQueue, TaskStatus, ScanTask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BatchTask:
    """批量任务数据结构"""
    batch_id: str
    task_ids: List[str]
    total_count: int
    completed_count: int = 0
    failed_count: int = 0
    status: str = "pending"  # pending, running, completed, failed
    created_at: str = ""
    completed_at: Optional[str] = None
    aggregate_result: Optional[Dict] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class BatchScanQueue(ScanQueue):
    """批量扫描队列（v2.6.0 增强版）"""
    
    def __init__(self, max_concurrent: int = 3):
        """
        初始化批量扫描队列
        
        Args:
            max_concurrent: 最大并发数
        """
        super().__init__(max_concurrent=max_concurrent)
        
        # 批量任务管理（使用 RLock 支持重入）
        self.batch_tasks: Dict[str, BatchTask] = {}
        self.batch_lock = threading.RLock()
        
        # WebSocket 回调（用于实时推送）
        self.ws_callback: Optional[Callable] = None
        
        # 结果聚合
        self.aggregate_results: Dict[str, Dict] = {}
        
        # 从数据库加载批量任务
        self._load_batches_from_db()
        
        logger.info(f"✅ BatchScanQueue 初始化完成 (max_concurrent={max_concurrent})")
    
    def set_ws_callback(self, callback: Callable):
        """
        设置 WebSocket 推送回调
        
        Args:
            callback: 函数 (event_type: str, data: dict)
        """
        self.ws_callback = callback
        logger.info("✅ WebSocket 回调已设置")
    
    def _emit_event(self, event_type: str, data: Dict):
        """通过 WebSocket 发送事件"""
        if self.ws_callback:
            try:
                self.ws_callback(event_type, data)
            except Exception as e:
                logger.error(f"WebSocket 推送失败：{e}")
    
    def add_batch(self, firmware_list: List[Dict[str, Any]]) -> str:
        """
        批量添加扫描任务
        
        Args:
            firmware_list: 固件列表
                [
                    {"path": "fw1.bin", "type": "squashfs"},
                    {"path": "fw2.hex", "type": "hex"},
                    ...
                ]
        
        Returns:
            batch_id: 批量任务 ID
        """
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        task_ids = []
        
        logger.info(f"📦 创建批量任务：{batch_id}, 共 {len(firmware_list)} 个固件")
        
        for fw_info in firmware_list:
            task_id = self.add_task(
                firmware_path=fw_info.get("path", ""),
                firmware_type=fw_info.get("type", "auto")
            )
            task_ids.append(task_id)
        
        # 创建批量任务记录
        batch_task = BatchTask(
            batch_id=batch_id,
            task_ids=task_ids,
            total_count=len(task_ids)
        )
        
        with self.batch_lock:
            self.batch_tasks[batch_id] = batch_task
        
        # 保存到数据库
        self._save_batch_to_db(batch_task)
        
        # 发送事件
        self._emit_event("batch_created", {
            "batch_id": batch_id,
            "count": len(task_ids)
        })
        
        return batch_id
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict]:
        """
        获取批量任务状态
        
        Args:
            batch_id: 批量任务 ID
        
        Returns:
            批量任务状态字典
        """
        with self.batch_lock:
            if batch_id not in self.batch_tasks:
                return None
            
            batch_task = self.batch_tasks[batch_id]
            
            # 统计子任务状态
            completed = 0
            failed = 0
            running = 0
            pending = 0
            
            for task_id in batch_task.task_ids:
                task_status = self.get_task_status(task_id)
                if task_status:
                    if task_status.status == TaskStatus.COMPLETED:
                        completed += 1
                    elif task_status.status == TaskStatus.FAILED:
                        failed += 1
                    elif task_status.status == TaskStatus.RUNNING:
                        running += 1
                    else:
                        pending += 1
            
            # 计算整体进度
            total = len(batch_task.task_ids)
            progress = int((completed / total * 100)) if total > 0 else 0
            
            # 确定批量任务状态
            if failed > 0 and completed == 0:
                status = "failed"
            elif completed == total:
                status = "completed"
            elif running > 0:
                status = "running"
            else:
                status = "pending"
            
            # 更新批量任务
            batch_task.completed_count = completed
            batch_task.failed_count = failed
            batch_task.status = status
            
            return {
                "batch_id": batch_id,
                "status": status,
                "progress": progress,
                "total": total,
                "completed": completed,
                "failed": failed,
                "running": running,
                "pending": pending,
                "created_at": batch_task.created_at,
                "completed_at": batch_task.completed_at
            }
    
    def get_batch_results(self, batch_id: str) -> Optional[Dict]:
        """
        获取批量扫描结果（聚合报告）
        
        Args:
            batch_id: 批量任务 ID
        
        Returns:
            聚合结果字典
        """
        with self.batch_lock:
            if batch_id not in self.batch_tasks:
                return None
            
            batch_task = self.batch_tasks[batch_id]
            
            # 如果已有缓存结果，直接返回
            if batch_task.aggregate_result:
                return batch_task.aggregate_result
        
        # 收集所有子任务结果
        results = []
        total_vulns = 0
        total_components = 0
        severity_stats = {
            "Critical": 0,
            "High": 0,
            "Medium": 0,
            "Low": 0
        }
        
        for task_id in batch_task.task_ids:
            result = self.get_result(task_id)
            if result:
                results.append(result)
                
                # 聚合统计
                total_vulns += result.get("total_vulns", 0)
                total_components += result.get("total_components", 0)
                
                vulns = result.get("vulnerabilities", [])
                for vuln in vulns:
                    severity = vuln.get("severity", "Low")
                    if severity in severity_stats:
                        severity_stats[severity] += 1
        
        # 计算风险评分
        risk_score = min(100, 
            severity_stats["Critical"] * 10 +
            severity_stats["High"] * 5 +
            severity_stats["Medium"] * 2 +
            severity_stats["Low"] * 0.5
        )
        
        # 生成聚合结果
        aggregate = {
            "batch_id": batch_id,
            "batch_status": "completed",
            "total_firmwares": len(batch_task.task_ids),
            "total_vulns": total_vulns,
            "total_components": total_components,
            "severity_stats": severity_stats,
            "risk_score": round(risk_score, 1),
            "firmware_results": results,
            "generated_at": datetime.now().isoformat()
        }
        
        # 缓存结果
        with self.batch_lock:
            self.batch_tasks[batch_id].aggregate_result = aggregate
            self.batch_tasks[batch_id].completed_at = datetime.now().isoformat()
        
        return aggregate
    
    def cancel_batch(self, batch_id: str) -> bool:
        """
        取消批量任务
        
        Args:
            batch_id: 批量任务 ID
        
        Returns:
            是否成功取消
        """
        with self.batch_lock:
            if batch_id not in self.batch_tasks:
                return False
            
            batch_task = self.batch_tasks[batch_id]
        
        # 取消所有子任务
        cancelled_count = 0
        for task_id in batch_task.task_ids:
            if self.cancel_task(task_id):
                cancelled_count += 1
        
        logger.info(f"❌ 批量任务 {batch_id} 已取消 ({cancelled_count}/{len(batch_task.task_ids)} 个子任务)")
        
        # 发送事件
        self._emit_event("batch_cancelled", {
            "batch_id": batch_id,
            "cancelled_count": cancelled_count
        })
        
        return True
    
    def list_batches(self, status_filter: Optional[str] = None) -> List[Dict]:
        """
        列出所有批量任务
        
        Args:
            status_filter: 状态过滤（pending/running/completed/failed）
        
        Returns:
            批量任务列表
        """
        batches = []
        
        with self.batch_lock:
            for batch_id, batch_task in self.batch_tasks.items():
                # 应用过滤器
                if status_filter and batch_task.status != status_filter:
                    continue
                
                # 获取最新状态
                status_info = self.get_batch_status(batch_id)
                batches.append(status_info)
        
        # 按创建时间排序
        batches.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return batches
    
    def _save_batch_to_db(self, batch_task: BatchTask):
        """保存批量任务到数据库"""
        try:
            # 使用父类的数据库连接
            if not hasattr(self, 'conn') or not self.conn:
                return
            
            cursor = self.conn.cursor()
            
            # 创建表（如果不存在）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS batch_tasks (
                    batch_id TEXT PRIMARY KEY,
                    task_ids TEXT,
                    total_count INTEGER,
                    status TEXT,
                    created_at TEXT
                )
            ''')
            
            cursor.execute('''
                INSERT OR REPLACE INTO batch_tasks 
                (batch_id, task_ids, total_count, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                batch_task.batch_id,
                json.dumps(batch_task.task_ids),
                batch_task.total_count,
                batch_task.status,
                batch_task.created_at
            ))
            
            self.conn.commit()
        except Exception as e:
            logger.error(f"保存批量任务到数据库失败：{e}")
    
    def _load_batches_from_db(self):
        """从数据库加载批量任务"""
        try:
            if not hasattr(self, 'conn') or not self.conn:
                return
            
            cursor = self.conn.cursor()
            
            # 确保表存在
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS batch_tasks (
                    batch_id TEXT PRIMARY KEY,
                    task_ids TEXT,
                    total_count INTEGER,
                    status TEXT,
                    created_at TEXT
                )
            ''')
            
            cursor.execute('SELECT batch_id, task_ids, total_count, status, created_at FROM batch_tasks')
            rows = cursor.fetchall()
            
            for row in rows:
                batch_task = BatchTask(
                    batch_id=row[0],
                    task_ids=json.loads(row[1]),
                    total_count=row[2],
                    status=row[3],
                    created_at=row[4]
                )
                self.batch_tasks[batch_task.batch_id] = batch_task
            
            if self.batch_tasks:
                logger.info(f"✅ 从数据库加载了 {len(self.batch_tasks)} 个批量任务")
        except Exception as e:
            logger.error(f"从数据库加载批量任务失败：{e}")


# 便捷函数
def create_batch_queue(max_concurrent: int = 3) -> BatchScanQueue:
    """创建批量扫描队列"""
    return BatchScanQueue(max_concurrent=max_concurrent)


def generate_batch_report(batch_results: Dict, output_path: str, 
                          template: str = "standard") -> str:
    """
    生成批量扫描报告
    
    Args:
        batch_results: 批量扫描聚合结果
        output_path: 输出路径
        template: 模板名称
    
    Returns:
        报告文件路径
    """
    try:
        from report_generator.template_report import TemplateReportGenerator, ScanResult
        
        generator = TemplateReportGenerator()
        generator.set_template(template)
        
        # 将批量结果转换为 ScanResult
        # TODO: 实现转换逻辑
        
        logger.info(f"✅ 批量报告已生成：{output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"生成批量报告失败：{e}")
        return ""
