#!/usr/bin/env python3
"""
EU R155/R156 法规合规检查引擎

参考文献:
- UNECE R155: Cybersecurity and Cybersecurity Management System (CSMS)
- UNECE R156: Software Update and Software Update Management System (SUMS)
- ISO/SAE 21434: Road vehicles – Cybersecurity engineering

模块功能:
1. 解析法规条款到可执行的规则
2. 评估固件/组件的合规性
3. 计算合规得分（0-100 分）
4. 生成合规差距分析报告
"""

import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComplianceLevel(Enum):
    """合规等级"""
    NONE = 0           # 完全不合规
    PARTIAL = 1        # 部分合规
    MOSTLY = 2         # 基本合规
    FULL = 3           # 完全合规
    EXCEEDS = 4        # 超出要求


@dataclass
class RegulationClause:
    """法规条款"""
    clause_id: str  # 如 "R155-A.1"
    title: str      # 如 "策略与流程"
    category: str   # 如 "Governance", "Development", "Operations"
    description: str
    priority: str   # "Mandatory"/"Recommended"/"Optional"
    evidence_type: List[str]  # ["CVE_Database", "Build_System", "Code_Review"]
    
    def __str__(self):
        return f"{self.clause_id}: {self.title}"


@dataclass
class ComplianceEvidence:
    """合规证据"""
    evidence_id: str
    clause_id: str
    status: str  # "Compliant"/"Non-Compliant"/"Partial"/"Not_Applicable"
    description: str
    severity: str  # "Critical"/"High"/"Medium"/"Low"
    risk_score: float = 0.0  # 0-1 之间的风险分数
    
    def to_dict(self):
        return {
            'evidence_id': self.evidence_id,
            'clause_id': self.clause_id,
            'status': self.status,
            'description': self.description,
            'severity': self.severity,
            'risk_score': round(self.risk_score, 3)
        }


@dataclass
class ComplianceScore:
    """合规评分结果"""
    firmware_id: str
    firmware_name: str
    scan_time: str
    overall_score: float  # 0-100
    compliance_level: ComplianceLevel
    domain_scores: Dict[str, float]  # 各域得分
    total_evidence_count: int
    compliant_count: int
    non_compliant_count: int
    partial_count: int
    critical_vulnerabilities: int
    high_risk_items: List[Dict]
    remediation_recommendations: List[str]
    evidence_details: List[Dict]
    
    def to_dict(self):
        return {
            'firmware_id': self.firmware_id,
            'firmware_name': self.firmware_name,
            'scan_time': self.scan_time,
            'overall_score': round(self.overall_score, 2),
            'compliance_level': self.compliance_level.value,
            'compliance_level_text': self._get_level_text(),
            'domain_scores': self.domain_scores,
            'statistics': {
                'total_evidence': self.total_evidence_count,
                'compliant': self.compliant_count,
                'non_compliant': self.non_compliant_count,
                'partial': self.partial_count,
                'critical_vulns': self.critical_vulnerabilities
            },
            'high_risk_items': self.high_risk_items,
            'remediation_recommendations': self.remediation_recommendations,
            'evidence_details': self.evidence_details
        }
    
    def _get_level_text(self) -> str:
        texts = {
            0: "不合规",
            1: "部分合规",
            2: "基本合规", 
            3: "完全合规",
            4: "超出要求"
        }
        return texts.get(self.compliance_level.value, "未知")


