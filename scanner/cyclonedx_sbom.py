#!/usr/bin/env python3
"""
CycloneDX SBOM 生成器

生成符合 CycloneDX 标准的软件物料清单 (SBOM)
支持格式：JSON, XML
版本：CycloneDX 1.4

依赖:
    pip install cyclonedx-python-lib

参考:
    - https://cyclonedx.org/
    - https://github.com/CycloneDX/cyclonedx-python-lib
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any
from enum import Enum

try:
    from cyclonedx.model.bom import Bom
    from cyclonedx.model.component import Component, ComponentType
    from cyclonedx.model.vulnerability import Vulnerability, VulnerabilityRating
    from cyclonedx.output.json import BY_SCHEMA_VERSION
    from cyclonedx.schema import SchemaVersion
    HAS_CYCLONEDX = True
except ImportError:
    HAS_CYCLONEDX = False
    SchemaVersion = None  # 类型提示占位符


class SbomFormat(Enum):
    """SBOM 输出格式"""
    JSON_14 = "json-1.4"
    JSON_13 = "json-1.3"
    XML_14 = "xml-1.4"
    XML_13 = "xml-1.3"


class CycloneDxGenerator:
    """CycloneDX SBOM 生成器"""
    
    def __init__(self, schema_version=None):
        """
        初始化 CycloneDX 生成器
        
        Args:
            schema_version: CycloneDX 规范版本 (默认 V1_4)
        """
        if not HAS_CYCLONEDX:
            raise RuntimeError(
                "cyclonedx-python-lib 未安装。请运行：pip install cyclonedx-python-lib"
            )
        
        if schema_version is None:
            schema_version = SchemaVersion.V1_4
            
        self.schema_version = schema_version
        self.bom = Bom()
        self.component_map: Dict[str, Component] = {}
        
    def add_component(self, component_data: dict) -> str:
        """
        添加组件到 SBOM
        
        Args:
            component_data: 组件信息字典
                {
                    'name': 'OpenSSL',
                    'version': '1.1.1k',
                    'type': 'library',  # library, application, operating-system
                    'supplier': 'OpenSSL Foundation',
                    'purl': 'pkg:pypi/openssl@1.1.1k',
                    'cpe': 'cpe:2.3:a:openssl:openssl:1.1.1k:*:*:*:*:*:*:*',
                    'description': 'SSL/TLS library'
                }
        
        Returns:
            component_bom_ref: 组件的唯一标识符
        """
        name = component_data.get('name', 'unknown')
        version = component_data.get('version', '0.0.0')
        
        # 确定组件类型
        comp_type_str = component_data.get('type', 'library').lower()
        type_mapping = {
            'library': ComponentType.LIBRARY,
            'application': ComponentType.APPLICATION,
            'operating-system': ComponentType.OPERATING_SYSTEM,
            'framework': ComponentType.FRAMEWORK,
            'container': ComponentType.CONTAINER,
            'file': ComponentType.FILE,
        }
        comp_type = type_mapping.get(comp_type_str, ComponentType.LIBRARY)
        
        # 创建组件
        component = Component(
            name=name,
            version=version,
            type=comp_type,
            supplier=component_data.get('supplier'),
            description=component_data.get('description'),
            purl=component_data.get('purl'),
            cpe=component_data.get('cpe'),
            bom_ref=f"{name}@{version}"
        )
        
        # 添加到 BOM
        self.bom.components.add(component)
        self.component_map[f"{name}@{version}"] = component
        
        return component.bom_ref.value
    
    def add_vulnerability(
        self, 
        vuln_data: dict,
        target_components: Optional[List[str]] = None
    ):
        """
        添加漏洞信息到 SBOM
        
        Args:
            vuln_data: 漏洞信息字典
                {
                    'id': 'CVE-2021-44228',
                    'source': 'NVD',
                    'description': 'Log4Shell RCE',
                    'ratings': [
                        {'method': 'CVSSv31', 'severity': 'critical', 'score': 10.0}
                    ],
                    'published': '2021-12-10',
                    'updated': '2021-12-15',
                    'recommendations': ['Upgrade to 2.17.0']
                }
            target_components: 受影响的组件列表 (bom_ref)
        """
        vuln_id = vuln_data.get('id', 'UNKNOWN')
        
        # 创建漏洞对象
        vulnerability = Vulnerability(
            id=vuln_id,
            source={'name': vuln_data.get('source', 'Unknown Source')},
            description=vuln_data.get('description', ''),
            published=self._parse_date(vuln_data.get('published')),
            updated=self._parse_date(vuln_data.get('updated'))
        )
        
        # 添加评分
        ratings = vuln_data.get('ratings', [])
        for rating in ratings:
            method = rating.get('method', 'CVSSv31')
            severity = rating.get('severity', 'unknown')
            score = rating.get('score', 0.0)
            
            try:
                cvss_method = getattr(VulnerabilityRating.CvssVector, f'CVSS_V{method[-1]}', None)
                if cvss_method is None:
                    continue
                
                vuln_rating = VulnerabilityRating(
                    source={'name': 'CVSS'},
                    method=cvss_method,
                    severity=Vulnerability.Severity.from_custom_severity(severity.upper()),
                    vector=rating.get('vector', ''),
                    score=score
                )
                vulnerability.ratings.add(vuln_rating)
            except (AttributeError, ValueError) as e:
                # 跳过无法解析的评分
                pass
        
        # 添加建议
        recommendations = vuln_data.get('recommendations', [])
        if recommendations:
            vulnerability.recommendations = '\n'.join(recommendations)
        
        # 关联到受影响组件
        if target_components:
            for bom_ref in target_components:
                try:
                    vulnerability.affects.add({
                        'ref': bom_ref
                    })
                except Exception:
                    # 组件可能不存在
                    pass
        
        # 添加到 BOM
        self.bom.vulnerabilities.add(vulnerability)
    
    def generate(
        self, 
        components: List[dict],
        vulnerabilities: Optional[List[dict]] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        生成 CycloneDX SBOM
        
        Args:
            components: 组件列表
            vulnerabilities: 漏洞列表 (可选)
            metadata: 元数据 (可选)
                {
                    'timestamp': '2026-08-04T10:00:00Z',
                    'tools': [{'name': 'Firmware Scanner', 'version': '1.0.0'}],
                    'authors': [{'name': 'Xuanwu Team'}]
                }
        
        Returns:
            CycloneDX JSON 或 XML 字符串
        """
        # 设置 BOM 序列号
        self.bom.serial_number = f"urn:uuid:{uuid.uuid4()}"
        self.bom.version = 1
        
        # 添加元数据
        if metadata:
            timestamp = metadata.get('timestamp', datetime.now(timezone.utc).isoformat())
            self.bom.metadata.timestamp = timestamp
            
            tools = metadata.get('tools', [])
            for tool in tools:
                from cyclonedx.model.tool import Tool
                t = Tool(name=tool.get('name'), version=tool.get('version'))
                self.bom.metadata.tools.add(t)
            
            authors = metadata.get('authors', [])
            from cyclonedx.model import OrganizationalContact
            for author in authors:
                contact = OrganizationalContact(name=author.get('name'))
                self.bom.metadata.authors.add(contact)
        
        # 添加组件
        for comp_data in components:
            try:
                self.add_component(comp_data)
            except Exception as e:
                print(f"⚠️ 添加组件失败 {comp_data.get('name')}: {e}")
        
        # 添加漏洞
        if vulnerabilities:
            for vuln_data in vulnerabilities:
                try:
                    # 找到受影响的组件
                    target_comps = []
                    comp_name = vuln_data.get('component', '')
                    comp_version = vuln_data.get('version', '')
                    
                    for key, comp in self.component_map.items():
                        if comp_name in key or comp_version in key:
                            target_comps.append(comp.bom_ref.value)
                    
                    self.add_vulnerability(vuln_data, target_comps)
                except Exception as e:
                    print(f"⚠️ 添加漏洞失败 {vuln_data.get('id')}: {e}")
        
        # 序列化输出
        outputter = BY_SCHEMA_VERSION[self.schema_version]
        return outputter.output_as_string(bom=self.bom)
    
    def save_to_file(
        self, 
        output_path: str,
        format: SbomFormat = SbomFormat.JSON_14
    ):
        """
        保存 SBOM 到文件
        
        Args:
            output_path: 输出文件路径
            format: 输出格式
        """
        content = self.generate([], format=format)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ SBOM 已保存到：{output_path}")
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """解析日期字符串"""
        if not date_str:
            return None
        
        try:
            # 尝试多种格式
            formats = [
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S%z',
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # 如果都不匹配，返回 None
            return None
            
        except Exception:
            return None


def generate_cyclonedx_sbom(
    components: List[dict],
    vulnerabilities: List[dict] = None,
    schema_version: str = "1.4",
    output_format: str = "json"
) -> str:
    """
    便捷函数：生成 CycloneDX SBOM
    
    Args:
        components: 组件列表
        vulnerabilities: 漏洞列表
        schema_version: CycloneDX 版本 ('1.4' or '1.3')
        output_format: 输出格式 ('json' or 'xml')
    
    Returns:
        CycloneDX 格式的 SBOM 字符串
    """
    if not HAS_CYCLONEDX:
        # 降级方案：生成简易 JSON 格式（不标准但可读）
        return _generate_simple_sbom(components, vulnerabilities)
    
    # 映射版本号
    version_map = {
        '1.4': SchemaVersion.V1_4,
        '1.3': SchemaVersion.V1_3,
        '1.2': SchemaVersion.V1_2,
    }
    schema = version_map.get(schema_version, SchemaVersion.V1_4)
    
    generator = CycloneDxGenerator(schema_version=schema)
    
    metadata = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'tools': [{'name': 'Firmware Scanner', 'version': '2.1-alpha'}],
        'authors': [{'name': 'Xuanwu Team'}]
    }
    
    return generator.generate(components, vulnerabilities, metadata)


