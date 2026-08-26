#!/usr/bin/env python3
"""
模板报告生成器测试脚本 - v2.6.0

测试所有模板类型的报告生成功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from report_generator.template_report import (
    TemplateReportGenerator, 
    ScanResult,
    generate_report
)


def create_test_scan_result() -> ScanResult:
    """创建测试扫描结果"""
    return ScanResult(
        task_id="test-001",
        firmware_name="OpenWrt_21.02.5_bcm27xx_bcm2711_ext4-factory.img.gz",
        firmware_hash="sha256:a1b2c3d4e5f6...",
        scan_date="2026-08-26 15:30:00",
        duration=45.8,
        total_components=156,
        total_vulns=47,
        critical_count=3,
        high_count=8,
        medium_count=15,
        low_count=21,
        cvss_avg=7.2,
        epss_avg=0.15,
        vulnerabilities=[
            {
                "cve_id": "CVE-2026-1234",
                "severity": "Critical",
                "component_name": "openssl",
                "component_version": "1.1.1k",
                "cvss_score": 9.8,
                "epss_score": 0.85,
                "published_date": "2026-01-15",
                "description": "OpenSSL 中存在严重缓冲区溢出漏洞，允许远程攻击者执行任意代码",
                "fixed_version": "1.1.1l"
            },
            {
                "cve_id": "CVE-2026-5678",
                "severity": "High",
                "component_name": "curl",
                "component_version": "7.79.0",
                "cvss_score": 7.5,
                "epss_score": 0.45,
                "published_date": "2026-03-20",
                "description": "Curl 中存在信息泄露漏洞，可能导致敏感数据暴露",
                "fixed_version": "7.79.1"
            },
            {
                "cve_id": "CVE-2026-9012",
                "severity": "Medium",
                "component_name": "zlib",
                "component_version": "1.2.11",
                "cvss_score": 5.3,
                "epss_score": 0.25,
                "published_date": "2026-05-10",
                "description": "Zlib 中存在拒绝服务漏洞，可能导致应用程序崩溃",
                "fixed_version": "1.2.12"
            },
            {
                "cve_id": "CVE-2026-3456",
                "severity": "Low",
                "component_name": "busybox",
                "component_version": "1.35.0",
                "cvss_score": 3.1,
                "epss_score": 0.08,
                "published_date": "2026-06-01",
                "description": "BusyBox 中存在轻微的信息泄露问题",
                "fixed_version": "1.35.1"
            }
        ],
        components=[
            {"name": "openssl", "version": "1.1.1k"},
            {"name": "curl", "version": "7.79.0"},
            {"name": "zlib", "version": "1.2.11"},
            {"name": "busybox", "version": "1.35.0"},
            {"name": "linux-kernel", "version": "5.15.0"}
        ]
    )


def test_all_templates():
    """测试所有模板"""
    print("=" * 80)
    print("🐢 玄武·AFVS v2.6.0 模板报告生成器测试")
    print("=" * 80)
    
    # 创建生成器和测试数据
    gen = TemplateReportGenerator()
    scan_result = create_test_scan_result()
    
    # 测试输出目录
    output_dir = "/mnt/workspace/firmware_scanner/data/reports/test_templates"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n📁 输出目录：{output_dir}")
    print(f"📊 测试数据：{scan_result.total_vulns} 个漏洞，{scan_result.total_components} 个组件\n")
    
    # 测试每个模板
    templates_to_test = ["simple", "standard", "detailed", "json"]
    
    for template_name in templates_to_test:
        print(f"\n{'='*60}")
        print(f"📋 测试模板：{template_name.upper()}")
        print(f"{'='*60}")
        
        try:
            # 设置模板
            gen.set_template(template_name)
            
            # 确定输出格式
            if template_name == "json":
                output_format = "json"
            else:
                output_format = "html"
            
            # 生成报告
            output_path = f"{output_dir}/test_{template_name}.{output_format}"
            
            content = gen.generate(
                scan_result,
                output_format=output_format,
                output_path=output_path
            )
            
            # 显示结果
            if output_format == "json":
                print(f"✅ JSON 报告已生成：{output_path}")
                print(f"   大小：{len(content)} 字节")
            else:
                print(f"✅ HTML 报告已生成：{output_path}")
                print(f"   大小：{len(content)} 字节")
                print(f"   漏洞数：{len(gen._filter_vulns(scan_result.vulnerabilities, gen.current_template.filters))}")
            
        except Exception as e:
            print(f"❌ 测试失败：{e}")
            import traceback
            traceback.print_exc()
    
    # 测试便捷函数
    print(f"\n{'='*60}")
    print("📦 测试便捷函数 generate_report()")
    print(f"{'='*60}")
    
    try:
        report = generate_report(
            scan_result,
            template="standard",
            format="html",
            output_path=f"{output_dir}/test_quick.html"
        )
        print(f"✅ 便捷函数测试通过：{output_dir}/test_quick.html")
    except Exception as e:
        print(f"❌ 便捷函数测试失败：{e}")
    
    # 总结
    print(f"\n{'='*80}")
    print("✅ 所有模板测试完成！")
    print(f"{'='*80}")
    print(f"\n📁 生成的测试报告位于：{output_dir}")
    print(f"\n💡 提示:")
    print(f"   - 使用浏览器打开 HTML 报告查看效果")
    print(f"   - 使用 'cat' 或文本编辑器查看 JSON 报告")
    print(f"   - 在生产环境中使用 API 端点调用模板生成")
    print()


if __name__ == "__main__":
    test_all_templates()
