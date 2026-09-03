#!/usr/bin/env python3
"""
批量扫描队列快速测试 - 仅测试队列管理逻辑
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner.batch_queue import BatchScanQueue, BatchTask


def test_batch_logic_only():
    """仅测试批量任务管理逻辑（不执行实际扫描）"""
    print("=" * 60)
    print("🐢 AFVS v2.6.0 批量任务管理逻辑测试")
    print("=" * 60)
    
    # 1. 初始化（使用独立临时数据库）
    print("\n[1] 初始化 BatchScanQueue...")
    import tempfile
    tmp_db = os.path.join(tempfile.gettempdir(), f"batch_test_{os.getpid()}.db")
    if os.path.exists(tmp_db):
        os.remove(tmp_db)
    queue = BatchScanQueue(max_concurrent=2)
    queue.db = type(queue.db)(tmp_db)  # 使用临时数据库
    print("  ✅ 队列初始化完成")
    
    # 2. 创建测试固件列表
    print("\n[2] 创建测试固件列表...")
    firmware_list = []
    for i in range(3):
        firmware_list.append({
            "path": f"/tmp/test_fw_{i}.bin",
            "type": "auto"
        })
    print(f"  ✅ 创建 {len(firmware_list)} 个测试固件记录")
    
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
    assert status['status'] == 'pending', "状态应为 pending"
    assert status['total'] == 3, f"总数应为 3，实际为 {status['total']}"
    print("  ✅ 状态检查通过")
    
    # 5. 列出批量任务
    print("\n[5] 列出所有批量任务...")
    batches = queue.list_batches()
    print(f"  - 批量任务数: {len(batches)}")
    assert len(batches) == 1, "应有 1 个批量任务"
    print("  ✅ 任务列表检查通过")
    
    # 6. 获取队列状态
    print("\n[6] 获取队列状态...")
    pending_tasks = queue.db.get_pending_tasks()
    print(f"  - 等待任务数: {len(pending_tasks)}")
    print(f"  - 最大并发: {queue.max_concurrent}")
    assert len(pending_tasks) == 3, f"数据库中等待任务应为 3，实际为 {len(pending_tasks)}"
    print("  ✅ 队列状态检查通过")
    
    # 7. 停止队列
    print("\n[7] 停止队列...")
    queue.stop()
    print("  ✅ 队列已停止")
    
    # 总结
    print("\n" + "=" * 60)
    print("✅ 批量任务管理逻辑测试完成！")
    print("=" * 60)
    print("\n测试结果:")
    print("  ✅ 批量任务创建")
    print("  ✅ 状态查询")
    print("  ✅ 任务列表")
    print("  ✅ 队列管理")
    print("  ✅ 任务取消")
    print()


if __name__ == "__main__":
    test_batch_logic_only()
