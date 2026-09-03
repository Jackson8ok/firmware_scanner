#!/usr/bin/env python3
"""
Phase 4 API 集成测试脚本 (v2.7.2)

测试内容:
1. 导入 SBOM
2. 扫描固件时指定 sbom_id
3. 验证融合结果返回

使用方法:
    python test_phase4_api.py
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from services.sbom.sbom_api import sbom_db
from scanner.task_queue import ScanQueue
from services.sbom.sbom_fusion import SBOMFusionEngine

def test_phase4_integration():
    """测试 Phase 4 融合分析流程"""
    
    print("=" * 60)
    print("Phase 4 API 集成测试 (v2.7.2)")
    print("=" * 60)
    
    # ========== 步骤 1: 导入 SBOM ==========
    print("\n[1/4] 导入 SBOM...")
    
    test_sbom = {
        "sbom_id": "test_sbom_001",
        "file_path": "/tmp/test_sbom.json",
        "task_id": "test_task_001",
        "components": [
            {
                "name": "openssl",
                "version": "1.1.1k",
                "purl": "pkg:npm/openssl@1.1.1k",
                "cpe": "cpe:2.3:a:openssl:openssl:1.1.1k:*:*:*:*:*:*:*",
                "source": "sbom"
            },
            {
                "name": "busybox",
                "version": "1.33.1",
                "purl": "pkg:deb/debian/busybox@1.33.1",
                "cpe": "cpe:2.3:a:busybox:busybox:1.33.1:*:*:*:*:*:*:*",
                "source": "sbom"
            }
        ],
        "components_count": 2,
        "format": "spdx",
        "created_at": "2026-09-03T10:00:00",
        "status": "imported"
    }
    
    sbom_db.save(test_sbom)
    print(f"✅ SBOM 已保存：{test_sbom['sbom_id']}")
    
    # 验证保存
    retrieved = sbom_db.get("test_sbom_001")
    assert retrieved is not None, "SBOM 保存失败"
    # components 可能是字符串或列表（取决于 SQLite 版本）
    components = retrieved['components']
    if isinstance(components, str):
        import json
        components = json.loads(components)
    assert len(components) == 2, "组件数不匹配"
    print(f"✅ SBOM 验证通过：{len(components)} 个组件")
    
    # ========== 步骤 2: 测试融合引擎 ==========
    print("\n[2/4] 测试融合引擎...")
    
    # 模拟指纹组件（从固件扫描得到）
    fingerprint_components = [
        {
            "name": "openssl",
            "version": "1.1.1k",
            "purl": "",
            "cpe": "cpe:2.3:a:openssl:openssl:1.1.1k:*:*:*:*:*:*:*",
            "source": "firmware"
        },
        {
            "name": "zlib",
            "version": "1.2.11",
            "purl": "",
            "cpe": "cpe:2.3:a:zlib:zlib:1.2.11:*:*:*:*:*:*:*",
            "source": "firmware"
        }
    ]
    
    # 创建融合引擎
    fusion_engine = SBOMFusionEngine()
    
    # 执行融合
    fused = fusion_engine.fuse(test_sbom['components'], fingerprint_components)
    
    print(f"✅ 融合分析完成:")
    print(f"   - SBOM 组件数：{len(test_sbom['components'])}")
    print(f"   - 指纹组件数：{len(fingerprint_components)}")
    print(f"   - 融合后组件数：{len(fused)}")
    
    # 验证融合结果
    summary = fusion_engine.get_fusion_summary()
    print(f"✅ 融合摘要:")
    print(f"   - 总组件数：{summary['total_components']}")
    print(f"   - Level A (双源): {summary['evidence_levels']['A']}")
    print(f"   - Level B (SBOM only): {summary['evidence_levels']['B']}")
    print(f"   - Level C (指纹 only): {summary['evidence_levels']['C']}")
    
    assert summary['evidence_levels']['A'] == 1, "Level A 数量应为 1 (openssl)"
    assert summary['evidence_levels']['B'] == 1, "Level B 数量应为 1 (busybox)"
    assert summary['evidence_levels']['C'] == 1, "Level C 数量应为 1 (zlib)"
    print("✅ 融合摘要验证通过")
    
    # ========== 步骤 3: 测试任务队列集成 ==========
    print("\n[3/4] 测试任务队列集成...")
    
    queue = ScanQueue(max_concurrent=1)
    queue.start()
    
    # 添加任务时指定 sbom_id
    task_id = queue.add_task(
        firmware_path="/tmp/test_firmware.bin",
        firmware_type="bin",
        filename="test_firmware.bin",
        sbom_id="test_sbom_001"
    )
    
    print(f"✅ 任务已添加：{task_id}")
    print(f"   - sbom_id: test_sbom_001")
    
    # 验证任务元数据
    task = queue.db.get_task(task_id)
    assert task is not None, "任务不存在"
    assert task.result is not None, "任务元数据为空"
    assert task.result.get('sbom_id') == 'test_sbom_001', "sbom_id 未保存"
    print(f"✅ 任务元数据验证通过：sbom_id={task.result.get('sbom_id')}")
    
    queue.close()
    print("✅ 队列已关闭")
    
    # ========== 步骤 4: 测试加权 CVE 计算 ==========
    print("\n[4/4] 测试加权 CVE 计算...")
    
    # 模拟融合组件
    fused_components = [
        {"name": "openssl", "version": "1.1.1k", "evidence_level": "A"},
        {"name": "busybox", "version": "1.33.1", "evidence_level": "B"},
        {"name": "zlib", "version": "1.2.11", "evidence_level": "C"}
    ]
    
    # 模拟漏洞
    class MockVuln:
        def __init__(self, component, version, severity):
            self.component_name = component
            self.component_version = version
            self.severity = severity
    
    vulnerabilities = [
        MockVuln("openssl", "1.1.1k", "Critical"),
        MockVuln("busybox", "1.33.1", "High"),
        MockVuln("zlib", "1.2.11", "Medium")
    ]
    
    # 计算加权
    weighted = queue._calculate_weighted_cve(fused_components, vulnerabilities)
    
    print(f"✅ 加权 CVE 统计:")
    print(f"   - Critical (加权): {weighted['critical_weighted']:.2f}")
    print(f"   - High (加权): {weighted['high_weighted']:.2f}")
    print(f"   - Medium (加权): {weighted['medium_weighted']:.2f}")
    print(f"   - Total (加权): {weighted['total_weighted']:.2f}")
    
    # 验证权重计算
    # openssl (A) = 1.25, busybox (B) = 1.0, zlib (C) = 0.75
    assert abs(weighted['critical_weighted'] - 1.25) < 0.01, "Critical 加权错误"
    assert abs(weighted['high_weighted'] - 1.0) < 0.01, "High 加权错误"
    assert abs(weighted['medium_weighted'] - 0.75) < 0.01, "Medium 加权错误"
    print("✅ 加权计算验证通过")
    
    # ========== 清理 ==========
    print("\n清理测试数据...")
    sbom_db.delete("test_sbom_001")
    print("✅ 测试完成")
    
    print("\n" + "=" * 60)
    print("✅ Phase 4 API 集成测试全部通过！")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = test_phase4_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
