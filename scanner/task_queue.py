#!/usr/bin/env python3
"""
固件扫描任务队列管理器

功能:
1. 任务队列管理（先进先出）
2. 并发扫描控制
3. 任务状态跟踪
4. 进度实时更新
5. 错误处理和重试

使用方法:
    from scanner.task_queue import ScanQueue, TaskStatus
    
    # 初始化队列
    queue = ScanQueue(max_concurrent=3)
    
    # 添加扫描任务
    task_id_1 = queue.add_task("firmware1.bin", "squashfs")
    task_id_2 = queue.add_task("firmware2.hex", "hex")
    
    # 启动处理
    queue.start()
    
    # 检查进度
    status = queue.get_task_status(task_id_1)
    print(f"进度：{status.progress}% - {status.status}")
    
    # 等待完成
    queue.wait_for_completion(task_id_1)
    result = queue.get_result(task_id_1)
    
    # 停止服务
    queue.stop()
"""

import os
import uuid
import json
import time
import sqlite3
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
import traceback

# 导入扫描引擎和合规检查器
from .engine import FirmwareExtractor, SBOMGenerator, CVEMatcher
from .r155_compliance import get_r155_checker
from compliance.r155_rules import check_r155_compliance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"        # 等待中
    QUEUED = "queued"          # 已排队
    RUNNING = "running"        # 执行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消


@dataclass
class ScanTask:
    """扫描任务数据结构"""
    task_id: str
    firmware_path: str
    firmware_type: str
    filename: str
    status: TaskStatus
    progress: int  # 0-100
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[Dict] = None
    worker_id: Optional[int] = None
    
    def to_dict(self):
        return {
            'task_id': self.task_id,
            'firmware_path': self.firmware_path,
            'firmware_type': self.firmware_type,
            'filename': self.filename,
            'status': self.status.value,
            'progress': self.progress,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'error_message': self.error_message,
            'result': self.result,
            'worker_id': self.worker_id
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'ScanTask':
        data['status'] = TaskStatus(data['status'])
        return ScanTask(**data)


class TaskDatabase:
    """任务数据库（SQLite）"""
    
    def __init__(self, db_path: str = "./data/tasks.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._connect()
        self._init_schema()
    
    def _connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"任务数据库已连接：{self.db_path}")
    
    def _init_schema(self):
        """初始化表结构"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_tasks (
                task_id TEXT PRIMARY KEY,
                firmware_path TEXT NOT NULL,
                firmware_type TEXT NOT NULL,
                filename TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                result_json TEXT,
                worker_id INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status 
            ON scan_tasks(status, created_at DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_created 
            ON scan_tasks(created_at DESC)
        """)
        
        self.conn.commit()
        logger.info("任务数据库 schema 初始化完成")
    
    def save_task(self, task: ScanTask):
        """保存任务"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO scan_tasks 
            (task_id, firmware_path, firmware_type, filename, status, progress,
             created_at, started_at, completed_at, error_message, result_json, worker_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.task_id, task.firmware_path, task.firmware_type, task.filename,
            task.status.value, task.progress, task.created_at, task.started_at,
            task.completed_at, task.error_message,
            json.dumps(task.result) if task.result else None,
            task.worker_id
        ))
        
        self.conn.commit()
    
    def get_task(self, task_id: str) -> Optional[ScanTask]:
        """获取单个任务"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT * FROM scan_tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        
        if row:
            data = dict(row)
            data['result'] = json.loads(data['result_json']) if data['result_json'] else None
            del data['result_json']
            return ScanTask.from_dict(data)
        
        return None
    
    def get_all_tasks(self, limit: int = 100, status: Optional[TaskStatus] = None) -> List[ScanTask]:
        """获取所有任务（分页）"""
        cursor = self.conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT * FROM scan_tasks 
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (status.value, limit))
        else:
            cursor.execute("""
                SELECT * FROM scan_tasks 
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        
        tasks = []
        for row in cursor.fetchall():
            data = dict(row)
            data['result'] = json.loads(data['result_json']) if data['result_json'] else None
            del data['result_json']
            tasks.append(ScanTask.from_dict(data))
        
        return tasks
    
    def get_pending_tasks(self) -> List[ScanTask]:
        """获取待处理任务"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM scan_tasks 
            WHERE status IN ('pending', 'queued')
            ORDER BY created_at ASC
            LIMIT 100
        """)
        
        tasks = []
        for row in cursor.fetchall():
            data = dict(row)
            data['result'] = json.loads(data['result_json']) if data['result_json'] else None
            del data['result_json']
            tasks.append(ScanTask.from_dict(data))
        
        return tasks
    
    def delete_old_completed_tasks(self, days: int = 7) -> int:
        """清理旧的任务记录"""
        cutoff_date = datetime.now().timestamp() - (days * 86400)
        cutoff_str = datetime.fromtimestamp(cutoff_date).isoformat()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM scan_tasks 
            WHERE status IN ('completed', 'failed') 
            AND completed_at < ?
        """, (cutoff_str,))
        
        deleted_count = cursor.rowcount
        self.conn.commit()
        
        logger.info(f"清理了 {deleted_count} 条旧的扫描记录")
        return deleted_count
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()