class R155RegulationKnowledgeBase:
    """R155 法规知识库"""
    
    # R155 Annex 的 A 类（强制性）要求
    R155_A_CLAUSES = [
        # Governance & Policy Domain (A.1 - A.3)
        RegulationClause(
            clause_id="R155-A.1",
            title="网络安全策略与流程",
            category="Governance",
            description="制造商应建立并维护一个网络安全策略，定义组织级目标、角色和职责。",
            priority="Mandatory",
            evidence_type=["Policy_Document", "Org_Structure"]
        ),
        RegulationClause(
            clause_id="R155-A.2",
            title="网络安全管理系统（CSMS）",
            category="Governance", 
            description="应建立认证的 CSMS，包括政策、程序和控制措施。",
            priority="Mandatory",
            evidence_type=["CSMS_Certificate", "Audit_Report"]
        ),
        
        # Risk Assessment Domain (A.3 - A.5)
        RegulationClause(
            clause_id="R155-A.3",
            title="威胁分析与风险评估（TARA）",
            category="Risk_Assessment",
            description="对车辆系统进行定期的 TARA，识别潜在威胁并制定缓解措施。",
            priority="Mandatory",
            evidence_type=["TARA_Report", "Threat_Model"]
        ),
        RegulationClause(
            clause_id="R155-A.4",
            title="供应链安全",
            category="Supply_Chain",
            description="确保供应商和供应链中的网络安全要求得到满足。",
            priority="Mandatory",
            evidence_type=["Supplier_Assessment", "SBOM"]
        ),
        RegulationClause(
            clause_id="R155-A.5",
            title="组件安全验证",
            category="Vulnerability_Management",
            description="所有组件应在发布前进行安全测试和漏洞扫描。",
            priority="Mandatory",
            evidence_type=["Security_Test_Report", "Vulnerability_Scan"]
        ),
        
        # Development Security Domain (B.1 - B.5)
        RegulationClause(
            clause_id="R155-B.1",
            title="安全编码实践",
            category="Secure_Development",
            description="遵循安全编码指南，防止常见漏洞（OWASP TOP 10）。",
            priority="Mandatory",
            evidence_type=["Static_Analysis", "Code_Review"]
        ),
        RegulationClause(
            clause_id="R155-B.2",
            title="加密机制",
            category="Cryptographic_Protection",
            description="使用经批准的加密算法保护数据和通信。",
            priority="Mandatory",
            evidence_type=["Crypto_Provider_List", "Key_Management"]
        ),
        RegulationClause(
            clause_id="R155-B.3",
            title="认证与授权",
            category="Access_Control",
            description="实施强认证机制和最小权限原则。",
            priority="Mandatory",
            evidence_type=["Auth_Design", "Access_Logs"]
        ),
        
        # Operations & Monitoring Domain (C.1 - C.5)
        RegulationClause(
            clause_id="R155-C.1",
            title="安全监控与检测",
            category="Monitoring",
            description="持续监控系统以检测网络安全事件。",
            priority="Mandatory",
            evidence_type=["IDS_Configuration", "SIEM_Integration"]
        ),
        RegulationClause(
            clause_id="R155-C.2",
            title="事件响应",
            category="Incident_Response",
            description="建立快速响应和处理安全事件的流程。",
            priority="Mandatory",
            evidence_type=["IR_Playbook", "Drill_Records"]
        ),
        RegulationClause(
            clause_id="R155-C.3",
            title="漏洞披露政策",
            category="Vulnerability_Management",
            description="接受并处理外部研究人员提交的漏洞报告。",
            priority="Mandatory",
            evidence_type=["Bug_Bounty_Program", "Disclosure_Policy"]
        ),
        
        # Updates & Patches Domain (D.1 - D.3)
        RegulationClause(
            clause_id="R155-D.1",
            title="软件更新管理",
            category="Software_Update",
            description="建立安全的软件更新机制，确保更新完整性和真实性。",
            priority="Mandatory",
            evidence_type=["OTA_Mechanism", "Update_Signing"]
        ),
        RegulationClause(
            clause_id="R155-D.2",
            title="补丁及时性",
            category="Vulnerability_Management",
            description="在已知 CVE 公开后 180 天内修复高危漏洞。",
            priority="Mandatory",
            evidence_type=["Patch_Timeline", "CVE_History"]
        ),
        RegulationClause(
            clause_id="R155-D.3",
            title="向后兼容性",
            category="Software_Update",
            description="软件更新不应引入新的安全风险或破坏现有功能。",
            priority="Recommended",
            evidence_type=["Regression_Test", "Compatibility_Report"]
        ),
    ]
    
    # R155-B 类（建议性）要求
    R155_B_CLAUSES = [
        RegulationClause(
            clause_id="R155-B.1",
            title="红队演练",
            category="Penetration_Testing",
            description="定期进行红队攻击演练，模拟真实攻击者。",
            priority="Recommended",
            evidence_type=["RedTeaming_Report"]
        ),
        RegulationClause(
            clause_id="R155-B.2",
            title="员工安全意识培训",
            category="Human_Factors",
            description="定期为员工提供网络安全意识和技能培训。",
            priority="Recommended",
            evidence_type=["Training_Records", "Assessment_Scores"]
        ),
        RegulationClause(
            clause_id="R155-B.3",
            title="第三方渗透测试",
            category="Penetration_Testing",
            description="聘请独立的第三方进行渗透测试。",
            priority="Recommended",
            evidence_type=["ThirdParty_Pentest_Report"]
        ),
    ]
    
    def __init__(self):
        self.all_clauses = self.R155_A_CLAUSES + self.R155_B_CLAUSES
        self.clause_map = {c.clause_id: c for c in self.all_clauses}
        self.category_map = self._build_category_map()
        
        logger.info(f"R155 知识库已加载 {len(self.all_clauses)} 条条款")
    
    def _build_category_map(self) -> Dict[str, List[RegulationClause]]:
        """按类别组织条款"""
        categories = {}
        for clause in self.all_clauses:
            if clause.category not in categories:
                categories[clause.category] = []
            categories[clause.category].append(clause)
        return categories
    
    def get_clause(self, clause_id: str) -> Optional[RegulationClause]:
        """获取单个条款"""
        return self.clause_map.get(clause_id)
    
    def get_by_category(self, category: str) -> List[RegulationClause]:
        """获取某类别的所有条款"""
        return self.category_map.get(category, [])
    
    def get_mandatory_clauses(self) -> List[RegulationClause]:
        """获取所有强制性条款"""
        return [c for c in self.all_clauses if c.priority == "Mandatory"]
    
    def get_required_clause_count(self) -> int:
        """返回需要检查的条款总数"""
        return len(self.R155_A_CLAUSES)  # A 类为必须项


