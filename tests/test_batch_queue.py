#!/usr/bin/env python3
"""
批量扫描队列测试脚本 - v2.6.0

测试批量上传、并发扫描、进度跟踪等功能
"""

import sys
import os
import time
import threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner.batch_queue import BatchScanQueue


def create_test_firmwares(count: int = 5):
    """创建测试固件文件"""
    upload_dir = "/mnt/workspace/firmware_scanner/uploads/test"
    os.makedirs(upload_dir, exist_ok=True)
    
    firmware_paths = []
    for i in range(count):
        # 创建空文件模拟固件
        file_path = f"{upload_dir}/test_firmware_{i}.bin"
        with open(file_path, 'wb') as f:
            f.write(b'\x00' * 1024)  # 1KB 空文件
        firmware_paths.append({
            "path": file_path,
            "type": "auto"
        })
    
    print(f"✅ 创建 {count} 个测试固件文件")
    return firmware_paths


def test_batch_queue():
    """测试批量扫描队列"""
    print("=" * 80)
    print("🐢 玄武·AFVS v2.6.0 批量扫描队列测试")
    print("=" * 80)
    
    # 创建队列
    queue = BatchScanQueue(max_concurrent=2)
    
    # 设置 WebSocket 回调（模拟）
    def ws_callback(event_type: str, data: dict):
        print(f"📡 WebSocket 事件：{event_type} - {data}")
    
    queue.set_ws_callback(ws_callback)
    
    # 创建测试固件
    firmware_list = create_test_firmwares(5)
    
    print(f"\n📦 准备批量上传 {len(firmware_list)} 个固件")
    
    # 批量添加任务
    batch_id = queue.add_batch(firmware_list)
    print(f"✅ 批量任务已创建：{batch_id}")
    
    # 启动队列
    print("\n🚀 启动批量扫描...")
    queue.start()
    
    # 监控进度
    print("\n📊 实时监控进度:")
    print("-" * 80)
    
    try:
        while True:
            status = queue.get_batch_status(batch_id)
            if not status:
                break
            
            progress_bar = "█" * int(status["progress"] / 5) + "░" * (20 - int(status["progress"] / 5))
            print(f"\r  进度：[{progress_bar}] {status['progress']}% "
                  f"(完成:{status['completed']}/{status['total']} "
                  f"运行:{status['running']} "
                  f"等待:{status['pending']})", end="")
            
            if status["status"] == "completed":
                print("\n\n✅ 批量扫描完成！")
                break
            elif status["status"] == "failed":
                print("\n\n❌ 批量扫描失败！")
                break
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断")
    
    # 获取最终状态
    print("\n" + "=" * 80)
    print("📋 最终状态:")
    print("-" * 80)
    
    final_status = queue.get_batch_status(batch_id)
    if final_status:
        print(f"  批量 ID:    {final_status['batch_id']}")
        print(f"  状态：      {final_status['status']}")
        print(f"  总进度：    {final_status['progress']}%")
        print(f"  总固件数：  {final_status['total']}")
        print(f"  完成：      {final_status['completed']}")
        print(f"  失败：      {final_status['failed']}")
        print(f"  创建时间：  {final_status['created_at']}")
        print(f"  完成时间：  {final_status['completed_at']}")
    
    # 获取聚合结果
    print("\n" + "=" * 80)
    print("📊 聚合结果:")
    print("-" * 80)
    
    result = queue.get_batch_results(batch_id)
    if result:
        print(f"  总漏洞数：    {result.get('total_vulns', 0)}")
        print(f"  总组件数：    {result.get('total_components', 0)}")
        print(f"  风险评分：    {result.get('risk_score', 0)}/100")
        print(f"  严重性统计：")
        severity_stats = result.get('severity_stats', {})
        for severity, count in severity_stats.items():
            print(f"    {severity}: {count}")
    
    # 列出所有批量任务
    print("\n" + "=" * 80)
    print("📋 批量任务列表:")
    print("-" * 80)
    
    batches = queue.list_batches()
    for batch in batches:
        print(f"  - {batch['batch_id']}: {batch['status']} ({batch['progress']}%)")
    
    # 停止队列
    print("\n" + "=" * 80)
    print("⏹️  停止队列...")
    queue.stop()
    print("✅ 队列已停止")
    
    # 总结
    print("\n" + "=" * 80)
    print("✅ 批量扫描队列测试完成！")
    print("=" * 80)
    print()


if __name__ == "__main__":
    test_batch_queue()
