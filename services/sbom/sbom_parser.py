"""
SBOM 解析器 - v2.7.0-Phase2

支持格式:
- SPDX 2.3 (JSON)
- CycloneDX 1.4 (JSON)
- CSV (简化格式)

使用方式:
    from services.sbom.sbom_parser import SBOMParser
    
    parser = SBOMParser()
    components = parser.parse_file("sbom.json")
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SBOMComponent:
    """SBOM 组件"""
    name: str
    version: str
    supplier: Optional[str] = None
    licenses: Optional[List[str]] = None
    cpe: Optional[str] = None
    purl: Optional[str] = None
    description: Optional[str] = None
    source: str = "sbom"  # 'sbom' 或 'fingerprint'
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SBOMParseError(Exception):
    """SBOM 解析异常"""
    pass


class SBOMParser:
    """SBOM 解析器"""
    
    def __init__(self):
        self.supported_formats = ['spdx-2.3', 'cyclonedx-1.4', 'csv']
    
    def parse_file(self, file_path: str) -> List[SBOMComponent]:
        """
        解析 SBOM 文件
        
        Args:
            file_path: SBOM 文件路径
        
        Returns:
            组件列表
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise SBOMParseError(f"文件不存在：{file_path}")
        
        # 自动检测格式
        format_name = self._detect_format(file_path)
        
        logger.info(f"检测到 SBOM 格式：{format_name}")
        
        # 解析
        if format_name == 'spdx-2.3':
            return self._parse_spdx(file_path)
        elif format_name == 'cyclonedx-1.4':
            return self._parse_cyclonedx(file_path)
        elif format_name == 'csv':
            return self._parse_csv(file_path)
        else:
            raise SBOMParseError(f"不支持的格式：{format_name}")
    
    def parse_string(self, content: str, format_name: str) -> List[SBOMComponent]:
        """
        解析 SBOM 字符串
        
        Args:
            content: SBOM 内容
            format_name: 格式名称
        
        Returns:
            组件列表
        """
        if format_name == 'spdx-2.3':
            return self._parse_spdx_content(json.loads(content))
        elif format_name == 'cyclonedx-1.4':
            return self._parse_cyclonedx_content(json.loads(content))
        else:
            raise SBOMParseError(f"不支持的格式：{format_name}")
    
    def _detect_format(self, file_path: Path) -> str:
        """检测 SBOM 文件格式"""
        suffix = file_path.suffix.lower()
        
        if suffix == '.csv':
            return 'csv'
        
        if suffix in ['.json', '.jsonld']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # SPDX 2.3 检测
                if data.get('spdxVersion') == 'SPDX-2.3':
                    return 'spdx-2.3'
                
                # CycloneDX 1.4 检测
                spec_version = data.get('specVersion', '')
                if spec_version.startswith('1.4'):
                    return 'cyclonedx-1.4'
                
                # 尝试通过结构判断
                if 'packages' in data and 'SPDXRef-DOCUMENT' in str(data):
                    return 'spdx-2.3'
                
                if 'components' in data and 'bomFormat' in data:
                    return 'cyclonedx-1.4'
                
            except json.JSONDecodeError:
                pass
        
        raise SBOMParseError(f"无法识别文件格式：{file_path}")
    
    def _parse_spdx(self, file_path: Path) -> List[SBOMComponent]:
        """解析 SPDX 2.3 格式"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return self._parse_spdx_content(data)
    
    def _parse_spdx_content(self, data: Dict) -> List[SBOMComponent]:
        """解析 SPDX 2.3 内容"""
        components = []
        
        packages = data.get('packages', [])
        
        for pkg in packages:
            name = pkg.get('name', 'unknown')
            version = pkg.get('versionInfo', 'unknown')
            supplier = pkg.get('supplier')
            download_location = pkg.get('downloadLocation')
            
            # 提取许可证
            licenses = []
            license_concluded = pkg.get('licenseConcluded')
            if license_concluded:
                if license_concluded != 'NOASSERTION':
                    licenses.append(license_concluded)
            
            # 提取外部引用（CPE/purl）
            cpe = None
            purl = None
            external_refs = pkg.get('externalRefs', [])
            for ref in external_refs:
                ref_type = ref.get('referenceType')
                locator = ref.get('referenceLocator')
                if ref_type == 'cpe22Type' or ref_type == 'cpe23Type':
                    cpe = locator
                elif ref_type == 'purl':
                    purl = locator
            
            components.append(SBOMComponent(
                name=name,
                version=version,
                supplier=supplier,
                licenses=licenses if licenses else None,
                cpe=cpe,
                purl=purl,
                description=None
            ))
        
        logger.info(f"SPDX 解析完成：{len(components)} 个组件")
        return components
    
    def _parse_cyclonedx(self, file_path: Path) -> List[SBOMComponent]:
        """解析 CycloneDX 1.4 格式"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return self._parse_cyclonedx_content(data)
    
    def _parse_cyclonedx_content(self, data: Dict) -> List[SBOMComponent]:
        """解析 CycloneDX 1.4 内容"""
        components = []
        
        bom_components = data.get('components', [])
        
        for comp in bom_components:
            name = comp.get('name', 'unknown')
            version = comp.get('version', 'unknown')
            supplier = comp.get('supplier', {}).get('name') if comp.get('supplier') else None
            description = comp.get('description')
            
            # 提取许可证
            licenses = []
            license_obj = comp.get('licenses', [])
            for lic in license_obj:
                lic_id = lic.get('license', {}).get('id')
                if lic_id:
                    licenses.append(lic_id)
            
            # 提取外部标识
            cpe = comp.get('cpe')
            purl = comp.get('purl')
            
            components.append(SBOMComponent(
                name=name,
                version=version,
                supplier=supplier,
                licenses=licenses if licenses else None,
                cpe=cpe,
                purl=purl,
                description=description
            ))
        
        logger.info(f"CycloneDX 解析完成：{len(components)} 个组件")
        return components
    
    def _parse_csv(self, file_path: Path) -> List[SBOMComponent]:
        """解析 CSV 格式（简化格式）"""
        components = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                name = row.get('name', row.get('Name', 'unknown'))
                version = row.get('version', row.get('Version', 'unknown'))
                supplier = row.get('supplier', row.get('Supplier'))
                cpe = row.get('cpe', row.get('CPE'))
                purl = row.get('purl', row.get('PURL'))
                licenses_str = row.get('licenses', row.get('Licenses', ''))
                
                licenses = [l.strip() for l in licenses_str.split(';') if l.strip()] if licenses_str else None
                
                components.append(SBOMComponent(
                    name=name,
                    version=version,
                    supplier=supplier,
                    licenses=licenses,
                    cpe=cpe,
                    purl=purl
                ))
        
        logger.info(f"CSV 解析完成：{len(components)} 个组件")
        return components


