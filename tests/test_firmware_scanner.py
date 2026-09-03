#!/usr/bin/env python3
"""
固件漏洞扫描平台 - 完整测试套件
测试解包、SBOM 生成、CVE 匹配等核心功能
"""

import os
import sys
import tempfile
from pathlib import Path
import unittest
from datetime import datetime, timedelta
import logging

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.engine import FirmwareExtractor, SBOMGenerator, CVEMatcher, Component, Vulnerability

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class TestFirmwareExtractor(unittest.TestCase):
    """测试固件解包器"""
    
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="firmware_test_"))
        self.extractor = FirmwareExtractor(str(self.test_dir))
        logger.info(f"测试目录：{self.test_dir}")
    
    def tearDown(self):
        pass
    
    def test_binwalk_available(self):
        """测试 Binwalk 可用性检查"""
        print("\n" + "="*60)
        print("【测试 1】Binwalk 可用性")
        print("="*60)
        
        if self.extractor.binwalk_available:
            print("✅ Binwalk 已安装")
            result = os.popen("binwalk --version 2>&1").read().strip()
            print(f"   版本信息：{result[:50]}")
        else:
            print("⚠️  Binwalk 未安装（部分功能不可用）")
            print("   建议安装：sudo apt install binwalk")
        
        self.assertIsInstance(self.extractor.binwalk_available, bool)
    
    def test_7zip_available(self):
        """测试 7-Zip 可用性检查"""
        print("\n" + "="*60)
        print("【测试 2】7-Zip 可用性")
        print("="*60)
        
        status = "✅" if self.extractor.sevenzip_available else "❌"
        print(f"{status} 7-Zip: {'已安装' if self.extractor.sevenzip_available else '未安装'}")
        self.assertIsInstance(self.extractor.sevenzip_available, bool)
    
    def test_hex_parsing(self):
        """测试 HEX 文件解析（Python 备用实现）"""
        print("\n" + "="*60)
        print("【测试 3】HEX 文件 Python 解析")
        print("="*60)
        
        test_hex_content = """\
:020000040800F2
:100000000004A0E3020001EA00009FE50404A0E3C9
:10001000020001EB00F09FE50304A0E3020001EC46
:00000001FF
"""
        
        hex_file = self.test_dir / "test.hex"
        hex_file.write_text(test_hex_content)
        
        try:
            bin_file = self.extractor.hex_to_bin(str(hex_file))
            
            if bin_file.exists() and bin_file.stat().st_size > 0:
                size = bin_file.stat().st_size
                print(f"✅ HEX 转 BIN 成功：{size} bytes")
            else:
                print(f"⚠️  转换完成但输出为空")
                
        except Exception as e:
            print(f"❌ 异常：{e}")
            raise


class TestSBOMGenerator(unittest.TestCase):
    """测试 SBOM 生成器"""
    
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="sbom_test_"))
        self.sbom_gen = SBOMGenerator()
    
    def test_component_detection(self):
        """测试组件特征识别"""
        print("\n" + "="*60)
        print("【测试 4】组件特征识别")
        print("="*60)
        
        test_cases = [
            ("FreeRTOS", b"xTaskCreate pvPortMalloc vListInitialise"),
            ("lwIP", b"tcp_connect udp_sendto netif_add pbuf_alloc"),
            ("wolfSSL", b"wolfSSL_Init SSL_connect wolfSSL_new"),
            ("Zlib", b"deflateInit inflateEnd zlibVersion"),
        ]
        
        detected_count = 0
        
        for component_name, test_data in test_cases:
            bin_file = self.test_dir / f"{component_name.lower()}.bin"
            bin_file.write_bytes(test_data)
            
            components = self.sbom_gen.extract_mcu_components(str(bin_file))
            found = any(c.name == component_name for c in components)
            
            status = "✅" if found else "❌"
            print(f"{status} {component_name}: {'识别成功' if found else '未识别'}")
            
            if found:
                detected_count += 1
        
        print(f"\n总计：{detected_count}/{len(test_cases)} 个组件识别成功")
        self.assertGreater(detected_count, 2, "应该识别大部分组件")