class R155ComplianceChecker:
    """R155 合规检查器"""
    
    # R155 权重配置
    WEIGHTS = {
        # 域权重（影响总分计算）
        'domains': {
            'Governance': 1.0,
            'Risk_Assessment': 1.0,
            'Supply_Chain': 0.9,
            'Vulnerability_Management': 1.2,  # 最高权重
            'Secure_Development': 1.0,
            'Cryptographic_Protection': 1.0,
            'Access_Control': 1.0,
            'Monitoring': 1.0,
            'Incident_Response': 1.0,
            'Software_Update': 1.0,
            'Penetration_Testing': 0.5,
            'Human_Factors': 0.5
        },
        # 漏洞严重程度惩罚系数
        'vulnerability_penalty': {
            'Critical': 15,  # 每发现 1 个扣 15 分
            'High': 10,       # 每发现 1 个扣 10 分
            'Medium': 5,
            'Low': 2
        },
        # R155 合规阈值
        'r155_threshold': 70,  # >=70 分为合规
        'days_threshold': 180  # 180 天内必须修复高危漏洞
    }
    
    def __init__(self, knowledge_base: R155RegulationKnowledgeBase):
        self.kb = knowledge_base
    
    def check_compliance(
        self,
        firmware_id: str,
        firmware_name: str,
        components: List[Dict],
        vulnerabilities: List[Dict],
        scan_time: str
    ) -> ComplianceScore:
        """
        执行完整的合规检查
        
        Args:
            firmware_id: 固件 ID
            firmware_name: 固件文件名
            components: 识别出的组件列表
            vulnerabilities: CVE 漏洞列表
            scan_time: 扫描时间
            
        Returns:
            ComplianceScore: 合规评分结果
        """
        
        evidence_list = []
        domain_scores = {}
        
        # ========== 步骤 1: 基于 CVE 的证据评估 ==========
        evidence_list.extend(
            self._evaluate_cve_evidence(vulnerabilities)
        )
        
        # ========== 步骤 2: 基于组件的证据评估 ==========
        evidence_list.extend(
            self._evaluate_component_evidence(components)
        )
        
        # ========== 步骤 3: 按领域聚合得分 ==========
        for category, clauses in self.kb.category_map.items():
            domain_evidence = [e for e in evidence_list if any(e.clause_id == c.clause_id for c in clauses)]
            
            if domain_evidence:
                score = self._calculate_domain_score(domain_evidence, clauses)
            else:
                # 无证据时默认扣分（视为不合规）
                score = self.WEIGHTS['domains'].get(category, 0.5) * 50
            
            domain_scores[category] = min(score, 100)
        
        # ========== 步骤 4: 计算总体得分 ==========
        base_score = self._calculate_overall_score(domain_scores)
        penalty = self._calculate_vulnerability_penalty(vulnerabilities)
        final_score = max(base_score - penalty, 0)
        
        # ========== 步骤 5: 确定合规等级 ==========
        compliance_level = self._determine_compliance_level(final_score, len(vulnerabilities))
        
        # ========== 步骤 6: 收集高风险项目 ==========
        high_risk_items = self._identify_high_risk_items(vulnerabilities, evidence_list)
        
        # ========== 步骤 7: 生成修复建议 ==========
        recommendations = self._generate_recommendations(vulnerabilities, evidence_list, compliance_level)
        
        # 统计信息
        compliant_count = sum(1 for e in evidence_list if e['status'] == 'Compliant')
        non_compliant_count = sum(1 for e in evidence_list if e['status'] == 'Non-Compliant')
        partial_count = sum(1 for e in evidence_list if e['status'] == 'Partial')
        critical_count = sum(1 for v in vulnerabilities if v.get('severity', '').lower() == 'critical')
        
        return ComplianceScore(
            firmware_id=firmware_id,
            firmware_name=firmware_name,
            scan_time=scan_time,
            overall_score=final_score,
            compliance_level=compliance_level,
            domain_scores=domain_scores,
            total_evidence_count=len(evidence_list),
            compliant_count=compliant_count,
            non_compliant_count=non_compliant_count,
            partial_count=partial_count,
            critical_vulnerabilities=critical_count,
            high_risk_items=high_risk_items,
            remediation_recommendations=recommendations,
            evidence_details=[e.to_dict() if hasattr(e, 'to_dict') else e for e in evidence_list]
        )
    
    def _evaluate_cve_evidence(self, vulnerabilities: List[Dict]) -> List[ComplianceEvidence]:
        """基于 CVE 漏洞生成合规证据"""
        evidence = []
        
        # 检查 R155-D.2 补丁及时性
        patch_deadline_reached = False
        overdue_vulns = []
        
        for vuln in vulnerabilities:
            cve_id = vuln.get('cve_id', '')
            severity = vuln.get('severity', '').upper()
            r155_non_compliant = vuln.get('r155_non_compliant', False)
            
            # 严重漏洞证据
            if severity in ['CRITICAL', 'HIGH']:
                evidence.append(ComplianceEvidence(
                    evidence_id=f"EVID-{cve_id}-CVE",
                    clause_id="R155-A.5",  # 组件安全验证
                    status="Non-Compliant",
                    description=f"发现{severity}级别 CVE: {cve_id}",
                    severity=severity,
                    risk_score=1.0 if severity == 'CRITICAL' else 0.8
                ))
                
                # 检查是否超过 180 天期限
                if r155_non_compliant:
                    overdue_vulns.append(cve_id)
                    patch_deadline_reached = True
        
        # 如果存在超期未修复的高危 CVE，违反 R155-D.2
        if patch_deadline_reached:
            evidence.append(ComplianceEvidence(
                evidence_id="EVID-D.2-PATCH-TIMELINE",
                clause_id="R155-D.2",
                status="Non-Compliant",
                description=f"以下 CVE 超过 180 天未修复：{', '.join(overdue_vulns[:5])}",
                severity="Critical",
                risk_score=0.95
            ))
        
        return evidence
    
    def _evaluate_component_evidence(self, components: List[Dict]) -> List[ComplianceEvidence]:
        """基于组件生成合规证据"""
        evidence = []
        
        # 检查是否有已知安全组件（如 wolfSSL, mbedTLS）
        secure_components = set()
        unsafe_patterns = {'telnet', 'ftpd', 'httpd', 'busybox'}
        
        for comp in components:
            # 兼容 dict 和 Component dataclass
            if isinstance(comp, dict):
                name = comp.get('name', '').lower()
            else:
                name = getattr(comp, 'name', '').lower()
            
            # 加密组件正面证据
            if any(safe in name for safe in ['openssl', 'wolfssl', 'mbedtls', 'crypto']):
                secure_components.add(name)
            
            # 不安全模式负面证据
            for pattern in unsafe_patterns:
                if pattern in name:
                    comp_name = comp.get('name', '') if isinstance(comp, dict) else getattr(comp, 'name', '')
                    evidence.append(ComplianceEvidence(
                        evidence_id=f"EVID-{pattern}-COMPONENT",
                        clause_id="R155-B.2",  # 加密机制
                        status="Partial",
                        description=f"发现潜在不安全组件：{comp_name}",
                        severity="Medium",
                        risk_score=0.5
                    ))
        
        # 如果有加密库，添加正面证据
        if secure_components:
            evidence.append(ComplianceEvidence(
                evidence_id="EVID-B.2-CRYPTO",
                clause_id="R155-B.2",
                status="Compliant",
                description=f"检测到加密库：{', '.join(list(secure_components)[:3])}",
                severity="Low",
                risk_score=-0.1  # 加分项
            ))
        
        return evidence
    
    def _calculate_domain_score(self, evidence_list: List, clauses: List[RegulationClause]) -> float:
        """计算某一领域的得分"""
        if not evidence_list:
            return 50.0
        
        weights = self.WEIGHTS['domains'].get(clauses[0].category, 1.0)
        
        scores = []
        for ev in evidence_list:
            status = ev['status'] if isinstance(ev, dict) else ev.status
            
            if status == 'Compliant':
                scores.append(100)
            elif status == 'Partial':
                scores.append(60)
            else:  # Non-Compliant
                scores.append(30)
        
        return (sum(scores) / len(scores)) * weights
    
    def _calculate_overall_score(self, domain_scores: Dict[str, float]) -> float:
        """计算整体得分（加权平均）"""
        total_weight = 0
        weighted_sum = 0
        
        for domain, score in domain_scores.items():
            weight = self.WEIGHTS['domains'].get(domain, 1.0)
            weighted_sum += score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 50.0
    
    def _calculate_vulnerability_penalty(self, vulnerabilities: List[Dict]) -> float:
        """计算漏洞惩罚分数"""
        penalty = 0
        
        for vuln in vulnerabilities:
            severity = vuln.get('severity', '').upper()
            penalty += self.WEIGHTS['vulnerability_penalty'].get(severity, 2)
        
        return penalty
    
    def _determine_compliance_level(self, score: float, critical_vulns: int) -> ComplianceLevel:
        """根据分数确定合规等级"""
        if critical_vulns > 0 or score < 50:
            return ComplianceLevel.NONE
        elif score < self.WEIGHTS['r155_threshold']:
            return ComplianceLevel.PARTIAL
        elif score < 85:
            return ComplianceLevel.MOSTLY
        elif score < 95:
            return ComplianceLevel.FULL
        else:
            return ComplianceLevel.EXCEEDS
    
    def _identify_high_risk_items(self, vulnerabilities: List[Dict], evidence_list: List) -> List[Dict]:
        """识别高风险项"""
        high_risk = []
        
        # 添加高危 CVE
        for vuln in vulnerabilities:
            if vuln.get('severity', '').upper() in ['CRITICAL', 'HIGH']:
                high_risk.append({
                    'type': 'CVE',
                    'id': vuln.get('cve_id'),
                    'severity': vuln.get('severity'),
                    'description': vuln.get('description', '')[:200]
                })
        
        # 添加不合规证据
        for ev in evidence_list:
            status = ev['status'] if isinstance(ev, dict) else ev.status
            if status == 'Non-Compliant':
                high_risk.append({
                    'type': 'COMPLIANCE_GAP',
                    'id': ev.get('clause_id') if isinstance(ev, dict) else ev.clause_id,
                    'severity': ev.get('severity') if isinstance(ev, dict) else ev.severity,
                    'description': ev.get('description') if isinstance(ev, dict) else ev.description
                })
        
        return sorted(high_risk, key=lambda x: 4 if x['severity'] == 'Critical' else 3 if x['severity'] == 'High' else 2 if x['severity'] == 'Medium' else 1, reverse=True)
    
    def _generate_recommendations(self, vulnerabilities: List[Dict], evidence_list: List, level: ComplianceLevel) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        # 基于漏洞的建议
        critical_vulns = [v for v in vulnerabilities if v.get('severity', '').upper() == 'CRITICAL']
        if critical_vulns:
            recommendations.append(f"🔴 立即修复 {len(critical_vulns)} 个严重 CVE（优先级：P0）")
        
        high_vulns = [v for v in vulnerabilities if v.get('severity', '').upper() == 'HIGH']
        if high_vulns:
            recommendations.append(f"🟠 在 30 天内修复 {len(high_vulns)} 个高危 CVE（优先级：P1）")
        
        # 基于合规差距的建议
        for ev in evidence_list:
            status = ev['status'] if isinstance(ev, dict) else ev.status
            if status == 'Non-Compliant':
                clause_id = ev.get('clause_id') if isinstance(ev, dict) else ev.clause_id
                if 'D.2' in clause_id:
                    recommendations.append("⚠️ 更新补丁策略，确保高危漏洞在 180 天内修复")
                elif 'A.5' in clause_id:
                    recommendations.append("⚠️ 增加固件扫描频率，发布前必须进行安全测试")
                elif 'B.2' in clause_id:
                    recommendations.append("⚠️ 审查加密机制，优先使用业界标准库（OpenSSL/mbedTLS）")
        
        # 通用建议
        if level in [ComplianceLevel.NONE, ComplianceLevel.PARTIAL]:
            recommendations.append("💡 建议建立正式的 CSMS 体系并获得认证")
            recommendations.append("💡 开展 TARA 分析，识别关键风险点")
        
        return recommendations


