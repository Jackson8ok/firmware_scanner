#!/usr/bin/env python3
"""
PDF 报告生成测试脚本
用于验证 PDF 生成功能是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from report_generator.pdf_generator import generate_pdf_report

def test_pdf_generation():
    """测试 PDF 报告生成"""
    
    # 模拟扫描结果数据
    test_data = {
        'filename': 'test_firmware.bin',
        'firmware_type': 'squashfs',
        'file_size': '45.2 MB',
        'scan_time': '2026-07-27 11:30:00',
        'compliance_score': 68.5,
        'cves': [
            {
                'cve_id': 'CVE-2021-44228',
                'cvss_score': 10.0,
                'component': 'Apache Log4j',
                'version': '2.14.1',
                'description': 'Log4Shell 远程代码执行漏洞，允许攻击者通过恶意构造的日志消息执行任意代码。'
            },
            {
                'cve_id': 'CVE-2021-3156',
                'cvss_score': 8.8,
                'component': 'sudo',
                'version': '1.8.31',
                'description': '堆缓冲区溢出漏洞，允许普通用户以 root 权限执行命令。'
            },
            {
                'cve_id': 'CVE-2020-1938',
                'cvss_score': 9.8,
                'component': 'Apache Tomcat',
                'version': '9.0.30',
                'description': 'GhostCat 漏洞，允许攻击者读取或包含 Apache Tomcat 上的文件。'
            }
        ],
        'category_scores': {
            'Authentication & Access Control': 55.0,
            'Secure Boot': 82.0,
            'Supply Chain Security': 72.5,
            'Vulnerability Management': 60.0,
            'Encryption': 75.0,
            'Logging & Auditing': 65.0,
            'Integrity Verification': 70.0
        },
        'violating_cves': 3,
        'recommendations': [
            '立即升级到 Apache Log4j 2.17.0 或更高版本',
            '更新 sudo 到最新版本（>= 1.9.5p2）',
            '升级 Apache Tomcat 到 9.0.40 或更高版本',
            '实施最小权限原则，禁用不必要的服务',
            '启用安全启动和固件签名验证'
        ],
        'sbom': {
            'components': [
                {'name': 'linux-kernel', 'version': '5.4.0', 'license': 'GPL-2.0'},
                {'name': 'busybox', 'version': '1.33.1', 'license': 'GPL-2.0'},
                {'name': 'openssl', 'version': '1.1.1k', 'license': 'Apache-2.0'},
                {'name': 'nginx', 'version': '1.20.1', 'license': 'BSD-2-Clause'}
            ]
        }
    }
    
    print("🐢 玄武固件扫描平台 - PDF 报告生成测试")
    print("=" * 50)
    print("\n📊 测试数据:")
    print(f"  • 固件名称: {test_data['filename']}")
    print(f"  • R155 合规评分：{test_data['compliance_score']}%")
    print(f"  • 发现 CVE: {len(test_data['cves'])} 个")
    print(f"  • 分类得分: {len(test_data['category_scores'])} 个维度")
    
    try:
        print("\n📄 正在生成 PDF 报告...")
        pdf_path = generate_pdf_report('test_20260727', test_data)
        
        print(f"\n✅ PDF 报告生成成功!")
        print(f"   路径：{pdf_path}")
        print(f"   文件大小：{Path(pdf_path).stat().st_size / 1024:.2f} KB")
        
        return True
        
    except Exception as e:
        print(f"\n❌ PDF 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_pdf_generation()
    sys.exit(0 if success else 1)
