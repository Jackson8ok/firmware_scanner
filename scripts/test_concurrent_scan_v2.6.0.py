#!/usr/bin/env python3
"""
v2.6.0 并发扫描性能测试

对比：
- 串行扫描（v2.5.5）
- 并发扫描（v2.6.0, max_concurrency=5）

目标：扫描速度提升 50%
"""

import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.grype_matcher import GrypeCLIMatcher
from scanner.concurrent_grype_matcher import ConcurrentGrypeMatcher


def test_serial_scan(target_path: str, components: list):
    """测试串行扫描"""
    print(f"\n{'='*60}")
    print("📊 串行扫描测试（v2.5.5）")
    print(f"{'='*60}")
    
    matcher = GrypeCLIMatcher(
        grype_bin="/mnt/workspace/firmware_scanner/tools/grype/grype",
        timeout=600
    )
    
    start_time = time.time()
    
    # 串行扫描：逐个组件调用
    all_vulns = []
    for comp in components:
        print(f"  🔍 扫描 {comp['name']} {comp['version']}...")
        vulns = matcher.scan(target_path)
        all_vulns.extend(vulns)
        print(f"    ✅ 发现 {len(vulns)} CVEs")
    
    duration = time.time() - start_time
    
    # 去重
    seen = set()
    unique_vulns = []
    for vuln in all_vulns:
        key = (vuln.cve_id, vuln.component_name, vuln.component_version)
        if key not in seen:
            seen.add(key)
            unique_vulns.append(vuln)
    
    print(f"\n✅ 串行扫描完成")
    print(f"   - 总耗时：{duration:.2f}s")
    print(f"   - CVE 总数：{len(unique_vulns)}")
    print(f"   - 平均速度：{len(components)/duration:.2f} 组件/秒")
    
    return duration, len(unique_vulns)


def test_concurrent_scan(target_path: str, components: list, max_concurrency: int = 5):
    """测试并发扫描"""
    print(f"\n{'='*60}")
    print("🚀 并发扫描测试（v2.6.0）")
    print(f"{'='*60}")
    
    matcher = ConcurrentGrypeMatcher(
        grype_bin="/mnt/workspace/firmware_scanner/tools/grype/grype",
        timeout=600,
        max_concurrency=max_concurrency,
        enable_cache=True
    )
    
    start_time = time.time()
    
    # 并发扫描
    vulns = matcher.scan(target_path, components)
    
    duration = time.time() - start_time
    
    print(f"\n✅ 并发扫描完成")
    print(f"   - 总耗时：{duration:.2f}s")
    print(f"   - CVE 总数：{len(vulns)}")
    print(f"   - 平均速度：{len(components)/duration:.2f} 组件/秒")
    print(f"   - 并发度：{max_concurrency}")
    
    # 缓存统计
    stats = matcher.get_cache_stats()
    print(f"   - 缓存大小：{stats['size']}")
    
    return duration, len(vulns)


def main():
    """主测试函数"""
    # 测试样本：使用 OpenWrt 固件
    target_path = "/mnt/workspace/firmware_scanner/demo_firmwares/owrt_15.05.1.squashfs.extracted"
    
    if not Path(target_path).exists():
        print(f"❌ 测试固件不存在：{target_path}")
        print("请先解压固件：unsquashfs -d {target_path} firmware.bin")
        sys.exit(1)
    
    # 模拟组件列表（从 SBOM 提取）
    components = [
        {"name": "busybox", "version": "1.35.0", "purl": "pkg:apk/busybox@1.35.0"},
        {"name": "openssl", "version": "1.1.1", "purl": "pkg:apk/openssl@1.1.1"},
        {"name": "libcrypto", "version": "1.1.1", "purl": "pkg:apk/libcrypto@1.1.1"},
        {"name": "dropbear", "version": "2022.82", "purl": "pkg:apk/dropbear@2022.82"},
        {"name": "procd", "version": "2021-01-04", "purl": "pkg:apk/procd@2021-01-04"},
        {"name": "ubus", "version": "2021-04-11", "purl": "pkg:apk/ubus@2021-04-11"},
        {"name": "libc", "version": "2.30", "purl": "pkg:apk/libc@2.30"},
        {"name": "libgcc", "version": "9.3.0", "purl": "pkg:apk/libgcc@9.3.0"},
        {"name": "kernel", "version": "5.4.143", "purl": "pkg:generic/kernel@5.4.143"},
    ]
    
    print(f"\n{'='*60}")
    print("🧪 v2.6.0 并发扫描性能测试")
    print(f"{'='*60}")
    print(f"目标路径：{target_path}")
    print(f"组件数量：{len(components)}")
    print(f"并发度：5")
    
    # 测试串行扫描
    serial_duration, serial_vulns = test_serial_scan(target_path, components)
    
    # 测试并发扫描
    concurrent_duration, concurrent_vulns = test_concurrent_scan(target_path, components, max_concurrency=5)
    
    # 性能对比
    print(f"\n{'='*60}")
    print("📈 性能对比")
    print(f"{'='*60}")
    print(f"串行扫描：{serial_duration:.2f}s ({serial_vulns} CVEs)")
    print(f"并发扫描：{concurrent_duration:.2f}s ({concurrent_vulns} CVEs)")
    
    speedup = serial_duration / concurrent_duration if concurrent_duration > 0 else 0
    improvement = (1 - concurrent_duration / serial_duration) * 100 if serial_duration > 0 else 0
    
    print(f"\n🚀 性能提升:")
    print(f"   - 加速比：{speedup:.2f}x")
    print(f"   - 提升：{improvement:.1f}%")
    
    if improvement >= 50:
        print(f"\n✅ 目标达成！(≥50%)")
    else:
        print(f"\n⚠️ 未达目标 (目标≥50%, 实际{improvement:.1f}%)")
    
    # CVE 数量对比
    vuln_diff = abs(serial_vulns - concurrent_vulns)
    if vuln_diff <= 5:
        print(f"\n✅ CVE 数量一致 (差异={vuln_diff})")
    else:
        print(f"\n⚠️ CVE 数量差异较大 (差异={vuln_diff})")
    
    print(f"\n{'='*60}")
    print("✅ 测试完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