# 全局实例
_r155_checker: Optional[R155ComplianceChecker] = None

def get_r155_checker() -> R155ComplianceChecker:
    """获取全局 R155 检查器实例"""
    global _r155_checker
    
    if _r155_checker is None:
        kb = R155RegulationKnowledgeBase()
        _r155_checker = R155ComplianceChecker(kb)
    
    return _r155_checker


# 便捷函数
def evaluate_firmware_compliance(
    firmware_id: str,
    firmware_name: str,
    components: List[Dict],
    vulnerabilities: List[Dict],
    scan_time: str = None
) -> Dict:
    """快速评估固件 R155 合规性"""
    checker = get_r155_checker()
    
    result = checker.check_compliance(
        firmware_id=firmware_id,
        firmware_name=firmware_name,
        components=components,
        vulnerabilities=vulnerabilities,
        scan_time=scan_time or datetime.now().isoformat()
    )
    
    return result.to_dict()


if __name__ == "__main__":
    # 测试运行
    print("=" * 60)
    print("R155 合规检查引擎测试")
    print("=" * 60)
    
    # 创建测试数据
    test_vulns = [
        {'cve_id': 'CVE-2023-1234', 'severity': 'Critical', 'r155_non_compliant': True},
        {'cve_id': 'CVE-2023-5678', 'severity': 'High', 'r155_non_compliant': False},
        {'cve_id': 'CVE-2023-9012', 'severity': 'Medium', 'r155_non_compliant': False}
    ]
    
    test_components = [
        {'name': 'wolfSSL-4.5.0', 'version': '4.5.0'},
        {'name': 'BusyBox-1.35', 'version': '1.35'}
    ]
    
    # 执行检查
    result = evaluate_firmware_compliance(
        firmware_id='TEST-FW-001',
        firmware_name='test_firmware.bin',
        components=test_components,
        vulnerabilities=test_vulns
    )
    
    print("\n📊 合规评分结果:")
    print(f"  总体得分：{result['overall_score']:.2f}/100")
    print(f"  合规等级：{result['compliance_level_text']}")
    print(f"  总证据数：{result['statistics']['total_evidence']}")
    print(f"  ✓ 合规项：{result['statistics']['compliant']}")
    print(f"  ✗ 不合规项：{result['statistics']['non_compliant']}")
    print(f"  ⚠ 部分合规：{result['statistics']['partial']}")
    
    print("\n🔐 域名得分:")
    for domain, score in result['domain_scores'].items():
        bar = '█' * int(score / 10) + '░' * (10 - int(score / 10))
        print(f"  {domain:25} [{bar}] {score:.1f}")
    
    print("\n📋 高风险项目:")
    for item in result['high_risk_items'][:5]:
        print(f"  • {item['type']}: {item['id']} ({item['severity']})")
    
    print("\n✅ 修复建议:")
    for rec in result['remediation_recommendations'][:5]:
        print(f"  {rec}")
    
    print("\n" + "=" * 60)