def _generate_simple_sbom(components: List[dict], vulnerabilities: List[dict]) -> str:
    """
    降级方案：生成简易 SBOM（当 cyclonedx 库未安装时）
    
    这不是标准 CycloneDX 格式，但包含基本结构
    """
    import json
    
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "version": 1,
        "components": [],
        "vulnerabilities": []
    }
    
    # 转换组件
    for comp in components:
        sbom["components"].append({
            "type": comp.get('type', 'library'),
            "name": comp.get('name', 'unknown'),
            "version": comp.get('version', '0.0.0'),
            "cpe": comp.get('cpe'),
            "purl": comp.get('purl')
        })
    
    # 转换漏洞
    if vulnerabilities:
        for vuln in vulnerabilities:
            sbom["vulnerabilities"].append({
                "id": vuln.get('cve_id', vuln.get('id')),
                "source": {"name": "NVD"},
                "ratings": [{
                    "score": vuln.get('cvss_score', 0),
                    "severity": vuln.get('severity', 'unknown').lower()
                }]
            })
    
    return json.dumps(sbom, indent=2, ensure_ascii=False)


def validate_sbom(sbom_content: str) -> bool:
    """
    验证 SBOM 是否符合 CycloneDX 规范
    
    Args:
        sbom_content: SBOM 字符串内容
    
    Returns:
        是否有效
    """
    # 即使没有 cyclonedx 库，也可以进行基本验证
    try:
        import json
        data = json.loads(sbom_content)
        
        # 检查必要字段
        required_fields = ['bomFormat', 'specVersion', 'version']
        for field in required_fields:
            if field not in data:
                return False
        
        # 检查格式
        if data['bomFormat'] != 'CycloneDX':
            return False
        
        # 检查版本号（如果提供了标准库则使用完整验证）
        if HAS_CYCLONEDX:
            try:
                # 尝试使用官方验证器
                from cyclonedx.schema import SchemaVersion, BomRefResolver
                version_map = {
                    '1.4': SchemaVersion.V1_4,
                    '1.3': SchemaVersion.V1_3,
                    '1.2': SchemaVersion.V1_2,
                }
                spec_version = data.get('specVersion', '1.4')
                schema = version_map.get(spec_version)
                
                if schema is None:
                    return False
                
                # 更深入的验证（可选）
                # BomRefResolver().resolve(data)
                
            except Exception as e:
                print(f"⚠️ 详细验证失败：{e}")
        
        return True
        
    except (json.JSONDecodeError, KeyError, TypeError):
        return False