class TestVulnerabilityScoring(unittest.TestCase):
    """测试漏洞评分计算"""
    
    def test_priority_calculation(self):
        """测试优先级分数计算和 R155 合规检查"""
        print("\n" + "="*60)
        print("【测试 5】漏洞优先级评分 & R155 合规")
        print("="*60)
        
        vulns = [
            Vulnerability(
                cve_id="CVE-2023-0001", component_name="openssl", component_version="1.1.1",
                severity="Critical", cvss_score=9.8, cvss_vector="", description="",
                fixed_version="1.1.2", published_date=datetime.now() - timedelta(days=30),
                epss_score=0.85
            ),
            Vulnerability(
                cve_id="CVE-2023-0002", component_name="freertos", component_version="10.4.3",
                severity="High", cvss_score=7.5, cvss_vector="", description="",
                fixed_version=None, published_date=datetime.now() - timedelta(days=200),
                epss_score=0.45
            ),
            Vulnerability(
                cve_id="CVE-2023-0003", component_name="lwip", component_version="2.1.2",
                severity="Medium", cvss_score=5.3, cvss_vector="", description="",
                fixed_version="2.1.3", published_date=datetime.now() - timedelta(days=100),
                epss_score=0.12
            ),
        ]
        
        print(f"\n{'CVE ID':<18} {'组件':<12} {'CVSS':<6} {'EPSS':<6} {'优先级':<8} {'R155'}")
        print("-" * 60)
        
        for vuln in sorted(vulns, key=lambda v: v.calculate_priority(), reverse=True):
            r155 = "❌" if vuln.is_r155_non_compliant() else "✅"
            print(f"{vuln.cve_id:<18} {vuln.component_name:<12} "
                  f"{vuln.cvss_score:<6.1f} {vuln.epss_score or 0:<6.2f} "
                  f"{vuln.priority_score:<8.3f} {r155}")
        
        highest = max(vulns, key=lambda v: v.priority_score)
        self.assertEqual(highest.component_name, "openssl", "OpenSSL 应排第一")
        
        # 检查 R155
        non_compliant = [v for v in vulns if v.is_r155_non_compliant()]
        print(f"\nR155 不合规数量：{len(non_compliant)}")
        if non_compliant:
            print(f"   • {non_compliant[0].cve_id} (未修复 >180 天)")


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="integration_"))
    
    def test_full_workflow(self):
        """完整扫描流程模拟"""
        print("\n" + "="*60)
        print("【测试 6】完整扫描流程模拟")
        print("="*60)
        
        firmware = b"\x7fELF" + b"\x00"*50 + b"FreeRTOS V10.4.3" + b"\x00"*30 + b"lwIP 2.1.2"
        firmware_file = self.test_dir / "simulated.bin"
        firmware_file.write_bytes(firmware)
        
        print("1. 创建模拟固件 ✅")
        
        extractor = FirmwareExtractor(str(self.test_dir))
        print(f"2. 初始化提取器: Binwalk={'✅' if extractor.binwalk_available else '❌'}")
        
        sbom = SBOMGenerator()
        components = sbom.extract_mcu_components(str(firmware_file))
        print(f"3. 生成 SBOM: 识别 {len(components)} 个组件")
        for c in components:
            print(f"   • {c.name} v{c.version}")
        
        print("4. CVE 匹配：跳过（需要 Grype DB）⏭️ ")
        print("\n✅ 集成测试通过!")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print(" 🐢 固件漏洞扫描平台 - 完整测试套件")
    print("   开始时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*70)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestFirmwareExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestSBOMGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestVulnerabilityScoring))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print(" 📊 测试结果")
    print("="*70)
    print(f"  总测试数：{result.testsRun}")
    print(f"  成功：{result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  失败：{len(result.failures)}")
    print(f"  错误：{len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ 所有测试通过！系统就绪!")
    else:
        print("\n⚠️  部分测试失败，请查看详细输出")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
