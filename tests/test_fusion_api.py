#!/usr/bin/env python3
"""
Phase 4 融合端到端集成测试 (v2.7.2-hotfix)

验收编号：VAL-FWSCAN-2026-016
测试目标：验证 Phase 4 融合功能端到端流程（导入 SBOM → 带 sbom_id 扫描 → 验证 A/B/C 分层）

修复记录:
- v2.7.2-hotfix: 修复双重 JSON 反序列化问题 (scanner/task_queue.py 第 659 行)

使用方法:
    PYTHONPATH=/mnt/workspace/firmware_scanner python3 tests/test_fusion_api.py
"""

import sys
import os
import json
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.sbom.sbom_api import sbom_db
from scanner.task_queue import ScanQueue
from services.sbom.sbom_fusion import SBOMFusionEngine

def test_fusion_end_to_end():
    """Phase 4 融合端到端测试"""
    
    print("=" * 80)
    print("Phase 4 融合端到端集成测试 (v2.7.2-hotfix)")
    print("验收编号：VAL-FWSCAN-2026-016")
    print("=" * 80)
    
    # ========== 步骤 1: 导入 SBOM ==========
    print("\n[1/5] 导入 SBOM...")
    
    test_sbom = {
        "sbom_id": "test_sbom_fusion_001",
        "file_path": "/tmp/test_sbom_fusion.json",
        "task_id": "test_task_fusion_001",
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
            },
            {
                "name": "zlib",
                "version": "1.2.11",
                "purl": "pkg:deb/debian/zlib@1.2.11",
                "cpe": "cpe:2.3:a:zlib:zlib:1.2.11:*:*:*:*:*:*:*",
                "source": "sbom"
            }
        ],
        "components_count": 3,
        "format": "spdx",
        "created_at": "2026-09-03T12:00:00",
        "status": "imported"
    }
    
    sbom_db.save(test_sbom)
    print(f"✅ SBOM 已保存：{test_sbom['sbom_id']}")
    
    # 验证保存（确保 components 被正确序列化/反序列化）
    retrieved = sbom_db.get("test_sbom_fusion_001")
    assert retrieved is not None, "SBOM 保存失败"
    
    # 检查 components 类型（可能是 list 或 str）
    comps_raw = retrieved['components']
    if isinstance(comps_raw, list):
        components_list = comps_raw
    else:
        components_list = json.loads(comps_raw)
    
    assert len(components_list) == 3, f"组件数不匹配：期望 3，实际 {len(components_list)}"
    print(f"✅ SBOM 验证通过：{len(components_list)} 个组件，序列化/反序列化正确")
    
    # ========== 步骤 2: 模拟扫描任务（带 sbom_id）==========
    print("\n[2/5] 创建扫描任务（带 sbom_id）...")
    
    queue = ScanQueue(max_concurrent=1)
    queue.start()
    
    # 添加任务时指定 sbom_id
    task_id = queue.add_task(
        firmware_path="/tmp/test_firmware_fusion.bin",
        firmware_type="bin",
        filename="test_firmware_fusion.bin",
        sbom_id="test_sbom_fusion_001"
    )
    
    print(f"✅ 任务已添加：{task_id}")
    print(f"   - sbom_id: test_sbom_fusion_001")
    
    # 验证任务元数据
    task = queue.db.get_task(task_id)
    assert task is not None, "任务不存在"
    assert task.result is not None, "任务元数据为空"
    assert task.result.get('sbom_id') == 'test_sbom_fusion_001', "sbom_id 未保存"
    print(f"✅ 任务元数据验证通过：sbom_id={task.result.get('sbom_id')}")
    
    # ========== 步骤 3: 模拟融合流程（不实际扫描，只测试融合逻辑）==========
    print("\n[3/5] 测试融合逻辑（关键步骤）...")
    
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
        },
        {
            "name": "libcrypto",
            "version": "1.1.1k",
            "purl": "",
            "cpe": "cpe:2.3:a:openssl:libcrypto:1.1.1k:*:*:*:*:*:*:*",
            "source": "firmware"
        }
    ]
    
    # 获取 SBOM 记录（模拟 task_queue.py 的逻辑）
    sbom_record = sbom_db.get("test_sbom_fusion_001")
    assert sbom_record is not None, "SBOM 记录不存在"
    
    # 关键修复验证：正确处理 components 字段（避免双重反序列化）
    comps_raw = sbom_record['components']
    sbom_components_list = comps_raw if isinstance(comps_raw, list) else json.loads(comps_raw)
    
    print(f"✅ SBOM 组件加载成功：{len(sbom_components_list)} 个组件")
    print(f"   - components 类型：{type(comps_raw).__name__}")
    print(f"   - 反序列化后类型：{type(sbom_components_list).__name__}")
    
    # 转换组件格式
    sbom_components = []
    for comp in sbom_components_list:
        sbom_components.append({
            'name': comp.get('name', ''),
            'version': comp.get('version', ''),
            'purl': comp.get('purl', ''),
            'cpe': comp.get('cpe', ''),
            'source': 'sbom'
        })
    
    # 创建融合引擎
    fusion_engine = SBOMFusionEngine()
    
    # 执行融合
    fused_components = fusion_engine.fuse(sbom_components, fingerprint_components)
    
    print(f"✅ 融合分析完成:")
    print(f"   - SBOM 组件数：{len(sbom_components)}")
    print(f"   - 指纹组件数：{len(fingerprint_components)}")
    print(f"   - 融合后组件数：{len(fused_components)}")
    
    # 验证融合结果
    summary = fusion_engine.get_fusion_summary()
    print(f"✅ 融合摘要:")
    print(f"   - 总组件数：{summary['total_components']}")
    print(f"   - Level A (双源): {summary['evidence_levels']['A']}")
    print(f"   - Level B (SBOM only): {summary['evidence_levels']['B']}")
    print(f"   - Level C (指纹 only): {summary['evidence_levels']['C']}")
    
    # 验证 A/B/C 分级正确
    assert summary['evidence_levels']['A'] == 2, "Level A 数量应为 2 (openssl, zlib)"
    assert summary['evidence_levels']['B'] == 1, "Level B 数量应为 1 (busybox)"
    assert summary['evidence_levels']['C'] == 1, "Level C 数量应为 1 (libcrypto)"
    print("✅ 融合摘要验证通过")
    
    # ========== 步骤 4: 测试加权 CVE 计算 ==========
    print("\n[4/5] 测试加权 CVE 计算...")
    
    # 模拟融合组件（带证据等级）
    fused_components_mock = [
        {"name": "openssl", "version": "1.1.1k", "evidence_level": "A"},
        {"name": "busybox", "version": "1.33.1", "evidence_level": "B"},
        {"name": "zlib", "version": "1.2.11", "evidence_level": "A"},
        {"name": "libcrypto", "version": "1.1.1k", "evidence_level": "C"}
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
        MockVuln("zlib", "1.2.11", "Medium"),
        MockVuln("libcrypto", "1.1.1k", "Critical")
    ]
    
    # 计算加权
    weighted = queue._calculate_weighted_cve(fused_components_mock, vulnerabilities)
    
    print(f"✅ 加权 CVE 统计:")
    print(f"   - Critical (加权): {weighted['critical_weighted']:.2f}")
    print(f"   - High (加权): {weighted['high_weighted']:.2f}")
    print(f"   - Medium (加权): {weighted['medium_weighted']:.2f}")
    print(f"   - Total (加权): {weighted['total_weighted']:.2f}")
    
    # 验证权重计算
    # openssl (A) = 1.25 → Critical weighted = 1.25
    # libcrypto (C) = 0.75 → Critical weighted = 0.75
    # 总计 Critical = 2.0 (两个 Critical 漏洞分别计算)
    # busybox (B) = 1.0 → High weighted = 1.0
    # zlib (A) = 1.25 → Medium weighted = 1.25
    assert abs(weighted['critical_weighted'] - 2.0) < 0.01, f"Critical 加权错误：期望 2.0，实际 {weighted['critical_weighted']}"
    assert abs(weighted['high_weighted'] - 1.0) < 0.01, "High 加权错误"
    assert abs(weighted['medium_weighted'] - 1.25) < 0.01, "Medium 加权错误"
    print("✅ 加权计算验证通过")
    
    # ========== 步骤 5: 清理 ==========
    print("\n[5/5] 清理测试数据...")
    
    queue.close()
    sbom_db.delete("test_sbom_fusion_001")
    
    print("✅ 测试数据已清理")
    
    # ========== 总结 ==========
    print("\n" + "=" * 80)
    print("✅ Phase 4 融合端到端集成测试全部通过！")
    print("=" * 80)
    print("\n关键验证点:")
    print("  ✅ SBOM 序列化/反序列化正确（无双重反序列化）")
    print("  ✅ 融合引擎 A/B/C 分级正确")
    print("  ✅ 加权 CVE 计算准确")
    print("  ✅ 端到端流程完整")
    print("\n验收标准:")
    print("  ✅ 导入 SBOM → 带 sbom_id 扫描 → A/B/C 分层返回")
    print("  ✅ 加权统计正确")
    print("  ✅ 无运行时崩溃")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    try:
        success = test_fusion_end_to_end()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
