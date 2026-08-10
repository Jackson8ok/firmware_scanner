#!/usr/bin/env python3
"""
CycloneDX SBOM 功能测试脚本

测试内容:
1. 组件生成
2. 漏洞关联
3. Schema 验证
4. API 端点调用
5. 降级模式（无依赖时）
"""

import sys
from pathlib import Path
import json

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from scanner.cyclonedx_sbom import (
    generate_cyclonedx_sbom, 
    validate_sbom, 
    HAS_CYCLONEDX
)
from scanner.engine import Component, Vulnerability


def test_basic_generation():
    """测试基本 SBOM 生成"""
    print("\n" + "="*60)
    print("📦 测试 1: 基本 SBOM 生成")
    print("="*60)
    
    components = [
        {'name': 'FreeRTOS', 'version': '10.4.6', 'type': 'operating-system'},
        {'name': 'lwIP', 'version': '2.1.3', 'type': 'library'},
        {'name': 'wolfSSL', 'version': '4.6.0', 'type': 'library'}
    ]
    
    try:
        sbom = generate_cyclonedx_sbom(components=components)
        
        # 解析并验证结构
        data = json.loads(sbom)
        
        assert data['bomFormat'] == 'CycloneDX', "BOM 格式错误"
        assert data['specVersion'] in ['1.4', '1.3'], "Schema 版本错误"
        assert len(data['components']) == 3, "组件数量错误"
        
        print(f"✅ SBOM 生成成功!")
        print(f"   - Format: {data['bomFormat']}")
        print(f"   - Version: {data['specVersion']}")
        print(f"   - Components: {len(data['components'])}")
        print(f"   - Size: {len(sbom)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_vulnerability_integration():
    """测试漏洞关联"""
    print("\n" + "="*60)
    print("🛡️ 测试 2: 漏洞关联")
    print("="*60)
    
    components = [
        {'name': 'Log4j', 'version': '2.14.1', 'type': 'library'},
        {'name': 'OpenSSL', 'version': '1.1.1k', 'type': 'library'}
    ]
    
    vulnerabilities = [
        {
            'id': 'CVE-2021-44228',
            'source': 'NVD',
            'description': 'Log4Shell RCE',
            'ratings': [{'method': 'CVSSv31', 'severity': 'critical', 'score': 10.0}],
            'published': '2021-12-10'
        },
        {
            'id': 'CVE-2021-3711',
            'source': 'NVD',
            'description': 'OpenSSL SM2 Decryption Buffer Overflow',
            'ratings': [{'method': 'CVSSv31', 'severity': 'high', 'score': 9.1}],
            'published': '2021-08-24'
        }
    ]
    
    try:
        sbom = generate_cyclonedx_sbom(
            components=components,
            vulnerabilities=vulnerabilities
        )
        
        data = json.loads(sbom)
        
        assert 'vulnerabilities' in data, "缺少 vulnerabilities 字段"
        assert len(data['vulnerabilities']) == 2, "漏洞数量错误"
        
        print(f"✅ 漏洞关联成功!")
        print(f"   - Vulnerabilities: {len(data['vulnerabilities'])}")
        for vuln in data['vulnerabilities']:
            print(f"     • {vuln['id']} ({vuln['ratings'][0]['severity']})")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation():
    """测试 SBOM 验证"""
    print("\n" + "="*60)
    print("✓ 测试 3: Schema 验证")
    print("="*60)
    
    components = [
        {'name': 'TestComponent', 'version': '1.0.0', 'type': 'library'}
    ]
    
    try:
        sbom = generate_cyclonedx_sbom(components=components)
        is_valid = validate_sbom(sbom)
        
        if is_valid:
            print("✅ SBOM 验证通过")
            return True
        else:
            print("❌ SBOM 验证失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return False


def test_downgrade_mode():
    """测试降级模式（当 cyclonedx 库不可用时）"""
    print("\n" + "="*60)
    print("🔧 测试 4: 降级模式")
    print("="*60)
    
    components = [
        {'name': 'FallbackTest', 'version': '0.0.1', 'type': 'library'}
    ]
    
    try:
        sbom = generate_cyclonedx_sbom(components=components)
        
        # 即使没有标准库，也应该能生成基本格式
        data = json.loads(sbom)
        
        assert 'bomFormat' in data, "缺少 bomFormat 字段"
        assert 'components' in data, "缺少 components 字段"
        
        mode = "标准模式" if HAS_CYCLONEDX else "降级模式"
        print(f"✅ {mode}工作正常")
        print(f"   - HAS_CYCLONEDX: {HAS_CYCLONEDX}")
        print(f"   - BOM Format: {data['bomFormat']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return False


def test_api_endpoint():
    """测试 API 端点（需要服务器运行）"""
    print("\n" + "="*60)
    print("🌐 测试 5: API 端点")
    print("="*60)
    
    try:
        import requests
        
        # 假设服务器运行在 localhost:8000
        response = requests.get(
            "http://localhost:8000/api/sbom/test-task-id",
            params={'format': 'cyclonedx', 'schema_version': '1.4'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = json.loads(response.content)
            print(f"✅ API 端点响应成功")
            print(f"   - Status: {response.status_code}")
            print(f"   - Content-Type: {response.headers.get('Content-Type')}")
            return True
        elif response.status_code == 404:
            print(f"⚠️ 任务不存在（预期行为，因为 task_id 是假的）")
            return True
        else:
            print(f"❌ API 请求失败：{response.status_code}")
            return False
            
    except requests.ConnectionError:
        print(f"⚠️ 服务器未运行（跳过 API 测试）")
        print(f"   启动服务器：cd firmware_scanner && python api/main.py")
        return None  # 非致命错误
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return False


def save_sample_sbom():
    """保存示例 SBOM 到文件"""
    print("\n" + "="*60)
    print("💾 保存示例 SBOM")
    print("="*60)
    
    components = [
        {
            'name': 'FreeRTOS',
            'version': '10.4.6',
            'type': 'operating-system',
            'description': 'Real-time operating system for embedded devices',
            'cpe': 'cpe:2.3:o:freertos:freertos:10.4.6:*:*:*:*:*:*:*'
        },
        {
            'name': 'lwIP',
            'version': '2.1.3',
            'type': 'library',
            'description': 'Lightweight TCP/IP stack',
            'cpe': 'cpe:2.3:a:lwip:lwip:2.1.3:*:*:*:*:*:*:*'
        },
        {
            'name': 'wolfSSL',
            'version': '4.6.0',
            'type': 'library',
            'description': 'TLS/SSL library',
            'cpe': 'cpe:2.3:a:wolfssl:wolfssl:4.6.0:*:*:*:*:*:*:*'
        }
    ]
    
    vulnerabilities = [
        {
            'id': 'CVE-2022-30801',
            'source': 'NVD',
            'description': 'FreeRTOS heap corruption vulnerability',
            'ratings': [
                {'method': 'CVSSv31', 'severity': 'high', 'score': 8.8}
            ],
            'published': '2022-03-15',
            'recommendations': ['Upgrade to FreeRTOS 202202.00 or later']
        }
    ]
    
    try:
        sbom = generate_cyclonedx_sbom(
            components=components,
            vulnerabilities=vulnerabilities,
            schema_version="1.4"
        )
        
        output_path = "./sample_sbom.cyclonedx.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(sbom)
        
        print(f"✅ 示例 SBOM 已保存到：{output_path}")
        print(f"   - Size: {len(sbom)} bytes")
        print(f"   - Components: {len(components)}")
        print(f"   - Vulnerabilities: {len(vulnerabilities)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 保存失败：{e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "🚀 "*20)
    print(" " * 20 + "CycloneDX SBOM 功能测试套件")
    print("🚀 "*20)
    
    results = {}
    
    # 检查依赖
    print(f"\n📋 环境检查:")
    print(f"   - HAS_CYCLONEDX: {'✅' if HAS_CYCLONEDX else '❌'}")
    if not HAS_CYCLONEDX:
        print(f"   💡 提示：运行 'pip install cyclonedx-python-lib' 安装完整支持")
    
    # 运行测试
    tests = [
        ("基本生成", test_basic_generation),
        ("漏洞关联", test_vulnerability_integration),
        ("Schema 验证", test_validation),
        ("降级模式", test_downgrade_mode),
        ("保存示例", save_sample_sbom),
    ]
    
    for name, test_func in tests:
        results[name] = test_func()
    
    # API 测试（可选）
    api_result = test_api_endpoint()
    if api_result is not None:
        results["API 端点"] = api_result
    
    # 汇总
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for name, result in results.items():
        status = "✅" if result else ("⚠️" if result is None else "❌")
        print(f"   {status} {name}")
    
    print(f"\n总计：{passed} 通过, {failed} 失败, {skipped} 跳过")
    
    # 退出码
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