def compare_sbom_with_fingerprint(
    sbom_components: List[SBOMComponent],
    fingerprint_components: List[Dict]
) -> Dict:
    """
    比较 SBOM 声明组件与指纹识别组件（v2.7.0-Phase3 增强版）
    
    Args:
        sbom_components: SBOM 解析的组件列表
        fingerprint_components: 指纹识别的组件列表（字典格式，含 confidence/version_note）
    
    Returns:
        比对结果字典
    """
    # 标准化名称映射（处理大小写和命名差异）
    def normalize_name(name: str) -> str:
        return name.lower().replace('-', '').replace('_', '').replace(' ', '')
    
    # 创建指纹组件索引（按标准化名称）
    fingerprint_index = {}
    for comp in fingerprint_components:
        norm_name = normalize_name(comp.get('name', ''))
        fingerprint_index[norm_name] = comp
    
    # 创建 SBOM 组件索引
    sbom_index = {}
    for comp in sbom_components:
        norm_name = normalize_name(comp.name)
        sbom_index[norm_name] = comp
    
    # 分类
    matched = []
    sbom_only = []
    fingerprint_only = []
    
    # 检查 SBOM 组件
    for norm_name, sbom_comp in sbom_index.items():
        if norm_name in fingerprint_index:
            fp_comp = fingerprint_index[norm_name]
            
            # 版本比较
            sbom_version = sbom_comp.version
            fp_version = fp_comp.get('version', 'unknown')
            fp_confidence = fp_comp.get('confidence', 'high')
            fp_version_note = fp_comp.get('version_note')
            
            if sbom_version == fp_version:
                status = "confirmed"
            elif fp_version == 'unknown':
                status = "sbom_version"
            else:
                status = "version_mismatch"
            
            matched.append({
                "name": sbom_comp.name,
                "sbom_version": sbom_version,
                "fingerprint_version": fp_version,
                "confidence": fp_confidence,
                "version_note": fp_version_note,
                "status": status,
                "evidence": fp_comp.get('evidence', [])
            })
        else:
            sbom_only.append({
                "name": sbom_comp.name,
                "version": sbom_comp.version,
                "warning": "二进制未命中，可能符号裁剪或未链接",
                "cpe": sbom_comp.cpe,
                "purl": sbom_comp.purl
            })
    
    # 检查指纹组件（找出 SBOM 未声明的）
    for norm_name, fp_comp in fingerprint_index.items():
        if norm_name not in sbom_index:
            fingerprint_only.append({
                "name": fp_comp.get('name'),
                "version": fp_comp.get('version', 'unknown'),
                "confidence": fp_comp.get('confidence', 'high'),
                "version_note": fp_comp.get('version_note'),
                "warning": "SBOM 未声明，可能遗漏",
                "evidence": fp_comp.get('evidence', [])
            })
    
    # 生成告警
    warnings = []
    
    if sbom_only:
        warnings.append({
            "type": "sbom_not_in_fingerprint",
            "count": len(sbom_only),
            "components": [c["name"] for c in sbom_only],
            "message": f"{len(sbom_only)} 个组件在 SBOM 中声明但二进制未检测到"
        })
    
    if fingerprint_only:
        warnings.append({
            "type": "fingerprint_not_in_sbom",
            "count": len(fingerprint_only),
            "components": [c["name"] for c in fingerprint_only],
            "message": f"{len(fingerprint_only)} 个组件在二进制中检测到但 SBOM 未声明"
        })
    
    version_mismatches = [m for m in matched if m["status"] == "version_mismatch"]
    if version_mismatches:
        warnings.append({
            "type": "version_mismatch",
            "count": len(version_mismatches),
            "components": [
                {"name": m["name"], "sbom_version": m["sbom_version"], "fingerprint_version": m["fingerprint_version"]}
                for m in version_mismatches
            ],
            "message": f"{len(version_mismatches)} 个组件版本不一致"
        })
    
    # Phase 3: 版本未知组件统计
    unknown_version_components = [
        m for m in matched 
        if m.get("confidence") == "medium" or m.get("confidence") == "low"
    ]
    if unknown_version_components:
        warnings.append({
            "type": "version_unknown",
            "count": len(unknown_version_components),
            "components": [
                {"name": c["name"], "version_note": c.get("version_note")}
                for c in unknown_version_components
            ],
            "message": f"{len(unknown_version_components)} 个组件版本未知（需厂商提供）"
        })
    
    return {
        "matched": matched,
        "sbom_only": sbom_only,
        "fingerprint_only": fingerprint_only,
        "warnings": warnings,
        "summary": {
            "total_sbom": len(sbom_components),
            "total_fingerprint": len(fingerprint_components),
            "matched_count": len(matched),
            "sbom_only_count": len(sbom_only),
            "fingerprint_only_count": len(fingerprint_only),
            "unknown_version_count": len(unknown_version_components)
        }
    }
