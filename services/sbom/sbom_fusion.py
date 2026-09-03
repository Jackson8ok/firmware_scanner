"""
SBOM 融合引擎 - v2.7.0-Phase4

实现 SBOM 与二进制指纹的深度融合架构:
1. 双源输入（固件 + SBOM）
2. 证据强度分级（A/B/C 类）
3. CVE 统计加权
4. 向后兼容

使用方式:
    from services.sbom.sbom_fusion import SBOMFusionEngine
    
    engine = SBOMFusionEngine()
    components = engine.fuse(sbom_components, fingerprint_components)
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EvidenceLevel(Enum):
    """证据强度级别"""
    A = "confirmed"      # A 类：指纹确认版本（高置信度）
    B = "sbom_declared"  # B 类：SBOM 声明（中置信度）
    C = "unknown"        # C 类：版本未知（低置信度）


@dataclass
class FusedComponent:
    """融合后的组件"""
    name: str
    version: str
    type: str
    path: str
    cpe: Optional[str] = None
    evidence_level: str = "A"  # A/B/C
    evidence_sources: List[str] = None  # ['fingerprint', 'sbom']
    confidence: str = "high"  # high/medium/low
    version_note: Optional[str] = None
    evidence: List[str] = None
    sbom_version: Optional[str] = None
    fingerprint_version: Optional[str] = None
    
    def __post_init__(self):
        if self.evidence_sources is None:
            self.evidence_sources = []
        if self.evidence is None:
            self.evidence = []
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def get_cve_weight(self) -> float:
        """获取 CVE 统计权重"""
        weights = {
            "A": 1.0,   # A 类：100%
            "B": 0.5,   # B 类：50%
            "C": 0.25   # C 类：25%
        }
        return weights.get(self.evidence_level, 0.5)


class SBOMFusionEngine:
    """SBOM 融合引擎"""
    
    def __init__(self):
        self.fused_components: List[FusedComponent] = []
        self.warnings: List[Dict] = []
    
    def fuse(self, sbom_components: List[Dict], fingerprint_components: List[Dict]) -> List[FusedComponent]:
        """
        融合 SBOM 和指纹组件
        
        Args:
            sbom_components: SBOM 组件列表（字典格式）
            fingerprint_components: 指纹组件列表（字典格式）
        
        Returns:
            融合后的组件列表
        """
        logger.info(f"SBOM 融合引擎启动：{len(sbom_components)} SBOM 组件，{len(fingerprint_components)} 指纹组件")
        
        # 标准化名称映射
        def normalize_name(name: str) -> str:
            return name.lower().replace('-', '').replace('_', '').replace(' ', '')
        
        # 创建索引
        sbom_index = {normalize_name(c.get('name', '')): c for c in sbom_components}
        fp_index = {normalize_name(c.get('name', '')): c for c in fingerprint_components}
        
        self.fused_components = []
        self.warnings = []
        
        # 融合逻辑
        all_names = set(sbom_index.keys()) | set(fp_index.keys())
        
        for norm_name in all_names:
            sbom_comp = sbom_index.get(norm_name)
            fp_comp = fp_index.get(norm_name)
            
            if sbom_comp and fp_comp:
                # 双方都有 → A 类或 B 类
                fused = self._fuse_both_present(sbom_comp, fp_comp)
            elif fp_comp:
                # 仅有指纹 → C 类
                fused = self._fuse_fingerprint_only(fp_comp)
            else:
                # 仅有 SBOM → B 类
                fused = self._fuse_sbom_only(sbom_comp)
            
            if fused:
                self.fused_components.append(fused)
        
        # 生成告警
        self._generate_warnings()
        
        logger.info(f"SBOM 融合完成：{len(self.fused_components)} 个融合组件")
        return self.fused_components
    
    def _fuse_both_present(self, sbom_comp: Dict, fp_comp: Dict) -> Optional[FusedComponent]:
        """双方都存在的融合逻辑"""
        name = sbom_comp.get('name', fp_comp.get('name'))
        sbom_version = sbom_comp.get('version', 'unknown')
        fp_version = fp_comp.get('version', 'unknown')
        fp_confidence = fp_comp.get('confidence', 'high')
        
        # 证据强度判定
        if fp_version != 'unknown' and fp_version == sbom_version:
            # 版本一致且已知 → A 类
            evidence_level = "A"
            final_version = fp_version
            version_note = None
            logger.debug(f"✅ {name}: A 类（指纹确认，版本={final_version}）")
        elif fp_version == 'unknown':
            # 指纹版本未知 → C 类（以指纹为准，但标记为未知）
            evidence_level = "C"
            final_version = 'unknown'
            version_note = fp_comp.get('version_note', '版本未知（需厂商提供）')
            logger.debug(f"❓ {name}: C 类（指纹版本未知）")
        else:
            # 版本不一致 → B 类（以 SBOM 为准，标记为不一致）
            evidence_level = "B"
            final_version = sbom_version
            version_note = f"版本不一致（SBOM: {sbom_version}, 指纹：{fp_version}）"
            logger.warning(f"⚠️  {name}: B 类（版本不一致：SBOM={sbom_version}, 指纹={fp_version}）")
        
        return FusedComponent(
            name=name,
            version=final_version,
            type=sbom_comp.get('type', fp_comp.get('type', 'unknown')),
            path=fp_comp.get('path', ''),
            cpe=sbom_comp.get('cpe') or fp_comp.get('cpe'),
            evidence_level=evidence_level,
            evidence_sources=['sbom', 'fingerprint'],
            confidence=fp_confidence,
            version_note=version_note,
            evidence=fp_comp.get('evidence', []),
            sbom_version=sbom_version,
            fingerprint_version=fp_version
        )
    
    def _fuse_fingerprint_only(self, fp_comp: Dict) -> FusedComponent:
        """仅有指纹的融合逻辑"""
        name = fp_comp.get('name')
        version = fp_comp.get('version', 'unknown')
        confidence = fp_comp.get('confidence', 'high')
        
        if version != 'unknown':
            # 指纹版本已知 → C 类（但实际应归为 A 类，这里保持 C 类表示无 SBOM 确认）
            evidence_level = "C"
            version_note = None
            logger.debug(f"🔍 {name}: C 类（仅指纹，版本={version}）")
        else:
            # 指纹版本未知 → C 类
            evidence_level = "C"
            version_note = fp_comp.get('version_note', '版本未知')
            logger.debug(f"❓ {name}: C 类（仅指纹，版本未知）")
        
        return FusedComponent(
            name=name,
            version=version,
            type=fp_comp.get('type', 'unknown'),
            path=fp_comp.get('path', ''),
            cpe=fp_comp.get('cpe'),
            evidence_level=evidence_level,
            evidence_sources=['fingerprint'],
            confidence=confidence,
            version_note=version_note,
            evidence=fp_comp.get('evidence', []),
            fingerprint_version=version
        )
    
    def _fuse_sbom_only(self, sbom_comp: Dict) -> FusedComponent:
        """仅有 SBOM 的融合逻辑"""
        name = sbom_comp.get('name')
        version = sbom_comp.get('version', 'unknown')
        
        # B 类（SBOM 声明但指纹未命中）
        evidence_level = "B"
        version_note = "SBOM 声明，二进制未检测到（可能符号裁剪）"
        logger.warning(f"⚠️  {name}: B 类（仅 SBOM 声明，二进制未检测到）")
        
        return FusedComponent(
            name=name,
            version=version,
            type=sbom_comp.get('type', 'unknown'),
            path='',
            cpe=sbom_comp.get('cpe'),
            evidence_level=evidence_level,
            evidence_sources=['sbom'],
            confidence='medium',
            version_note=version_note,
            sbom_version=version
        )
    
    def _generate_warnings(self):
        """生成告警"""
        a_count = sum(1 for c in self.fused_components if c.evidence_level == "A")
        b_count = sum(1 for c in self.fused_components if c.evidence_level == "B")
        c_count = sum(1 for c in self.fused_components if c.evidence_level == "C")
        
        if b_count > 0:
            b_components = [c.name for c in self.fused_components if c.evidence_level == "B"]
            self.warnings.append({
                "type": "sbom_fingerprint_mismatch",
                "count": b_count,
                "components": b_components,
                "message": f"{b_count} 个组件 SBOM 与指纹不一致",
                "suggestion": "请核实 SBOM 准确性或检查二进制是否符号裁剪"
            })
        
        if c_count > 0:
            c_components = [c.name for c in self.fused_components if c.evidence_level == "C"]
            self.warnings.append({
                "type": "fingerprint_only_or_unknown",
                "count": c_count,
                "components": c_components,
                "message": f"{c_count} 个组件仅有指纹识别或版本未知",
                "suggestion": "建议在 SBOM 中补充这些组件"
            })
        
        logger.info(f"生成 {len(self.warnings)} 条告警")
    
    def get_fusion_summary(self) -> Dict:
        """获取融合摘要"""
        a_count = sum(1 for c in self.fused_components if c.evidence_level == "A")
        b_count = sum(1 for c in self.fused_components if c.evidence_level == "B")
        c_count = sum(1 for c in self.fused_components if c.evidence_level == "C")
        
        return {
            "total_components": len(self.fused_components),
            "evidence_levels": {
                "A": a_count,
                "B": b_count,
                "C": c_count
            },
            "warnings_count": len(self.warnings)
        }
    
    def calculate_weighted_cve_count(self, vulnerabilities: List[Dict]) -> Dict:
        """
        计算加权 CVE 数量
        
        Args:
            vulnerabilities: 漏洞列表（每个漏洞应包含 component_evidence_level 字段）
        
        Returns:
            加权统计结果
        """
        total_raw = len(vulnerabilities)
        total_weighted = 0.0
        
        by_severity = {
            "Critical": {"raw": 0, "weighted": 0.0},
            "High": {"raw": 0, "weighted": 0.0},
            "Medium": {"raw": 0, "weighted": 0.0},
            "Low": {"raw": 0, "weighted": 0.0}
        }
        
        for vuln in vulnerabilities:
            evidence_level = vuln.get('component_evidence_level', 'C')
            weight = {"A": 1.0, "B": 0.5, "C": 0.25}.get(evidence_level, 0.25)
            severity = vuln.get('severity', 'Low')
            
            total_weighted += weight
            
            if severity in by_severity:
                by_severity[severity]["raw"] += 1
                by_severity[severity]["weighted"] += weight
        
        return {
            "total": {
                "raw": total_raw,
                "weighted": round(total_weighted, 2)
            },
            "by_severity": {
                sev: {
                    "raw": data["raw"],
                    "weighted": round(data["weighted"], 2)
                }
                for sev, data in by_severity.items()
            }
        }


def create_fusion_engine() -> SBOMFusionEngine:
    """创建融合引擎实例"""
    return SBOMFusionEngine()
