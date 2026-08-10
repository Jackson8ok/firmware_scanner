#!/usr/bin/env python3
"""
PDF 报告生成演示脚本
展示如何从扫描结果生成完整的 PDF 安全报告
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from report_generator.pdf_generator import generate_pdf_report
from datetime import datetime

def create_demo_result():
    """创建示例扫描结果"""
    return {
        'filename': 'demo_firmware_v2.3.bin',
        'firmware_type': 'squashfs',
        'file_size': '67.8 MB',
        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        
        # CVE 漏洞列表
        'cves': [
            {
                'cve_id': 'CVE-2021-44228',
                'cvss_score': 10.0,
                'severity': 'Critical',
                'component': 'Apache Log4j 2.14.1',
                'description': 'Log4Shell 远程代码执行漏洞。攻击者可以通过构造特殊的日志输入来执行任意代码。',
                'fixed_version': '2.17.0'
            },
            {
                'cve_id': 'CVE-2021-3156',
                'cvss_score': 8.8,
                'severity': 'High',
                'component': 'sudo 1.8.2-1.9.5p1',
                'description': 'Baron Samedit 堆缓冲区溢出漏洞，允许本地用户提权到 root。',
                'fixed_version': '1.9.5p2'
            },
            {
                'cve_id': 'CVE-2022-22965',
                'cvss_score': 9.8,
                'severity': 'Critical',
                'component': 'Spring Framework 5.3.17',
                'description': 'Spring4Shell 远程代码执行漏洞，影响 Spring MVC 和 WebFlux。',
                'fixed_version': '5.3.18'
            },
            {
                'cve_id': 'CVE-2023-44487',
                'cvss_score': 7.5,
                'severity': 'High',
                'component': 'OpenSSL 3.0.7',
                'description': 'HTTP/2 快速重置攻击（Rapid Reset Attack），可能导致拒绝服务。',
                'fixed_version': '3.0.11'
            },
            {
                'cve_id': 'CVE-2020-8285',
                'cvss_score': 5.3,
                'severity': 'Medium',
                'component': 'Node.js 12.19.0',
                'description': '原型链污染漏洞，可能泄露敏感信息或导致拒绝服务。',
                'fixed_version': '12.21.0'
            }
        ],
        
        # R155 合规评分
        'compliance_score': 65.5,
        
        # 分类得分详情
        'category_scores': {
            'Authentication & Access Control': 45.0,
            'Secure Boot & Integrity': 72.5,
            'Supply Chain Security': 58.0,
            'Vulnerability Management': 35.0,
            'Encryption & Cryptography': 80.0,
            'Logging & Monitoring': 62.5,
            'Network Security': 70.0,
            'Data Protection': 75.0
        },
        
        # 违规项详情
        'violations': [
            {
                'rule_id': 'R155-A1.1',
                'rule_name': '身份验证强度要求',
                'cve_id': 'CVE-2021-44228',
                'component': 'Apache Log4j',
                'penalty_score': 10,
                'description': '存在严重身份验证绕过风险，不符合 EN 303 645 要求'
            },
            {
                'rule_id': 'R155-B2.3',
                'rule_name': '软件更新机制',
                'cve_id': 'CVE-2021-3156',
                'component': 'sudo',
                'penalty_score': 7,
                'description': '未及时更新已知高危漏洞组件'
            },
            {
                'rule_id': 'R155-C1.2',
                'rule_name': '漏洞响应时效',
                'cve_id': 'CVE-2022-22965',
                'component': 'Spring Framework',
                'penalty_score': 8,
                'description': '关键漏洞超过 90 天未修复'
            },
            {
                'rule_id': 'R155-D3.1',
                'rule_name': '加密算法强度',
                'cve_id': None,
                'component': 'OpenSSL',
                'penalty_score': 5,
                'description': '使用弱加密算法套件'
            }
        ],
        
        # SBOM 组件
        'sbom': {
            'components': [
                {'name': 'Linux Kernel', 'version': '5.4.0', 'license': 'GPL-2.0'},
                {'name': 'BusyBox', 'version': '1.33.0', 'license': 'GPL-2.0'},
                {'name': 'OpenSSL', 'version': '1.1.1k', 'license': 'Apache-2.0'},
                {'name': 'curl', 'version': '7.76.1', 'license': 'MIT'},
                {'name': 'OpenSSH', 'version': '8.4p1', 'license': 'BSD-3-Clause'},
                {'name': 'nginx', 'version': '1.18.0', 'license': 'BSD-2-Clause'},
                {'name': 'Python', 'version': '3.8.10', 'license': 'PSF-2.0'},
                {'name': 'libsqlite3', 'version': '3.34.1', 'license': 'Public Domain'}
            ]
        },
        
        # 修复建议
        'recommendations': [
            '立即升级 Apache Log4j 到 2.17.0 或更高版本，消除远程代码执行风险',
            '更新 sudo 到 1.9.5p2，修复 Baron Samedit 提权漏洞',
            '将 Spring Framework 升级到 5.3.18 以上版本，解决 Spring4Shell 漏洞',
            '实施网络层的 WAF 规则，临时缓解 HTTP/2 Rapid Reset 攻击',
            '建立自动化的漏洞扫描和补丁管理机制',
            '加强密码策略，实现多因素认证',
            '启用代码签名和完整性验证机制',
            '定期进行渗透测试和安全审计'
        ]
    }

def main():
    """主函数"""
    print("=" * 70)
    print("🐢 玄武固件安全扫描平台 - PDF 报告生成演示")
    print("=" * 70)
    print()
    
    # 创建示例数据
    scan_result = create_demo_result()
    
    print(f"📦 固件名称：{scan_result['filename']}")
    print(f"📊 文件大小：{scan_result['file_size']}")
    print(f"🔒 R155 合规评分：{scan_result['compliance_score']:.1f}%")
    print(f"🐛 发现漏洞数量：{len(scan_result['cves'])}")
    print()
    
    # 显示漏洞统计
    cves = scan_result['cves']
    critical_count = sum(1 for c in cves if c['cvss_score'] >= 9.0)
    high_count = sum(1 for c in cves if 7.0 <= c['cvss_score'] < 9.0)
    medium_count = sum(1 for c in cves if 4.0 <= c['cvss_score'] < 7.0)
    low_count = sum(1 for c in cves if c['cvss_score'] < 4.0)
    
    print("📈 漏洞严重程度分布:")
    print(f"   🔴 严重 (CVSS ≥ 9.0): {critical_count} 个")
    print(f"   🟠 高危 (CVSS 7.0-8.9): {high_count} 个")
    print(f"   🟡 中危 (CVSS 4.0-6.9): {medium_count} 个")
    print(f"   🟢 低危 (CVSS < 4.0): {low_count} 个")
    print()
    
    # 显示合规情况
    print("🏆 R155 合规分类得分:")
    for category, score in sorted(scan_result['category_scores'].items(), key=lambda x: x[1], reverse=True):
        bar_length = int(score / 5)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        print(f"   {category[:35]:35s} [{bar}] {score:.1f}%")
    print()
    
    # 生成 PDF 报告
    print("📄 正在生成 PDF 报告...")
    task_id = f"demo_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    try:
        # 使用 PDFReportGenerator 类来支持 include_charts 参数
        from report_generator.pdf_generator import PDFReportGenerator
        generator = PDFReportGenerator()
        pdf_path = generator.generate_full_report(task_id, scan_result, include_charts=False)
        
        # 获取文件大小
        file_size = os.path.getsize(pdf_path)
        file_size_mb = file_size / (1024 * 1024)
        
        print()
        print("=" * 70)
        print("✨ PDF 报告生成成功！")
        print("=" * 70)
        print()
        print(f"📂 文件路径：{pdf_path}")
        print(f"📏 文件大小：{file_size:.1f} KB ({file_size_mb:.3f} MB)")
        print()
        
        # API 下载链接
        host = "localhost:8000"
        download_url = f"http://{host}/api/task/{task_id}/report/pdf"
        
        print("🔗 下载链接:")
        print(f"   {download_url}")
        print()
        print("💻 命令行下载:")
        print(f"   curl -o firmware_report.pdf '{download_url}'")
        print()
        print("✅ 演示完成！")
        print()
        
        return pdf_path
        
    except Exception as e:
        print(f"❌ PDF 生成失败：{e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()