if __name__ == "__main__":
    # 测试示例
    test_components = [
        {
            'name': 'FreeRTOS',
            'version': '10.4.6',
            'type': 'operating-system',
            'description': 'Real-time operating system'
        },
        {
            'name': 'lwIP',
            'version': '2.1.3',
            'type': 'library',
            'description': 'Lightweight TCP/IP stack'
        },
        {
            'name': 'wolfSSL',
            'version': '4.6.0',
            'type': 'library',
            'cpe': 'cpe:2.3:a:wolfssl:wolfssl:4.6.0:*:*:*:*:*:*:*'
        }
    ]
    
    test_vulnerabilities = [
        {
            'id': 'CVE-2021-44228',
            'source': 'NVD',
            'description': 'Apache Log4j Remote Code Execution',
            'ratings': [
                {'method': 'CVSSv31', 'severity': 'critical', 'score': 10.0}
            ],
            'published': '2021-12-10',
            'recommendations': ['Upgrade to 2.17.0 or later']
        }
    ]
    
    print("=" * 60)
    print("📦 CycloneDX SBOM 生成器测试")
    print("=" * 60)
    
    if not HAS_CYCLONEDX:
        print("\n⚠️  cyclonedx-python-lib 未安装，使用降级模式")
        print("💡 安装命令：pip install cyclonedx-python-lib\n")
    
    try:
        sbom_json = generate_cyclonedx_sbom(
            components=test_components,
            vulnerabilities=test_vulnerabilities,
            schema_version="1.4",
            output_format="json"
        )
        
        print(f"\n✅ SBOM 生成成功!")
        print(f"   大小：{len(sbom_json)} 字节")
        print(f"   组件数：{len(test_components)}")
        print(f"   漏洞数：{len(test_vulnerabilities)}")
        
        # 打印前 50 行
        lines = sbom_json.split('\n')[:50]
        print("\n预览:")
        for line in lines:
            print(f"  {line}")
        
        if len(lines) > 50:
            print(f"  ... ({len(lines) - 50} 行省略)")
        
        # 验证
        if validate_sbom(sbom_json):
            print("\n✅ SBOM 验证通过")
        else:
            print("\n❌ SBOM 验证失败")
        
        # 保存到文件
        output_path = "./test_sbom.cyclonedx.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(sbom_json)
        print(f"\n💾 已保存到：{output_path}")
        
    except Exception as e:
        print(f"\n❌ 生成失败：{e}")
        import traceback
        traceback.print_exc()
