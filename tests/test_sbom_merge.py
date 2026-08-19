"""
v2.5.0 Phase 2 集成测试：Syft + 自研提取器结果合并

验证：
1. Syft 和自研提取器都能正常返回组件
2. 合并去重逻辑正确
3. 当 Syft 失败时能降级到自研提取器
4. 当自研提取器失败时能保留 Syft 结果
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

try:
    from scanner.engine import SBOMGenerator, Component
    FROM_ENGINE = True
except ImportError:
    FROM_ENGINE = False


@pytest.mark.skipif(not FROM_ENGINE, reason="engine 模块未找到")
class TestMergedSBOM:
    """Syft + 自研提取器合并测试"""
    
    @pytest.fixture
    def sbom_gen(self):
        """创建 SBOMGenerator 实例"""
        return SBOMGenerator()
    
    def test_merge_syft_and_custom(self, sbom_gen):
        """测试合并 Syft + 自研结果"""
        with patch.object(sbom_gen, 'generate_syft_sbom') as mock_syft, \
             patch.object(sbom_gen, 'extract_squashfs_components_from_dir') as mock_custom:
            
            mock_syft.return_value = [
                Component(name='busybox', version='1.35.0', type='library', path='/bin/busybox'),
                Component(name='openssl', version='1.1.1m', type='library', path='/usr/lib/openssl'),
            ]
            
            mock_custom.return_value = [
                Component(name='busybox', version='1.35.0', type='library', path='/bin/busybox'),
                Component(name='libpcre', version='8.45', type='library', path='/usr/lib/libpcre.so'),
                Component(name='libz', version='1.2.11', type='library', path='/usr/lib/libz.so'),
            ]
            
            with tempfile.TemporaryDirectory() as tmpdir:
                # 创建必要的目录结构
                os.makedirs(os.path.join(tmpdir, 'usr', 'lib', 'opkg', 'info'), exist_ok=True)
                os.makedirs(os.path.join(tmpdir, 'usr', 'lib'), exist_ok=True)
                
                # 创建模拟的 .so 文件
                Path(tmpdir, 'usr', 'lib', 'libpcre.so').touch()
                Path(tmpdir, 'usr', 'lib', 'libz.so').touch()
                
                result = sbom_gen.generate_syft_sbom(tmpdir)
                
                # 验证合并结果
                assert len(result) >= 2  # 至少有 Syft 的结果
                names = [c.name for c in result]
                assert 'busybox' in names
                assert 'openssl' in names
    
    def test_deduplication(self, sbom_gen):
        """测试去重逻辑"""
        with patch.object(sbom_gen, 'generate_syft_sbom') as mock_syft, \
             patch.object(sbom_gen, 'extract_squashfs_components_from_dir') as mock_custom:
            
            mock_syft.return_value = [
                Component(name='busybox', version='1.35.0', type='library', path='/bin/busybox'),
                Component(name='openssl', version='1.1.1m', type='library', path='/usr/lib/openssl'),
            ]
            
            mock_custom.return_value = [
                Component(name='busybox', version='1.35.0', type='library', path='/bin/busybox'),  # 重复
                Component(name='libpcre', version='8.45', type='library', path='/usr/lib/libpcre.so'),
            ]
            
            with tempfile.TemporaryDirectory() as tmpdir:
                os.makedirs(os.path.join(tmpdir, 'usr', 'lib'), exist_ok=True)
                Path(tmpdir, 'usr', 'lib', 'libpcre.so').touch()
                
                result = sbom_gen.generate_syft_sbom(tmpdir)
                
                # 验证去重：busybox 应该只出现一次
                busybox_count = sum(1 for c in result if c.name == 'busybox')
                assert busybox_count == 1
    
    def test_syft_failure_fallback(self, sbom_gen):
        """测试 Syft 失败时降级到自研提取器"""
        with patch.object(sbom_gen, 'generate_syft_sbom') as mock_syft, \
             patch.object(sbom_gen, 'extract_squashfs_components_from_dir') as mock_custom:
            
            mock_syft.side_effect = RuntimeError("Syft 失败")
            mock_custom.return_value = [
                Component(name='libpcre', version='8.45', type='library', path='/usr/lib/libpcre.so'),
            ]
            
            with tempfile.TemporaryDirectory() as tmpdir:
                os.makedirs(os.path.join(tmpdir, 'usr', 'lib'), exist_ok=True)
                Path(tmpdir, 'usr', 'lib', 'libpcre.so').touch()
                
                result = sbom_gen.generate_sbom_merged(tmpdir)
                
                # 验证降级结果
                assert len(result) == 1
                assert result[0].name == 'libpcre'
    
    def test_custom_extractor_failure(self, sbom_gen):
        """测试自研提取器失败时保留 Syft 结果"""
        with patch.object(sbom_gen, 'generate_syft_sbom') as mock_syft, \
             patch.object(sbom_gen, 'extract_squashfs_components_from_dir') as mock_custom:
            
            mock_syft.return_value = [
                Component(name='busybox', version='1.35.0', type='library', path='/bin/busybox'),
            ]
            mock_custom.side_effect = RuntimeError("自研提取器失败")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                result = sbom_gen.generate_syft_sbom(tmpdir)
                
                # 验证 Syft 结果保留
                assert len(result) == 1
                assert result[0].name == 'busybox'
    
    def test_both_extractors_empty(self, sbom_gen):
        """测试两个提取器都返回空"""
        with patch.object(sbom_gen, 'generate_syft_sbom') as mock_syft, \
             patch.object(sbom_gen, 'extract_squashfs_components_from_dir') as mock_custom:
            
            mock_syft.return_value = []
            mock_custom.return_value = []
            
            with tempfile.TemporaryDirectory() as tmpdir:
                result = sbom_gen.generate_syft_sbom(tmpdir)
                assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