class ScanQueue:
    """扫描任务队列管理器"""
    
    def __init__(self, max_concurrent: int = 3, cache_dir: str = "./cache"):
        """
        初始化扫描队列
        
        Args:
            max_concurrent: 最大并发任务数
            cache_dir: 缓存目录
        """
        self.max_concurrent = max_concurrent
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 任务数据库
        self.db = TaskDatabase()
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.futures: Dict[str, Future] = {}
        
        # 锁
        self.lock = threading.Lock()
        
        # 状态
        self.running = False
        self._worker_id_counter = 0
        
        # 回调
        self._on_progress_callbacks: List[Callable] = []
        
        logger.info(f"扫描队列初始化完成 (最大并发：{max_concurrent})")
    
    def add_task(self, firmware_path: str, firmware_type: str, 
                 filename: Optional[str] = None) -> str:
        """
        添加扫描任务
        
        Args:
            firmware_path: 固件文件路径
            firmware_type: 固件类型 (squashfs/hex/srec/bin)
            filename: 文件名（可选，从路径自动提取）
        
        Returns:
            task_id: 任务 ID
        """
        task_id = str(uuid.uuid4())
        
        if not filename:
            filename = os.path.basename(firmware_path)
        
        # 创建任务对象
        task = ScanTask(
            task_id=task_id,
            firmware_path=str(Path(firmware_path).resolve()),
            firmware_type=firmware_type.lower(),
            filename=filename,
            status=TaskStatus.PENDING,
            progress=0,
            created_at=datetime.now().isoformat()
        )
        
        # 保存到数据库
        self.db.save_task(task)
        
        logger.info(f"✅ 任务已添加：{task_id} ({filename})")
        
        # 如果有运行中的工作进程，立即调度
        if self.running:
            self._schedule_task(task)
        
        return task_id
    
    def add_tasks_batch(self, file_paths: List[str], firmware_type: str) -> List[str]:
        """批量添加任务"""
        task_ids = []
        
        for path in file_paths:
            task_id = self.add_task(path, firmware_type)
            task_ids.append(task_id)
        
        logger.info(f"📦 批量添加 {len(task_ids)} 个任务")
        return task_ids
    
    def _schedule_task(self, task: ScanTask):
        """调度任务到工作线程"""
        with self.lock:
            if len(self.futures) >= self.max_concurrent:
                logger.debug("工作线程已满，任务等待中...")
                return
            
            # 更新任务状态为 running
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()
            self._worker_id_counter += 1
            task.worker_id = self._worker_id_counter
            self.db.save_task(task)
            
            logger.info(f"🔧 开始处理任务 {task.task_id[:8]}... [Worker-{task.worker_id}]")
        
        # 提交到线程池
        future = self.executor.submit(self._execute_scan, task)
        self.futures[task.task_id] = future
    
    def _execute_scan(self, task: ScanTask):
        """执行实际扫描（工作线程）"""
        try:
            def update_progress(stage: str, progress: int, details: str = ""):
                """更新进度回调"""
                with self.lock:
                    current_task = self.db.get_task(task.task_id)
                    if current_task and current_task.status == TaskStatus.RUNNING:
                        current_task.progress = progress
                        current_task.result = current_task.result or {}
                        current_task.result['progress_details'] = {
                            'stage': stage,
                            'details': details,
                            'timestamp': datetime.now().isoformat()
                        }
                        self.db.save_task(current_task)
                        
                        # 触发本地回调
                        for callback in self._on_progress_callbacks:
                            try:
                                callback(task.task_id, progress, stage, details)
                            except Exception as e:
                                logger.error(f"回调失败：{e}")
                        
                        # 发送 WebSocket 通知
                        self._send_notification("scan_progress", {
                            "task_id": task.task_id,
                            "filename": task.filename,
                            "status": "running",
                            "progress": progress,
                            "stage": stage,
                            "details": details,
                            "timestamp": datetime.now().isoformat()
                        })
                
                logger.debug(f"[{task.task_id[:8]}] {stage}: {progress}% - {details}")
            
            # ========== 阶段 1: 解包固件 (进度 0-30%)
            update_progress("extracting", 5, f"正在解压 {task.filename}")
            
            extractor = FirmwareExtractor(str(self.cache_dir / task.task_id))
            extracted_path = extractor.extract_firmware(task.firmware_path)
            
            update_progress("extracting", 20, "固件解包完成")
            
            if not extracted_path.exists():
                raise Exception("解包失败，未生成有效内容")
            
            # ========== 阶段 2: 生成 SBOM (进度 30-60%)
            update_progress("sbom_generation", 35, "正在识别组件")
            
            sbom_gen = SBOMGenerator()
            target_path = str(extracted_path) if extracted_path.is_dir() else str(extracted_path)
            components = sbom_gen.generate_sbom(target_path, task.firmware_type)
            
            update_progress("sbom_generation", 55, f"识别到 {len(components)} 个组件")
            
            # ========== 阶段 3: CVE 匹配 (进度 60-90%)
            update_progress("cve_matching", 65, "正在查询漏洞数据库")
            
            # 配置 Grype DB 路径（从环境变量或默认路径）
            grype_db_path = os.environ.get('GRYPE_DB_PATH', './data/grype.db')
            
            if not os.path.exists(grype_db_path):
                logger.warning(f"Grype DB 不存在：{grype_db_path}, 跳过 CVE 匹配")
                vulnerabilities = []
            else:
                matcher = CVEMatcher(grype_db_path)
                vulnerabilities = matcher.query_vulnerabilities(components)
                
                # 计算优先级
                for vuln in vulnerabilities:
                    vuln.calculate_priority()
                
                logger.info(f"找到 {len(vulnerabilities)} 个 CVE")
            
            update_progress("cve_matching", 80, "CVE 匹配完成")
            
            # ========== 阶段 4: R155 合规检查 (新增 - 进度 80-95%)
            update_progress("r155_compliance", 82, "正在进行 R155 合规评估")
            
            checker = get_r155_checker()
            compliance_result = checker.check_compliance(
                firmware_id=task.task_id,
                firmware_name=task.filename,
                components=components,
                vulnerabilities=vulnerabilities,
                scan_time=datetime.now().isoformat()
            )
            
            # 确保 compliance_result 是 dict 格式 (统一数据格式)
            if hasattr(compliance_result, 'to_dict'):
                compliance_dict = compliance_result.to_dict()
            else:
                compliance_dict = compliance_result
            
            update_progress("r155_compliance", 90, f"合规得分：{compliance_dict.get('overall_score', 0):.1f}/100")
            
            # ========== 阶段 5: 汇总结果 (进度 95-100%)
            update_progress("finalizing", 95, "正在生成报告")
            
            # 准备漏洞数据用于合规检查
            vuln_data_for_compliance = []
            for v in vulnerabilities:
                vuln_data_for_compliance.append({
                    'cve_id': v.cve_id,
                    'component_name': v.component_name,
                    'version': v.component_version,
                    'severity': v.severity,
                    'cvss_score': v.cvss_score,
                    'description': v.description[:500],
                    'published_date': datetime.now().isoformat(),
                    'fixed_version': getattr(v, 'fixed_version', None)
                })
            
            # R155 合规检查 (备用方案)
            try:
                r155_report = check_r155_compliance(vuln_data_for_compliance)
            except Exception as e:
                logger.warning(f"R155 合规检查失败：{e}")
                r155_report = {
                    'compliance_score': 100.0,
                    'violations': [],
                    'category_scores': {},
                    'recommendations': ['无法进行合规检查']
                }
            
            # 计算每个 CVE 的 R155 合规状态
            violating_cves = {v['cve_id'] for v in r155_report.get('violations', [])}
            
            # 构建结果对象 - r155_compliance 字段使用统一的 dict 格式
            result = {
                'firmware_id': task.task_id,
                'filename': task.filename,
                'firmware_type': task.firmware_type,
                'total_cves': len(vulnerabilities),
                'critical_count': sum(1 for v in vulnerabilities if v.severity == 'Critical'),
                'high_count': sum(1 for v in vulnerabilities if v.severity == 'High'),
                'medium_count': sum(1 for v in vulnerabilities if v.severity == 'Medium'),
                'low_count': sum(1 for v in vulnerabilities if v.severity == 'Low'),
                'components': [c.to_dict() for c in components],
                'vulnerabilities': [{
                    'cve_id': v.cve_id,
                    'component': v.component_name,
                    'version': v.component_version,
                    'severity': v.severity,
                    'cvss_score': v.cvss_score,
                    'priority_score': round(v.priority_score or 0, 3),
                    'description': v.description[:200],
                    'r155_non_compliant': v.cve_id in violating_cves
                } for v in sorted(vulnerabilities, key=lambda x: x.priority_score or 0, reverse=True)],
                'r155_compliance': compliance_dict,  # 使用统一的 dict 格式
                'scan_time': datetime.now().isoformat()
            }
            
            # 保存结果并发送通知
            with self.lock:
                completed_task = self.db.get_task(task.task_id)
                if completed_task:
                    completed_task.progress = 100
                    completed_task.status = TaskStatus.COMPLETED
                    completed_task.completed_at = datetime.now().isoformat()
                    completed_task.result = result
                    self.db.save_task(completed_task)
            
            # 发送完成通知
            self._send_notification("scan_completed", {
                "task_id": task.task_id,
                "filename": task.filename,
                "status": "completed",
                "progress": 100,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            update_progress("completed", 100, "扫描完成!")
            
            logger.info(f"✅ 任务完成：{task.task_id[:8]} ({len(vulnerabilities)} CVE)")
            
            # 从 futures 中移除
            with self.lock:
                self.futures.pop(task.task_id, None)
            
            return result
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"❌ 任务失败：{task.task_id} - {error_msg}")
            
            # 发送失败通知
            self._send_notification("scan_failed", {
                "task_id": task.task_id,
                "filename": task.filename,
                "status": "failed",
                "progress": 0,
                "error_message": error_msg,
                "timestamp": datetime.now().isoformat()
            })
            
            with self.lock:
                failed_task = self.db.get_task(task.task_id)
                if failed_task:
                    failed_task.status = TaskStatus.FAILED
                    failed_task.error_message = error_msg
                    failed_task.completed_at = datetime.now().isoformat()
                    self.db.save_task(failed_task)
            
            # 从 futures 中移除
            with self.lock:
                self.futures.pop(task.task_id, None)
            
            return None
    
    def start(self):
        """启动队列处理"""
        if self.running:
            logger.warning("队列已在运行中")
            return
        
        self.running = True
        
        # 加载待处理的任务
        pending_tasks = self.db.get_pending_tasks()
        
        if pending_tasks:
            logger.info(f"发现 {len(pending_tasks)} 个待处理任务，开始调度...")
            for task in pending_tasks:
                task.status = TaskStatus.QUEUED
                self.db.save_task(task)
                self._schedule_task(task)
        else:
            logger.info("队列为空，等待新任务...")
    
    def stop(self, wait: bool = True, timeout: int = 300):
        """停止队列"""
        logger.info("正在停止队列...")
        self.running = False
        
        if wait:
            logger.info("等待当前任务完成...")
            self.executor.shutdown(wait=True, cancel_futures=False)
        else:
            self.executor.shutdown(wait=False, cancel_futures=True)
        
        logger.info("队列已停止")
    
    def get_task_status(self, task_id: str) -> Optional[ScanTask]:
        """获取任务状态"""
        return self.db.get_task(task_id)
    
    def get_all_tasks(self, limit: int = 100, status: Optional[TaskStatus] = None) -> List[ScanTask]:
        """获取所有任务"""
        return self.db.get_all_tasks(limit, status)
    
    def get_queue_stats(self) -> Dict:
        """获取队列统计"""
        all_tasks = self.db.get_all_tasks(limit=1000)
        
        stats = {
            'total': len(all_tasks),
            'pending': sum(1 for t in all_tasks if t.status == TaskStatus.PENDING),
            'queued': sum(1 for t in all_tasks if t.status == TaskStatus.QUEUED),
            'running': sum(1 for t in all_tasks if t.status == TaskStatus.RUNNING),
            'completed': sum(1 for t in all_tasks if t.status == TaskStatus.COMPLETED),
            'failed': sum(1 for t in all_tasks if t.status == TaskStatus.FAILED),
            'active_workers': len(self.futures),
            'max_concurrent': self.max_concurrent
        }
        
        return stats
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.db.get_task(task_id)
        
        if not task:
            return False
        
        if task.status not in [TaskStatus.PENDING, TaskStatus.QUEUED]:
            logger.warning(f"无法取消 {task.status.value} 状态的任务")
            return False
        
        # 标记为取消
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now().isoformat()
        self.db.save_task(task)
        
        # 如果正在运行，尝试取消 future
        if task_id in self.futures:
            self.futures[task_id].cancel()
        
        logger.info(f"🚫 任务已取消：{task_id}")
        return True
    
    def clear_old_tasks(self, days: int = 7) -> int:
        """清理旧任务"""
        return self.db.delete_old_completed_tasks(days)
    
    def register_progress_callback(self, callback: Callable):
        """注册进度回调函数"""
        self._on_progress_callbacks.append(callback)
    
    def set_notification_sender(self, sender_func: Optional[Callable]):
        """设置通知发送函数（用于 WebSocket 推送）
        
        Args:
            sender_func: 函数签名 func(event_type: str, data: dict) -> None
                        例如：sender_func("scan_progress", {"task_id": "...", "progress": 50})
        """
        self._notification_sender = sender_func
        if sender_func:
            logger.info("✅ WebSocket 通知发送器已注册")
    
    def _send_notification(self, event_type: str, data: Dict):
        """发送通知（内部方法）"""
        if hasattr(self, '_notification_sender') and self._notification_sender:
            try:
                self._notification_sender(event_type, data)
            except Exception as e:
                logger.error(f"WebSocket 通知发送失败：{e}")
    
    def wait_for_completion(self, task_id: str, poll_interval: float = 1.0) -> Optional[ScanTask]:
        """等待任务完成"""
        while True:
            task = self.get_task_status(task_id)
            
            if not task:
                return None
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return task
            
            time.sleep(poll_interval)
    
    def close(self):
        """关闭资源"""
        self.stop(wait=True)
        self.db.close()
        logger.info("扫描队列已关闭")


# 全局实例（单例模式）
_scan_queue: Optional[ScanQueue] = None

def get_scan_queue(max_concurrent: int = 3) -> ScanQueue:
    """获取全局扫描队列实例"""
    global _scan_queue
    
    if _scan_queue is None:
        _scan_queue = ScanQueue(max_concurrent=max_concurrent)
        _scan_queue.start()
    
    return _scan_queue


# 便捷函数
def scan_firmware(firmware_path: str, firmware_type: str) -> str:
    """快速扫描单个固件（阻塞式）"""
    queue = get_scan_queue()
    task_id = queue.add_task(firmware_path, firmware_type)
    task = queue.wait_for_completion(task_id)
    return task_id if task else None


if __name__ == "__main__":
    # 测试运行
    import sys
    
    print("=" * 60)
    print("扫描队列测试工具")
    print("=" * 60)
    
    queue = ScanQueue(max_concurrent=2)
    queue.start()
    
    # 演示添加任务
    if len(sys.argv) > 1:
        firmware_path = sys.argv[1]
        firmware_type = sys.argv[2] if len(sys.argv) > 2 else "bin"
        
        print(f"\n正在扫描：{firmware_path} ({firmware_type})")
        task_id = queue.add_task(firmware_path, firmware_type)
        
        print(f"任务 ID: {task_id}")
        print("\n等待完成...")
        
        task = queue.wait_for_completion(task_id)
        
        if task:
            print(f"\n最终状态：{task.status.value}")
            print(f"进度：{task.progress}%")
            
            if task.result:
                print(f"\n扫描结果:")
                print(f"  组件数：{len(task.result.get('components', []))}")
                print(f"  CVE 数：{task.result.get('total_cves', 0)}")
            elif task.error_message:
                print(f"\n错误信息:\n{task.error_message[:500]}")
    else:
        print("\n用法：python task_queue.py <firmware_path> [firmware_type]")
        print("示例：python task_queue.py ./test.bin bin")
    
    queue.close()
    print("\n测试完成")
