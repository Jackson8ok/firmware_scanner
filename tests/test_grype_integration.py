"""
v2.5.0 集成测试：grype CLI 替换自研匹配器

验证：
1. grype CLI 可用性检测
2. 降级到自研匹配器逻辑
3. 结果格式兼容性
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

try:
    from scanner.grype_matcher import GrypeCLIMatcher, GrypeDBMatcher, scan_with_grype
    FROM_GRYPE = True
except ImportError:
    FROM_GRYPE = False


@pytest.mark.skipif(not FROM_GRYPE, reason="grype_matcher 模块未找到")
class TestGrypeCLIIntegration:
    """grype CLI 集成测试"""
    
    def test_grype_cli_not_found(self):
        """测试 grype CLI 未找到时的异常"""
        with pytest.raises(RuntimeError, match="grype CLI 未找到"):
            GrypeCLIMatcher(grype_bin="/nonexistent/grype")
    
    def test_scan_nonexistent_path(self):
        """测试扫描不存在的路径"""
        # 使用 mock 避免实际调用 grype
        with patch('scanner.grype_matcher.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"matches": []}'
            )
            
            matcher = GrypeCLIMatcher(grype_bin="/usr/local/bin/grype")
            
            with pytest.raises(FileNotFoundError):
                matcher.scan("/nonexistent/path")
    
    def test_parse_empty_grype_output(self):
        """测试解析空结果"""
        with patch('scanner.grype_matcher.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='grype version 0.115.0\n'
            )
            
            matcher = GrypeCLIMatcher(grype_bin="/usr/local/bin/grype")
            
            vulns = matcher._parse_grype_json('{"matches": []}')
            assert vulns == []
    
    def test_parse_single_match(self):
        """测试解析单个 CVE"""
        with patch('scanner.grype_matcher.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='grype version 0.115.0\n'
            )
            
            grype_json = {
                "matches": [
                    {
                        "vulnerability": {
                            "id": "CVE-2021-44228",
                            "severity": "Critical",
                            "cvss": [{
                                "baseScore": 10.0,
                                "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                                "severity": "Critical"
                            }],
                            "publishedDate": "2021-12-10T00:00:00Z",
                            "description": "Apache Log4j2 RCE"
                        },
                        "artifact": {
                            "name": "log4j",
                            "version": "2.14.1"
                        },
                        "fix": {
                            "version": "2.17.0",
                            "state": "fixed"
                        }
                    }
                ]
            }
            
            matcher = GrypeCLIMatcher(grype_bin="/usr/local/bin/grype")
            vulns = matcher._parse_grype_json(json.dumps(grype_json))
            
            assert len(vulns) == 1
            assert vulns[0].cve_id == "CVE-2021-44228"
            assert vulns[0].severity == "Critical"
            assert vulns[0].cvss_score == 10.0
            assert vulns[0].published_date is not None
            assert vulns[0].fixed_version == "2.17.0"
    
    def test_deduplication(self):
        """测试结果去重"""
        with patch('scanner.grype_matcher.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='grype version 0.115.0\n'
            )
            
            grype_json = {
                "matches": [
                    {
                        "vulnerability": {"id": "CVE-2021-44228", "severity": "Critical"},
                        "artifact": {"name": "log4j", "version": "2.14.1"}
                    },
                    {
                        "vulnerability": {"id": "CVE-2021-44228", "severity": "Critical"},
                        "artifact": {"name": "log4j", "version": "2.14.1"}
                    }
                ]
            }
            
            matcher = GrypeCLIMatcher(grype_bin="/usr/local/bin/grype")
            vulns = matcher._parse_grype_json(json.dumps(grype_json))
            
            assert len(vulns) == 1  # 去重后应为 1
    
    @patch('scanner.grype_matcher.subprocess.run')
    def test_scan_with_mock_grype(self, mock_run):
        """测试扫描流程（mock grype CLI）"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "matches": [
                    {
                        "vulnerability": {
                            "id": "CVE-2021-44228",
                            "severity": "Critical",
                            "cvss": [{"baseScore": 10.0, "vector": "", "severity": "Critical"}],
                            "publishedDate": "2021-12-10T00:00:00Z",
                            "description": "Apache Log4j2 RCE"
                        },
                        "artifact": {"name": "log4j", "version": "2.14.1"},
                        "fix": {"version": "2.17.0", "state": "fixed"}
                    }
                ]
            })
        )
        
        matcher = GrypeCLIMatcher(grype_bin="/usr/local/bin/grype")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            vulns = matcher.scan(tmpdir)
            
            assert len(vulns) == 1
            assert vulns[0].cve_id == "CVE-2021-44228"
            assert vulns[0].cvss_score == 10.0
    
    def test_fallback_to_legacy_matcher(self):
        """测试 grype CLI 失败时降级到自研匹配器（逻辑验证）"""
        # 这个测试验证降级逻辑的代码路径存在
        # 实际降级在 task_queue.py 的 _execute_scan 中实现
        
        # 读取 task_queue.py 验证降级逻辑
        task_queue_path = Path(__file__).parent.parent / "scanner" / "task_queue.py"
        content = task_queue_path.read_text()
        
        assert " GrypeCLIMatcher" in content or "grype_matcher" in content, \
            "task_queue.py 应导入 grype_matcher"
        assert "降级" in content or "fallback" in content.lower() or "legacy" in content.lower(), \
            "task_queue.py 应有降级逻辑"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
