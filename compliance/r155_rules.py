#!/usr/bin/env python3
"""
UNECE R155 法规合规规则引擎

背景:
- UNECE R155 (Cybersecurity Management System, CSMS)
- 2021 年生效，强制要求汽车供应商建立网络安全管理体系
- 与 ISO/SAE 21434 协同使用

核心要求:
1. 风险评估和管理
2. 漏洞管理流程
3. 软件供应链管理
4. 安全更新机制
5. 事件响应能力
6. 持续监控和审计
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime, timedelta


class Severity(Enum):
    """严重程度级别"""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    UNKNOWN = "Unknown"


@dataclass
class ComplianceRule:
    """单条合规规则"""
    rule_id: str
    category: str
    requirement: str
    description: str
    severity_weight: float
    component_types: List[str] = field(default_factory=list)
    cvss_threshold: float = 7.0
    max_days_threshold: int = 180
    
    def is_violated(self, vuln_dict: dict) -> bool:
        """判断该 CVE 是否违反此规则"""
        if vuln_dict.get('cvss_score', 0) < self.cvss_threshold:
            return False
        
        severity = vuln_dict.get('severity', '').lower()
        if severity not in ['critical', 'high']:
            return False
        
        # 检查超时时间
        try:
            pub_date = datetime.fromisoformat(
                vuln_dict.get('published_date', 
                            vuln_dict.get('publish_date', '2020-01-01'))
                .replace('Z', '+00:00')
            )
            days_since_published = (datetime.now(pub_date.tzinfo) - pub_date).days
        except:
            days_since_published = 365
        
        if days_since_published > self.max_days_threshold:
            return True
        
        return False
    
    def calculate_penalty(self, vuln_dict: dict) -> float:
        """计算违规扣分"""
        cvss = vuln_dict.get('cvss_score', 0)
        base_penalty = self.severity_weight * cvss
        
        # 时间惩罚
        try:
            pub_date = datetime.fromisoformat(
                vuln_dict.get('published_date', '2020-01-01').replace('Z', '+00:00')
            )
            days_overdue = max(0, (datetime.now(pub_date.tzinfo) - pub_date).days - self.max_days_threshold)
        except:
            days_overdue = 180
        
        time_multiplier = 1 + (days_overdue / 365)
        
        # 严重度惩罚
        severity_mult = {
            'critical': 2.0,
            'high': 1.5,
            'medium': 1.0,
            'low': 0.5
        }
        sev_mult = severity_mult.get(vuln_dict.get('severity', '').lower(), 1.0)
        
        return base_penalty * time_multiplier * sev_mult


# R155 核心规则集
R155_RULES = [
    ComplianceRule(
        rule_id="CM.01",
        category="Supply Chain Security",
        requirement="软件供应链中的第三方组件必须经过安全评估",
        description="对开源组件、第三方库进行 SBOM 管理和漏洞扫描",
        severity_weight=1.0,
        cvss_threshold=7.0,
        max_days_threshold=90
    ),
    
    ComplianceRule(
        rule_id="CM.02", 
        category="Vulnerability Management",
        requirement="必须建立正式的漏洞识别、评估和修复流程",
        description="所有 High/Critical 级别 CVE 必须在 180 天内修复或缓解",
        severity_weight=1.5,
        cvss_threshold=7.0,
        max_days_threshold=180
    ),
    
    ComplianceRule(
        rule_id="SEC.01",
        category="Cryptographic Protection", 
        requirement="敏感数据必须使用经认证的加密算法保护",
        description="禁止使用弱加密算法（MD5, SHA-1, DES, RC4 等）",
        severity_weight=2.0,
        component_types=["Crypto Library"],
        cvss_threshold=6.5,
        max_days_threshold=120
    ),
    
    ComplianceRule(
        rule_id="AUTH.01",
        category="Authentication & Access Control",
        requirement="系统必须实施强身份认证机制",
        description="禁用硬编码凭证、默认密码、空口令",
        severity_weight=2.5,
        cvss_threshold=8.0,
        max_days_threshold=90
    ),
    
    ComplianceRule(
        rule_id="SEC.02",
        category="Secure Boot",
        requirement="必须实施安全启动验证",
        description="防止未经授权的固件被刷入设备",
        severity_weight=3.0,
        cvss_threshold=9.0,
        max_days_threshold=60
    ),
    
    ComplianceRule(
        rule_id="MON.01",
        category="Logging & Monitoring",
        requirement="关键安全事件必须记录并可审计",
        description="记录身份验证失败、配置变更、异常访问等事件",
        severity_weight=1.0,
        cvss_threshold=6.0,
        max_days_threshold=200
    ),
    
    ComplianceRule(
        rule_id="INT.01",
        category="Integrity Check",
        requirement="固件更新必须有签名和完整性校验",
        description="防止中间人攻击篡改升级包",
        severity_weight=2.5,
        cvss_threshold=8.5,
        max_days_threshold=90
    ),
]


@dataclass
class ComplianceViolation:
    """单次违规记录"""
    rule_id: str
    rule_category: str
    cve_id: str
    component: str
    penalty_score: float
    remediation_suggestion: str


@dataclass  
class ComplianceReport:
    """完整的合规报告"""
    firmware_id: str
    scan_date: str
    total_cves: int
    compliant_cves: int
    violating_cves: int
    compliance_score: float
    violations: List[ComplianceViolation]
    category_scores: Dict[str, float]
    recommendations: List[str]
    
    def to_dict(self) -> dict:
        return {
            'firmware_id': self.firmware_id,
            'scan_date': self.scan_date,
            'total_cves': self.total_cves,
            'compliant_cves': self.compliant_cves,
            'violating_cves': self.violating_cves,
            'compliance_score': round(self.compliance_score, 2),
            'violations': [
                {
                    'rule_id': v.rule_id,
                    'category': v.rule_category,
                    'cve_id': v.cve_id,
                    'component': v.component,
                    'penalty_score': round(v.penalty_score, 3),
                    'remediation': v.remediation_suggestion
                } for v in self.violations
            ],
            'category_scores': {k: round(v, 2) for k, v in self.category_scores.items()},
            'recommendations': self.recommendations
        }


class R155ComplianceChecker:
    """R155 合规检查器"""
    
    def __init__(self, rules: List[ComplianceRule] = None):
        self.rules = rules or R155_RULES
        self.rules_by_category = {}
        for rule in self.rules:
            if rule.category not in self.rules_by_category:
                self.rules_by_category[rule.category] = []
            self.rules_by_category[rule.category].append(rule)
    
    def check(self, vulnerabilities: List[dict]) -> ComplianceReport:
        """对一组 CVE 进行合规检查"""
        if not vulnerabilities:
            return self._empty_report()
        
        violations = []
        category_penalties = {cat: 0 for cat in self.rules_by_category.keys()}
        violated_cves = set()
        
        for vuln in vulnerabilities:
            for rule in self.rules:
                if rule.is_violated(vuln):
                    penalty = rule.calculate_penalty(vuln)
                    category_penalties[rule.category] += penalty
                    violated_cves.add(vuln['cve_id'])
                    
                    violation = ComplianceViolation(
                        rule_id=rule.rule_id,
                        rule_category=rule.category,
                        cve_id=vuln['cve_id'],
                        component=vuln.get('component', vuln.get('component_name', '')),
                        penalty_score=penalty,
                        remediation_suggestion=self._generate_remediation(vuln)
                    )
                    violations.append(violation)
        
        # 计算各类别得分
        category_scores = {}
        for category, penalties in category_penalties.items():
            max_for_category = len([r for r in self.rules if r.category == category]) * 10
            score = max(0, 100 - (penalties / max(max_for_category, 1) * 100))
            category_scores[category] = score
        
        # 计算总分
        total_max_penalty = len(self.rules) * 10
        actual_penalty = sum(category_penalties.values())
        compliance_score = max(0, 100 - (actual_penalty / max(total_max_penalty, 1) * 100))
        
        # 生成建议
        recommendations = self._generate_recommendations(violations, category_penalties)
        
        return ComplianceReport(
            firmware_id=vulnerabilities[0].get('firmware_id', 'unknown'),
            scan_date=datetime.now().isoformat(),
            total_cves=len(vulnerabilities),
            compliant_cves=len(vulnerabilities) - len(violated_cves),
            violating_cves=len(violated_cves),
            compliance_score=compliance_score,
            violations=violations,
            category_scores=category_scores,
            recommendations=recommendations
        )
    
    def _empty_report(self) -> ComplianceReport:
        """返回空报告的占位符"""
        return ComplianceReport(
            firmware_id='unknown',
            scan_date=datetime.now().isoformat(),
            total_cves=0,
            compliant_cves=0,
            violating_cves=0,
            compliance_score=100.0,
            violations=[],
            category_scores={cat: 100.0 for cat in self.rules_by_category.keys()},
            recommendations=["未发现安全风险，继续保持良好的安全实践"]
        )
    
    def _generate_remediation(self, vuln: dict) -> str:
        """生成修复建议"""
        fixed_version = vuln.get('fixed_version')
        suggestions = []
        
        if fixed_version:
            suggestions.append(f"升级到{fixed_version}或更高版本")
        else:
            suggestions.append("联系供应商获取安全补丁")
        
        severity = vuln.get('severity', '').lower()
        if severity == 'critical':
            suggestions.append("立即采取临时缓解措施（如网络隔离）")
        
        return "; ".join(suggestions)
    
    def _generate_recommendations(self, violations: List[ComplianceViolation], 
                                   category_penalties: Dict[str, float]) -> List[str]:
        """生成总体改进建议"""
        recommendations = []
        
        if not violations:
            return ["✅ 未发现 R155 合规问题"]
        
        sorted_categories = sorted(
            category_penalties.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        if sorted_categories and sorted_categories[0][1] > 10:
            top_category = sorted_categories[0][0]
            recommendations.append(f"🔴 优先处理'{top_category}'类别的问题")
        
        critical_count = len([v for v in violations if v.penalty_score > 5])
        if critical_count > 0:
            recommendations.append(f"⚠️ 发现{critical_count}个严重合规违规，需要紧急修复")
        
        # R155 特别提示
        if any(v.rule_id.startswith("SEC") for v in violations):
            recommendations.append("🔐 加强加密和安全启动机制")
        
        if any(v.rule_id.startswith("AUTH") for v in violations):
            recommendations.append("🔑 强化身份认证和访问控制")
        
        return recommendations[:5]


def check_r155_compliance(vulnerabilities: List[dict]) -> dict:
    """便捷函数：检查 R155 合规性"""
    checker = R155ComplianceChecker()
    report = checker.check(vulnerabilities)
    return report.to_dict()


if __name__ == "__main__":
    test_vulns = [
        {
            "cve_id": "CVE-2021-44228",
            "component": "Apache Log4j",
            "version": "2.14.1",
            "severity": "Critical",
            "cvss_score": 10.0,
            "published_date": "2021-12-10",
            "fixed_version": "2.17.0"
        },
        {
            "cve_id": "CVE-2022-0778", 
            "component": "OpenSSL",
            "version": "1.1.1k",
            "severity": "High",
            "cvss_score": 7.5,
            "published_date": "2022-03-15",
            "fixed_version": "1.1.1n"
        }
    ]
    
    result = check_r155_compliance(test_vulns)
    print(f"\n📊 合规评分：{result['compliance_score']}/100")
    print(f"违规 CVE 数：{result['violating_cves']}")
    print("\n💡 建议:")
    for rec in result['recommendations']:
        print(f"  {rec}")
