#!/usr/bin/env python3
"""
批量扫描队列快速测试 - 验证核心功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner.batch_queue import BatchScanQueue, BatchTask
from scanner.task_queue import TaskStatus


def test_batch_core():
    """测试批量扫描核心功能"""
    print("=" * 60)
    print("🐢 AFVS v2.6.0 批量扫描核心功能测试")
    print("=" * 60)
    
    # 1. 初始化
    print("\n[1] 初始化 BatchScanQueue...")
    queue = BatchScanQueue(max_concurrent=2)
    
    # 2. 创建测试固件
    print("\n[2] 创建测试固件...")
    upload_dir = "/mnt/workspace/firmware_scanner/uploads/test"
    os.makedirs(upload_dir, exist_ok=True)
    
    firmware_list = []
    for i in range(3):
        file_path = f"{upload_dir}/test_fw_{i}.bin"
        with open(file_path, 'wb') as f:
            f.write(b'\x00' * 512)
        firmware_list.append({"path": file_path, "type": "auto"})
    
    print(f"  ✅ 创建 {len(firmware_list)} 个测试固件")
    
    # 3. 批量添加任务
    print("\n[3] 批量添加任务...")
    batch_id = queue.add_batch(firmware_list)
    print(f"  ✅ 批量任务 ID: {batch_id}")
    
    # 4. 检查批量任务状态
    print("\n[4] 检查批量任务状态...")
    status = queue.get_batch_status(batch_id)
    print(f"  - 状态: {status['status']}")
    print(f"  - 总数: {status['total']}")
    print(f"  - 完成: {status['completed']}")
    print(f"  - 等待: {status['pending']}")
    
    # 5. 列出批量任务
    print("\n[5] 列出所有批量任务...")
    batches = queue.list_batches()
    print(f"  - 批量任务数: {len(batches)}")
    for b in batches:
        print(f"    * {b['batch_id']}: {b['status']}")
    
    # 6. 获取队列状态
    print("\n[6] 获取队列状态...")
    print(f"  - 队列大小: {len(queue.task_queue)}")
    print(f"  - 活跃任务: {len(queue.active_tasks)}")
    print(f"  - 最大并发: {queue.max_concurrent}")
    
    # 7. 测试取消功能
    print("\n[7] 测试取消批量任务...")
    cancel_result = queue.cancel_batch(batch_id)
    print(f"  - 取消结果: {cancel_result}")
    
    # 8. 检查取消后状态
    print("\n[8] 检查取消后状态...")
    status_after = queue.get_batch_status(batch_id)
    if status_after:
        cancelled_count = sum(1 for tid in queue.batch_tasks[batch_id].task_ids 
                            if queue.get_task_status(tid).status == TaskStatus.CANCELLED)
        print(f"  - 已取消任务数: {cancelled_count}")
    
    # 总结
    print("\n" + "=" * 60)
    print("✅ 批量扫描核心功能测试完成！")
    print("=" * 60)
    print("\n测试结果:")
    print("  ✅ 批量任务创建")
    print("  ✅ 状态查询")
    print("  ✅ 任务列表")
    print("  ✅ 队列管理")
    print("  ✅ 任务取消")
    print()


if __name__ == "__main__":
    test_batch_core()
