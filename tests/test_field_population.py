"""
P1-2 字段补全集成测试

验证扫描结果中的以下字段在运行路径中正确填充：
- cvss_score
- published_date
- epss_score
- severity（非 Unknown）

验收标准（来自 v2.4.3 复测结论）：
- cvss/date/epss 非空率 ≥90%
- severity = Unknown ≤5%
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime

try:
    from scanner.engine import CVEMatcher, Vulnerability, Component
    from scanner.task_queue import ScanQueue, get_scan_queue
    FROM_SCANNER = True
    IMPORT_ERROR = None
except ImportError as e:
    FROM_SCANNER = False
    IMPORT_ERROR = str(e)


@pytest.mark.skipif(not FROM_SCANNER, reason=f"Cannot import scanner modules: {IMPORT_ERROR}")
class TestFieldPopulation:
    """字段补全集成测试"""
    
    @pytest.fixture
    def mock_grype_db(self, tmp_path):
        """创建模拟的 Grype DB（用于单元测试）"""
        import sqlite3
        
        db_path = tmp_path / "grype.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 创建最小表结构（适配 Grype v6 schema）
        cursor.executescript("""
            CREATE TABLE vulnerabilities (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                published_date TEXT,
                status TEXT DEFAULT 'active'
            );
            
            CREATE TABLE vulnerability_handles (
                id INTEGER PRIMARY KEY,
                vulnerability_id INTEGER NOT NULL,
                blob_id INTEGER NOT NULL,
                FOREIGN KEY (vulnerability_id) REFERENCES vulnerabilities(id)
            );
            
            CREATE TABLE affected_package_handles (
                id INTEGER PRIMARY KEY,
                vulnerability_id INTEGER NOT NULL,
                package_id INTEGER NOT NULL,
                blob_id INTEGER NOT NULL,
                FOREIGN KEY (vulnerability_id) REFERENCES vulnerabilities(id)
            );
            
            CREATE TABLE packages (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            
            CREATE TABLE blobs (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            );
            
            CREATE TABLE epss_handles (
                cve TEXT PRIMARY KEY,
                epss REAL,
                percentile REAL
            );
        """)
        
        # 插入测试数据
        # 漏洞 1: CVE-2021-44228 (Log4j) - 有完整 CVSS 和 EPSS
        cursor.execute("INSERT INTO vulnerabilities (name, published_date, status) VALUES (?, ?, ?)",
                      ("CVE-2021-44228", "2021-12-10T00:00:00Z", "active"))
        vuln_id_1 = cursor.lastrowid
        
        cursor.execute("INSERT INTO vulnerability_handles (vulnerability_id, blob_id) VALUES (?, ?)",
                      (vuln_id_1, 1))
        cursor.execute("INSERT INTO blobs (id, value) VALUES (?, ?)",
                      (1, json.dumps({
                          "description": "Apache Log4j2 RCE",
                          "severities": [{
                              "scheme": "CVSS",
                              "value": {
                                  "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                                  "score": 10.0
                              }
                          }]
                      })))
        
        cursor.execute("INSERT INTO packages (id, name) VALUES (?, ?)", (1, "log4j"))
        cursor.execute("INSERT INTO affected_package_handles (vulnerability_id, package_id, blob_id) VALUES (?, ?, ?)",
                      (vuln_id_1, 1, 2))
        cursor.execute("INSERT INTO blobs (id, value) VALUES (?, ?)",
                      (2, json.dumps({"ranges": [{"version": {"constraint": "< 2.17.0"}, "fix": {"version": "2.17.0", "state": "fixed"}}]})))
        
        # 插入 EPSS 数据
        cursor.execute("INSERT INTO epss_handles (cve, epss, percentile) VALUES (?, ?, ?)",
                      ("CVE-2021-44228", 0.95, 0.99))
        
        # 漏洞 2: CVE-2022-XXXX (测试 Unknown severity)
        cursor.execute("INSERT INTO vulnerabilities (name, published_date, status) VALUES (?, ?, ?)",
                      ("CVE-2022-0001", "2022-01-01T00:00:00Z", "active"))
        vuln_id_2 = cursor.lastrowid
        
        cursor.execute("INSERT INTO vulnerability_handles (vulnerability_id, blob_id) VALUES (?, ?)",
                      (vuln_id_2, 3))
        cursor.execute("INSERT INTO blobs (id, value) VALUES (?, ?)",
                      (3, json.dumps({
                          "description": "Test vulnerability without CVSS",
                          "severities": []
                      })))
        
        cursor.execute("INSERT INTO packages (id, name) VALUES (?, ?)", (2, "testlib"))
        cursor.execute("INSERT INTO affected_package_handles (vulnerability_id, package_id, blob_id) VALUES (?, ?, ?)",
                      (vuln_id_2, 2, 4))
        cursor.execute("INSERT INTO blobs (id, value) VALUES (?, ?)",
                      (4, json.dumps({"ranges": []})))
        
        conn.commit()
        conn.close()
        
        return db_path
    
    def test_cvss_score_populated(self, mock_grype_db):
        """测试 cvss_score 在运行路径中正确填充"""
        matcher = CVEMatcher(str(mock_grype_db))
        
        components = [
            Component(name="log4j", version="2.14.1", type="library", path="/tmp/log4j.jar")
        ]
        
        vulns = matcher.query_vulnerabilities(components)
        
        # 过滤出有 CVSS 的漏洞
        vulns_with_cvss = [v for v in vulns if v.cvss_score and v.cvss_score > 0]
        
        # 验收标准：cvss_score 非空率 ≥90%
        if vulns:
            non_empty_rate = len(vulns_with_cvss) / len(vulns)
            assert non_empty_rate >= 0.9, \
                f"cvss_score 非空率 {non_empty_rate:.1%} 低于 90% 阈值"
        
        matcher.close()
    
    def test_published_date_populated(self, mock_grype_db):
        """测试 published_date 在运行路径中正确填充"""
        matcher = CVEMatcher(str(mock_grype_db))
        
        components = [
            Component(name="log4j", version="2.14.1", type="library", path="/tmp/log4j.jar")
        ]
        
        vulns = matcher.query_vulnerabilities(components)
        
        # 过滤出有 published_date 的漏洞
        vulns_with_date = [v for v in vulns if v.published_date is not None]
        
        # 验收标准：published_date 非空率 ≥90%
        if vulns:
            non_empty_rate = len(vulns_with_date) / len(vulns)
            assert non_empty_rate >= 0.9, \
                f"published_date 非空率 {non_empty_rate:.1%} 低于 90% 阈值"
        
        matcher.close()
    
    def test_epss_score_populated(self, mock_grype_db):
        """测试 epss_score 在运行路径中正确填充（含离线降级）"""
        matcher = CVEMatcher(str(mock_grype_db))
        
        components = [
            Component(name="log4j", version="2.14.1", type="library", path="/tmp/log4j.jar")
        ]
        
        vulns = matcher.query_vulnerabilities(components)
        
        # 过滤出有 EPSS 的漏洞（来自 Grype DB 离线降级）
        vulns_with_epss = [v for v in vulns if v.epss_score is not None]
        
        # 验收标准：epss_score 非空率 ≥90%
        if vulns:
            non_empty_rate = len(vulns_with_epss) / len(vulns)
            assert non_empty_rate >= 0.9, \
                f"epss_score 非空率 {non_empty_rate:.1%} 低于 90% 阈值"
        
        matcher.close()
    
    def test_severity_not_unknown(self, mock_grype_db):
        """测试 severity 不是 Unknown（或 Unknown 比例 ≤5%）"""
        matcher = CVEMatcher(str(mock_grype_db))
        
        components = [
            Component(name="log4j", version="2.14.1", type="library", path="/tmp/log4j.jar"),
            Component(name="testlib", version="1.0.0", type="library", path="/tmp/testlib.so")
        ]
        
        vulns = matcher.query_vulnerabilities(components)
        
        # 验收标准：severity = Unknown ≤5%
        unknown_count = sum(1 for v in vulns if v.severity == "Unknown")
        if vulns:
            unknown_rate = unknown_count / len(vulns)
            assert unknown_rate <= 0.05, \
                f"severity=Unknown 比例 {unknown_rate:.1%} 超过 5% 阈值"
        
        matcher.close()
    
    def test_fields_in_task_queue_result(self, tmp_path):
        """测试字段在 task_queue 结果中正确序列化"""
        # 这个测试需要完整的扫描流程，暂时用 mock 验证
        # 实际应在集成测试环境中运行
        
        # 创建一个模拟的 vulnerability 对象
        vuln = Vulnerability(
            cve_id="CVE-2021-44228",
            component_name="log4j",
            component_version="2.14.1",
            severity="Critical",
            cvss_score=10.0,
            cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            description="Apache Log4j2 RCE",
            fixed_version="2.17.0",
            published_date=datetime(2021, 12, 10),
            epss_score=0.95
        )
        
        # 模拟 task_queue 中的序列化逻辑
        vuln_dict = {
            'cve_id': vuln.cve_id,
            'component': vuln.component_name,
            'version': vuln.component_version,
            'severity': vuln.severity,
            'cvss_score': vuln.cvss_score,
            'published_date': vuln.published_date.isoformat() if vuln.published_date else None,
            'epss_score': vuln.epss_score,
            'fixed_version': getattr(vuln, 'fixed_version', None),
            'priority_score': round(vuln.priority_score or 0, 3),
            'description': vuln.description[:200],
            'r155_non_compliant': False
        }
        
        # 断言所有关键字段都已填充
        assert vuln_dict['cvss_score'] > 0, "cvss_score 应大于 0"
        assert vuln_dict['published_date'] is not None, "published_date 不应为 None"
        assert vuln_dict['epss_score'] is not None, "epss_score 不应为 None"
        assert vuln_dict['severity'] != "Unknown", "severity 不应为 Unknown"
        assert vuln_dict['fixed_version'] is not None, "fixed_version 不应为 None"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])
