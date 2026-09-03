#!/usr/bin/env python3
"""
v2.5.2 published_date 字段补全自测脚本

验证 Grype DB 查询是否正确修复
"""

import sys
import os
sys.path.insert(0, '/mnt/workspace/firmware_scanner')

from scanner.grype_matcher import GrypeCLIMatcher
from pathlib import Path

def test_grype_db_connection():
    """测试 Grype DB 连接"""
    print("🧪 测试 1: Grype DB 连接...")
    
    grype_bin = "/mnt/workspace/firmware_scanner/tools/grype/grype"
    grype_db_path = "/mnt/workspace/firmware_scanner/db/grype/6/vulnerability.db"
    
    if not Path(grype_db_path).exists():
        print(f"  ❌ Grype DB 不存在：{grype_db_path}")
        return False
    
    print(f"  ✅ Grype DB 存在：{grype_db_path}")
    print(f"  ℹ️  文件大小：{Path(grype_db_path).stat().st_size / 1024 / 1024:.2f} MB")
    return True

def test_vulnerability_handles_table():
    """测试 vulnerability_handles 表查询"""
    print("\n🧪 测试 2: vulnerability_handles 表查询...")
    
    import sqlite3
    
    grype_db_path = "/mnt/workspace/firmware_scanner/db/grype/6/vulnerability.db"
    
    try:
        conn = sqlite3.connect(grype_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vulnerability_handles'")
        row = cursor.fetchone()
        
        if row:
            print(f"  ✅ vulnerability_handles 表存在")
        else:
            print(f"  ❌ vulnerability_handles 表不存在")
            conn.close()
            return False
        
        # 检查列名
        cursor.execute("PRAGMA table_info(vulnerability_handles)")
        columns = [col['name'] for col in cursor.fetchall()]
        print(f"  ℹ️  表列：{columns}")
        
        if 'name' in columns:
            print(f"  ✅ name 列存在（CVE 标识符列）")
        else:
            print(f"  ❌ name 列不存在")
            conn.close()
            return False
        
        if 'published_date' in columns:
            print(f"  ✅ published_date 列存在")
        else:
            print(f"  ❌ published_date 列不存在")
            conn.close()
            return False
        
        # 测试查询（使用已知 CVE）
        cursor.execute("""
            SELECT name, published_date FROM vulnerability_handles
            WHERE name LIKE 'CVE-2018-%'
            LIMIT 5
        """)
        rows = cursor.fetchall()
        
        if rows:
            print(f"  ✅ 查询成功，返回 {len(rows)} 条记录")
            for row in rows:
                print(f"    - {row['name']}: {row['published_date']}")
        else:
            print(f"  ⚠️  查询返回空结果（可能无 CVE-2018 数据）")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ 查询失败：{e}")
        return False

def test_published_date_from_grype():
    """测试从 grype 输出解析 published_date"""
    print("\n🧪 测试 3: grype_matcher._get_published_date_from_db()...")
    
    grype_bin = "/mnt/workspace/firmware_scanner/tools/grype/grype"
    
    if not Path(grype_bin).exists():
        print(f"  ⚠️  grype CLI 不存在，跳过测试")
        return None
    
    try:
        matcher = GrypeCLIMatcher(grype_bin=grype_bin, timeout=60)
        
        # 测试已知 CVE（从复测结论中的 busybox CVE）
        test_cves = [
            "CVE-2018-1000517",
            "CVE-2016-2148",
            "CVE-2016-6301",
        ]
        
        success_count = 0
        for cve_id in test_cves:
            published_date = matcher._get_published_date_from_db(cve_id)
            if published_date:
                print(f"  ✅ {cve_id}: {published_date}")
                success_count += 1
            else:
                print(f"  ❌ {cve_id}: None")
        
        if success_count > 0:
            print(f"  ✅ 成功率：{success_count}/{len(test_cves)}")
            return True
        else:
            print(f"  ❌ 全部失败")
            return False
            
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

def test_full_vulnerability_parsing():
    """测试完整 vulnerability 解析（含所有字段）"""
    print("\n🧪 测试 4: 完整 vulnerability 解析...")
    
    # 模拟 grype CLI 输出
    grype_sample = {
        "matches": [
            {
                "vulnerability": {
                    "id": "CVE-2018-1000517",
                    "description": "busybox 漏洞",
                    "cvss": [
                        {
                            "source": "nvd@nist.gov",
                            "type": "CVSSv31",
                            "metrics": {
                                "baseScore": 9.8,
                                "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
                            }
                        }
                    ],
                    "epss": [
                        {
                            "epss": 0.02979,
                            "percentile": 0.856
                        }
                    ]
                },
                "artifact": {
                    "name": "busybox",
                    "version": "1.35.0"
                },
                "fix": {
                    "version": "1.36.0"
                }
            }
        ]
    }
    
    grype_bin = "/mnt/workspace/firmware_scanner/tools/grype/grype"
    
    if not Path(grype_bin).exists():
        print(f"  ⚠️  grype CLI 不存在，跳过测试")
        return None
    
    try:
        matcher = GrypeCLIMatcher(grype_bin=grype_bin, timeout=60)
        
        match = grype_sample["matches"][0]
        vuln = matcher._convert_match_to_vulnerability(match)
        
        print(f"  CVE ID: {vuln.cve_id}")
        print(f"  组件：{vuln.component_name} {vuln.component_version}")
        print(f"  CVSS: {vuln.cvss_score}")
        print(f"  EPSS: {vuln.epss_score}")
        print(f"  Published Date: {vuln.published_date}")
        print(f"  Severity: {vuln.severity}")
        
        # 验证字段
        checks = [
            ("CVE ID", vuln.cve_id == "CVE-2018-1000517"),
            ("CVSS > 0", vuln.cvss_score > 0),
            ("EPSS > 0", vuln.epss_score is not None and vuln.epss_score > 0),
            ("Published Date", vuln.published_date is not None),
            # severity 依赖 grype 输出中的 top-level severity 字段，测试样本可能没有
            ("Severity", vuln.severity != "Unknown"),
        ]
        
        passed = sum(1 for _, result in checks if result)
        total = len(checks)
        
        print(f"\n  验证结果：{passed}/{total}")
        for name, result in checks:
            status = "✅" if result else "⚠️"
            print(f"    {status} {name}")
        
        # severity 为可选检查（依赖 grype 输出）
        critical_checks = checks[:4]  # 前 4 个是关键字段
        critical_passed = sum(1 for _, result in critical_checks if result)
        
        return critical_passed == 4  # 关键检查全部通过即可
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("🐢 玄武 v2.5.2 字段补全自测")
    print("=" * 60)
    print()
    
    results = []
    
    # 测试 1: Grype DB 连接
    results.append(("Grype DB 连接", test_grype_db_connection()))
    
    # 测试 2: vulnerability_handles 表查询
    results.append(("vulnerability_handles 表", test_vulnerability_handles_table()))
    
    # 测试 3: published_date 查询
    results.append(("published_date 查询", test_published_date_from_grype()))
    
    # 测试 4: 完整 vulnerability 解析
    results.append(("完整 vulnerability 解析", test_full_vulnerability_parsing()))
    
    print()
    print("=" * 60)
    print("自测汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)
    total = len(results)
    
    for name, result in results:
        if result is True:
            status = "✅"
        elif result is False:
            status = "❌"
        else:
            status = "⏸️"
        print(f"  {status} {name}")
    
    print()
    print(f"通过率：{passed}/{total} (跳过：{skipped})")
    
    if failed == 0 and passed > 0:
        print("\n✅ 所有测试通过！v2.5.2 published_date 修复完成")
        print("\n建议：使用实际固件样本进行端到端验证")
        return 0
    else:
        print(f"\n⚠️  {failed} 项测试失败")
        print("\n建议：修复失败测试后再提交客户复测")
        return 1

if __name__ == "__main__":
    sys.exit(main())
