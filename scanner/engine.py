"""
固件漏洞扫描引擎核心模块 - 增强版（支持 Binwalk）
包含解包、SBOM 生成、CVE 匹配等核心功能
"""

import os
import re
import subprocess
import hashlib
import sqlite3
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from .tool_detector import get_detector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入 EPSS 缓存
from .epss_cache import EPSSCacheManager

# 全局 EPSS 管理器（单例模式）
_epss_manager: Optional[EPSSCacheManager] = None

def get_epss_manager(cache_dir: str = "./cache/epss") -> EPSSCacheManager:
    """获取 EPSS 管理器实例（懒加载）"""
    global _epss_manager
    
    if _epss_manager is None:
        try:
            # 确保缓存目录存在
            Path(cache_dir).mkdir(parents=True, exist_ok=True)
            
            # 初始化管理器
            _epss_manager = EPSSCacheManager(os.path.join(cache_dir, "epss_cache.db"))
            
            # 检查数据是否可用，不可用则警告但不阻塞
            if not _epss_manager.is_data_available():
                logger.warning("⚠️  EPSS 缓存未初始化或已过期")
                logger.warning("   首次使用将自动下载数据，可能较慢")
                logger.info("   建议手动下载：python -m scanner.epss_cache")
            else:
                stats = _epss_manager.get_statistics()
                logger.info(f"✅ EPSS 缓存已加载 ({stats['total_records']:,} 条记录)")
                
        except Exception as e:
            logger.error(f"初始化 EPSS 缓存失败：{e}")
            _epss_manager = None
    
    return _epss_manager


@dataclass
class Component:
    """软件组件信息"""
    name: str
    version: str
    type: str  # 'library', 'os', 'language'
    path: str
    cpe: Optional[str] = None
    
    def to_dict(self):
        return {
            'name': self.name,
            'version': self.version,
            'type': self.type,
            'path': self.path,
            'cpe': self.cpe
        }


@dataclass
class ExtractedFile(NamedTuple):
    """Binwalk 提取的文件信息"""
    offset: int
    description: str
    file_type: str
    extracted_path: Optional[str] = None


@dataclass
class Vulnerability:
    """漏洞信息"""
    cve_id: str
    component_name: str
    component_version: str
    severity: str
    cvss_score: float
    cvss_vector: str
    description: str
    fixed_version: Optional[str]
    published_date: datetime
    epss_score: Optional[float] = None
    priority_score: Optional[float] = None
    
    def is_r155_non_compliant(self, days_threshold: int = 180):
        """检查是否 R155 不合规 (CVSS>=7.0 且>180 天未修复)"""
        if self.cvss_score < 7.0:
            return False
        age_days = (datetime.now() - self.published_date).days
        return age_days > days_threshold and not self.fixed_version
    
    def calculate_priority(self, cvss_weight: float = 0.35, 
                          epss_weight: float = 0.45, 
                          component_weight: float = 0.20) -> float:
        """计算优先级分数"""
        cvss_normalized = self.cvss_score / 10.0
        epss_normalized = self.epss_score or 0.0
        
        critical_components = ['openssl', 'libssl', 'linux-kernel', 'freertos']
        component_factor = 1.0 if any(c in self.component_name.lower() 
                                      for c in critical_components) else 0.5
        
        self.priority_score = (cvss_weight * cvss_normalized +
                              epss_weight * epss_normalized +
                              component_weight * component_factor)
        return self.priority_score


class FirmwareExtractor:
    """固件解包器 - 优先使用 Binwalk，支持降级到 7-Zip"""
    
    def __init__(self, work_dir: str):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用新的跨平台工具检测器
        detector = get_detector()
        tools = detector.detect_all_tools()
        
        self.binwalk_available = tools['binwalk']['available']
        self.sevenzip_available = tools['7zip']['available']
        self.unsquashfs_available = tools['unsquashfs']['available']
        self.objcopy_available = tools['objcopy']['available']
        
        logger.info(f"Binwalk: {'✅' if self.binwalk_available else '❌'} {tools['binwalk'].get('version', 'N/A')}")
        logger.info(f"7-Zip: {'✅' if self.sevenzip_available else '❌'} {tools['7zip'].get('version', 'N/A')}")
        logger.info(f"unsquashfs: {'✅' if self.unsquashfs_available else '❌'}")
        logger.info(f"objcopy: {'✅' if self.objcopy_available else '❌'}")
    
    def _check_binwalk(self) -> bool:
        """检查 Binwalk 是否可用（已弃用，保留兼容）"""
        return self.binwalk_available
    
    def _check_7zip(self) -> bool:
        """检查 7-Zip 是否可用（已弃用，保留兼容）"""
        return self.sevenzip_available
    
    def scan_firmware(self, firmware_path: str) -> List[ExtractedFile]:
        """扫描固件，识别内部结构（不提取）"""
        logger.info(f"扫描固件结构：{firmware_path}")
        
        if not self.binwalk_available:
            logger.warning("Binwalk 不可用，跳过扫描")
            return []
        
        try:
            result = subprocess.run(
                ['binwalk', firmware_path],
                capture_output=True, text=True
            )
            
            # 解析输出
            files = []
            for line in result.stdout.split('\n'):
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        offset = int(parts[0], 16) if 'x' in parts[0].lower() else int(parts[0])
                        desc = ' '.join(parts[2:])
                        files.append(ExtractedFile(
                            offset=offset,
                            description=desc,
                            file_type=desc.split(',')[0] if ',' in desc else desc
                        ))
                    except (ValueError, IndexError):
                        continue
            
            logger.info(f"发现 {len(files)} 个嵌入式对象")
            return files
            
        except Exception as e:
            logger.error(f"扫描失败：{e}")
            return []
    
    def extract_firmware(self, firmware_path: str) -> Path:
        """智能解包固件（优先 Binwalk，自动选择最佳方案）"""
        logger.info(f"解包固件：{firmware_path}")
        
        # 1. 优先使用 Binwalk（推荐）
        if self.binwalk_available:
            logger.info("使用 Binwalk 进行深度分析和提取...")
            extracted_path = self.extract_with_binwalk(firmware_path)
            if extracted_path.exists():
                return extracted_path
        
        # 2. Binwalk 失败后尝试 unsquashfs（针对纯 SquashFS）
        logger.info("尝试使用 unsquashfs 直接解压...")
        unsquashfs_path = self.extract_squashfs_mount(firmware_path)
        if unsquashfs_path.exists():
            return unsquashfs_path
        
        # 3. 降级到 7-Zip
        if self.sevenzip_available:
            logger.info("回退到 7-Zip 解包...")
            extracted_path = self.extract_with_7zip(firmware_path)
            if extracted_path.exists():
                return extracted_path
        
        # 4. 最后手段：返回原文件目录
        logger.warning("所有解包方法失败，使用原始文件")
        return Path(firmware_path).parent
    
    def extract_with_binwalk(self, firmware_path: str) -> Path:
        """使用 Binwalk 解包固件（推荐方式）"""
        output_dir = self.work_dir / "extracted"
        output_dir.mkdir(exist_ok=True)
        
        try:
            # 策略 1: 递归提取所有（Matryoshka 模式）
            cmd_recursive = [
                'binwalk',
                '-e',           # 自动提取
                '-M',           # 递归提取（重要！）
                '-d',           # 禁用签名数据库更新
                '--dir', str(output_dir),
                firmware_path
            ]
            
            logger.debug(f"执行 Binwalk 命令：{' '.join(cmd_recursive)}")
            result = subprocess.run(
                cmd_recursive,
                capture_output=True, text=True,
                timeout=300  # 5 分钟超时
            )
            
            logger.debug(f"Binwalk 输出:\n{result.stdout}")
            if result.stderr:
                logger.debug(f"Binwalk 错误:\n{result.stderr}")
            
            # 检查是否有提取内容
            extracted_contents = list(output_dir.glob("*"))
            if extracted_contents:
                logger.info(f"✅ Binwalk 成功提取 {len(extracted_contents)} 个项目")
                
                # 显示提取的文件类型
                file_types = set()
                for item in extracted_contents:
                    if item.is_file():
                        file_types.add(item.suffix)
                    elif item.is_dir():
                        file_types.add(f"[DIR]{item.name}")
                
                logger.info(f"提取的文件类型：{', '.join(file_types)}")
                return output_dir
            
            # 策略 2: 只列出不提取
            logger.warning("递归提取无结果，尝试简单模式...")
            cmd_simple = [
                'binwalk',
                '-e',
                '--dir', str(output_dir),
                firmware_path
            ]
            
            result = subprocess.run(cmd_simple, capture_output=True, text=True, timeout=120)
            return output_dir
            
        except subprocess.TimeoutExpired:
            logger.error("Binwalk 提取超时")
            return output_dir
        except Exception as e:
            logger.error(f"Binwalk 解包失败：{e}")
            return output_dir
    
    def extract_squashfs_mount(self, firmware_path: str) -> Path:
        """使用 unsquashfs 直接解压（针对纯 SquashFS 镜像）"""
        output_dir = self.work_dir / "squashfs_root"
        output_dir.mkdir(exist_ok=True)
        
        try:
            # 检测是否为 SquashFS
            detect_result = subprocess.run(
                ['file', firmware_path],
                capture_output=True, text=True
            )
            
            if 'SquashFS' not in detect_result.stdout:
                logger.info("非 SquashFS 格式，跳过 unsquashfs")
                return Path("")
            
            logger.info("检测到 SquashFS，使用 unsquashfs 提取...")
            result = subprocess.run(
                ['unsquashfs', '-f', '-d', str(output_dir), firmware_path],
                capture_output=True, text=True, check=True,
                timeout=300
            )
            
            logger.info(f"✅ Unsquashfs 提取成功：{output_dir}")
            return output_dir
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Unsquashfs 失败：{e}")
            return Path("")
        except Exception as e:
            logger.error(f"Unsquashfs 异常：{e}")
            return Path("")
    
    def extract_with_7zip(self, firmware_path: str) -> Path:
        """使用 7-Zip 解包（降级方案）"""
        output_dir = self.work_dir / "7z_extracted"
        output_dir.mkdir(exist_ok=True)
        
        try:
            result = subprocess.run(
                ['7z', 'x', '-o' + str(output_dir), '-y', firmware_path],
                capture_output=True, text=True, check=True
            )
            logger.info(f"✅ 7-Zip 提取成功：{output_dir}")
            return output_dir
        except Exception as e:
            logger.error(f"7-Zip 解包失败：{e}")
            return Path("")
    
    def hex_to_bin(self, hex_path: str) -> Path:
        """将 HEX/SREC 文件转换为二进制"""
        logger.info(f"HEX/SREC 转二进制：{hex_path}")
        output_path = self.work_dir / f"{Path(hex_path).stem}.bin"
        
        # 优先尝试 objcopy
        try:
            subprocess.run(
                ['objcopy', '-I', 'ihex', '-O', 'binary', hex_path, str(output_path)],
                check=True, timeout=60
            )
            logger.info("✅ 使用 objcopy 转换成功")
            return output_path
        except FileNotFoundError:
            logger.warning("objcopy 不可用，使用 Python 解析")
        except subprocess.CalledProcessError as e:
            logger.warning(f"objcopy 失败：{e}，尝试其他方法")
        
        # Python 备用实现
        return self._parse_hex_python(hex_path, output_path)
    
    def _parse_hex_python(self, hex_path: str, output_path: Path) -> Path:
        """纯 Python 实现 HEX/SREC 文件解析"""
        logger.info("使用 Python 解析 HEX/SREC 文件...")
        
        with open(hex_path, 'r') as f_in, open(output_path, 'wb') as f_out:
            buffer = {}
            base_addr = 0
            
            for line in f_in:
                line = line.strip()
                if not line or not line.startswith(':'):
                    continue
                
                try:
                    byte_count = int(line[1:3], 16)
                    addr = int(line[3:7], 16)
                    record_type = int(line[7:9], 16)
                    
                    if record_type == 0:  # 数据记录
                        data = bytes.fromhex(line[9:9+byte_count*2])
                        for i, b in enumerate(data):
                            buffer[base_addr + addr + i] = b
                    
                    elif record_type == 1:  # 结束
                        break
                    
                    elif record_type == 4:  # 扩展线性地址
                        base_addr = int(line[9:13], 16) << 16
                    
                    elif record_type == 2:  # 扩展段地址（SREC）
                        base_addr = int(line[9:13], 16) << 4
                        
                except (ValueError, IndexError) as e:
                    logger.debug(f"跳过无效行：{line[:20]}... ({e})")
                    continue
            
            # 写入二进制
            if buffer:
                max_addr = max(buffer.keys())
                for i in range(max_addr + 1):
                    f_out.write(bytes([buffer.get(i, 0)]))
                logger.info(f"✅ Python 解析完成，大小：{max_addr + 1} bytes")
            else:
                logger.warning("未能提取任何数据")
        
        return output_path


class SBOMGenerator:
    """SBOM 生成器 - 支持多种格式"""
    
    def __init__(self):
        self.syft_available = self._check_syft()
        self.cyclonedx_available = self._check_cyclonedx()
        logger.info(f"Syft 可用性：{'✅' if self.syft_available else '❌'}")
        logger.info(f"CycloneDX: {'✅' if self.cyclonedx_available else '❌'}")
    
    def _check_syft(self) -> bool:
        """检查 Syft 是否可用"""
        try:
            result = subprocess.run(['syft', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _check_cyclonedx(self) -> bool:
        """检查 CycloneDX 库是否可用"""
        try:
            from scanner.cyclonedx_sbom import HAS_CYCLONEDX
            return HAS_CYCLONEDX
        except ImportError:
            return False
    
    def generate_sbom(self, firmware_path: str, firmware_type: str = 'auto') -> List[Component]:
        """统一 SBOM 生成入口"""
        logger.info(f"生成 SBOM: {firmware_path} (类型：{firmware_type})")
        
        # 自动检测类型
        if firmware_type == 'auto':
            firmware_type = self._detect_firmware_type(firmware_path)
        
        # Linux/ELF固件优先用Syft
        if firmware_type in ['elf', 'squashfs', 'linux']:
            if self.syft_available:
                try:
                    return self.generate_syft_sbom(firmware_path)
                except Exception as e:
                    logger.warning(f"Syft 失败，降级到字符串提取：{e}")
        
        # MCU 固件或 Syft 不可用时使用字符串提取
        return self.extract_mcu_components(firmware_path)
    
    def _detect_firmware_type(self, firmware_path: str) -> str:
        """使用 file 命令检测固件类型"""
        try:
            result = subprocess.run(
                ['file', '-b', firmware_path],
                capture_output=True, text=True
            )
            output = result.stdout.lower()
            
            if 'squashfs' in output:
                return 'squashfs'
            elif 'elf' in output:
                return 'elf'
            elif 'intel hex' in output:
                return 'hex'
            elif 'motorola s-record' in output:
                return 'srec'
            elif 'data' in output or 'binary' in output:
                return 'bin'
            else:
                return 'unknown'
                
        except Exception as e:
            logger.error(f"类型检测失败：{e}")
            return 'unknown'
    
    def generate_syft_sbom(self, firmware_path: str) -> List[Component]:
        """使用 Syft 生成 SBOM (适用于 Linux/ELF 固件)"""
        logger.info(f"Syft 扫描：{firmware_path}")
        
        try:
            result = subprocess.run(
                ['syft', '-o', 'json', firmware_path],
                capture_output=True, text=True, check=True,
                timeout=300
            )
            return self._parse_syft_json(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Syft 扫描失败：{e}")
            raise RuntimeError(f"Syft 扫描失败：{e.stderr}")
    
    def _parse_syft_json(self, json_output: str) -> List[Component]:
        """解析 Syft JSON 输出"""
        import json
        data = json.loads(json_output)
        components = []
        
        seen = set()  # 去重
        for pkg in data.get('artifacts', []):
            key = (pkg['name'], pkg['version'])
            if key in seen:
                continue
            seen.add(key)
            
            comp = Component(
                name=pkg['name'],
                version=pkg['version'],
                type=pkg.get('type', 'unknown'),
                path=pkg.get('locations', [{}])[0].get('path', ''),
                cpe=pkg.get('cpes', [''])[0] if pkg.get('cpes') else None
            )
            components.append(comp)
        
        logger.info(f"Syft 识别 {len(components)} 个组件")
        return components
    
    def extract_mcu_components(self, firmware_path: str) -> List[Component]:
        """从 MCU 裸机固件提取组件特征"""
        logger.info(f"MCU 组件提取：{firmware_path}")
        components = []
        
        # 提取可打印字符串
        strings_output = self._extract_strings(firmware_path)
        
        # 增强的模式匹配库
        patterns = {
            'FreeRTOS': (re.compile(r'FreeRTOS|xTaskCreate|pvPortMalloc|xSemaphoreCreate'), 'rtos'),
            'lwIP': (re.compile(r'lwIP|tcp_connect|udp_sendto|netif_add|pbuf_alloc'), 'network'),
            'wolfSSL': (re.compile(r'wolfSSL_|WOLFSSL_|SSL_set_fd|wolfSSL_Init'), 'crypto'),
            'mbedTLS': (re.compile(r'mbedtls_|MBEDTLS_|mbedtls_ssl_init'), 'crypto'),
            'OpenSSL': (re.compile(r'OPENSSL_|SSL_library_init|EVP_'), 'crypto'),
            'uCLibc': (re.compile(r'uCLIBC|__uclibc|vprintf'), 'libc'),
            'BusyBox': (re.compile(r'BusyBox\s+v?\d+'), 'utilities'),
            'Zlib': (re.compile(r'zlib_h\w+|deflateInit|inflateEnd'), 'compression'),
            'Newlib': (re.compile(r'_newlib_version|sbrk'), 'libc'),
            'Chromium': (re.compile(r'Chromium|blink::'), 'browser'),
        }
        
        detected = {}
        for name, (pattern, comp_type) in patterns.items():
            matches = pattern.findall(strings_output)
            if matches:
                version = self._extract_version(strings_output, name)
                match_count = len(matches)
                
                detected[name] = Component(
                    name=name,
                    version=version or 'unknown',
                    type=comp_type,
                    path=firmware_path
                )
                
                logger.debug(f"✓ 识别 {name}: {match_count} 次匹配，版本={version}")
        
        logger.info(f"识别到 {len(detected)} 个 MCU 组件：{', '.join(detected.keys())}")
        return list(detected.values())
    
    def _extract_strings(self, binary_path: str, min_length: int = 5) -> str:
        """提取二进制文件中的可打印字符串（优化版）"""
        try:
            # 优先使用系统 strings 工具
            result = subprocess.run(
                ['strings', '-n', str(min_length), binary_path],
                capture_output=True, text=True, timeout=60
            )
            return result.stdout
        except FileNotFoundError:
            logger.warning("strings 命令不可用，使用 Python 实现")
        except Exception as e:
            logger.error(f"strings 失败：{e}")
        
        # Python 备用实现
        return self._strings_python(binary_path, min_length)
    
    def _strings_python(self, binary_path: str, min_length: int = 5) -> str:
        """Python 实现字符串提取（优化版）"""
        strings = []
        current = []
        
        with open(binary_path, 'rb') as f:
            while chunk := f.read(65536):  # 64KB 块读取
                for byte in chunk:
                    if 32 <= byte <= 126:  # 可打印 ASCII
                        current.append(chr(byte))
                    else:
                        if len(current) >= min_length:
                            strings.append(''.join(current))
                        current = []
        
        if len(current) >= min_length:
            strings.append(''.join(current))
        
        return '\n'.join(strings)
    
    def _extract_version(self, strings_text: str, component_name: str) -> Optional[str]:
        """从字符串中提取版本号"""
        # 增强的版本提取正则
        patterns = [
            rf'{component_name}\s*v?(\d+\.\d+\.\d+(?:[-+][\w.]+)?)',
            rf'{component_name}\s+(\d+\.\d+(?:\.\d+)?)',
            rf'(\d+\.\d+\.\d+(?:[-+][\w.]+)?)\s+{component_name}',
            rf'{component_name}[\s_-](\d+\.\d+\.\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, strings_text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def generate_cyclonedx_sbom(
        self, 
        components: List[Component],
        vulnerabilities: Optional[List[Vulnerability]] = None,
        output_format: str = 'json',
        schema_version: str = '1.4'
    ) -> str:
        """
        生成 CycloneDX 格式的 SBOM
        
        Args:
            components: 组件列表
            vulnerabilities: 漏洞列表 (可选)
            output_format: 输出格式 ('json' or 'xml')
            schema_version: CycloneDX 版本 ('1.4' or '1.3')
        
        Returns:
            CycloneDX 格式的 SBOM 字符串
        """
        try:
            from scanner.cyclonedx_sbom import generate_cyclonedx_sbom as cyclonedx_generator
            
            # 转换组件为 CycloneDX 格式
            comp_data = []
            for comp in components:
                comp_dict = {
                    'name': comp.name,
                    'version': comp.version or '0.0.0',
                    'type': comp.type or 'library',
                    'description': getattr(comp, 'description', None),
                }
                
                if hasattr(comp, 'cpe') and comp.cpe:
                    comp_dict['cpe'] = comp.cpe
                
                if hasattr(comp, 'purl') and comp.purl:
                    comp_dict['purl'] = comp.purl
                
                if hasattr(comp, 'path') and comp.path:
                    comp_dict['supplier'] = f"Found in: {comp.path}"
                
                comp_data.append(comp_dict)
            
            # 转换漏洞
            vuln_data = []
            if vulnerabilities:
                for vuln in vulnerabilities:
                    vuln_dict = {
                        'id': vuln.cve_id,
                        'source': 'NVD',
                        'description': vuln.description or '',
                        'published': vuln.published_date,
                        'ratings': [{
                            'method': 'CVSSv31',
                            'severity': vuln.severity.lower() if vuln.severity else 'unknown',
                            'score': vuln.cvss_score or 0.0
                        }]
                    }
                    
                    if vuln.fix_versions:
                        vuln_dict['recommendations'] = [f"Upgrade to {ver}"]
                    
                    vuln_data.append(vuln_dict)
            
            # 生成 CycloneDX SBOM
            sbom_json = cyclonedx_generator(
                components=comp_data,
                vulnerabilities=vuln_data,
                schema_version=schema_version,
                output_format=output_format
            )
            
            logger.info(f"✅ CycloneDX SBOM 生成成功 (格式={output_format}, 版本={schema_version})")
            return sbom_json
            
        except Exception as e:
            logger.error(f"❌ CycloneDX SBOM 生成失败：{e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"CycloneDX SBOM 生成失败：{e}")
    
    def generate_syft_sbom_raw(self, firmware_path: str) -> str:
        """
        使用 Syft 生成原始 JSON SBOM
        
        Args:
            firmware_path: 固件路径
        
        Returns:
            Syft JSON 格式字符串
        """
        if not self.syft_available:
            raise RuntimeError("Syft 未安装，请先运行：sudo snap install syft")
        
        try:
            result = subprocess.run(
                ['syft', '-o', 'json', firmware_path],
                capture_output=True, text=True, check=True,
                timeout=300
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Syft SBOM 生成失败：{e}")
            raise RuntimeError(f"Syft SBOM 生成失败：{e.stderr}")


class CVEMatcher:
    """CVE 匹配器 - 直接查询 Grype SQLite DB"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self._connect()
    
    def _connect(self):
        """连接 SQLite 数据库"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Grype 数据库不存在：{self.db_path}")
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"已连接 Grype 数据库：{self.db_path}")
    
    def query_vulnerabilities(self, components: List[Component]) -> List[Vulnerability]:
        """为组件列表查询 CVE"""
        logger.info(f"开始 CVE 查询，组件数：{len(components)}")
        vulnerabilities = []
        
        for i, comp in enumerate(components):
            if (i + 1) % 50 == 0:
                logger.info(f"正在查询组件 {i+1}/{len(components)}: {comp.name}")
            
            comp_vulns = self._query_component(comp)
            vulnerabilities.extend(comp_vulns)
        
        logger.info(f"CVE 查询完成，发现 {len(vulnerabilities)} 个漏洞")
        return vulnerabilities
    
    def _query_component(self, component: Component) -> List[Vulnerability]:
        """查询单个组件的漏洞（优化版）"""
        vulns = []
        
        if not component.name:
            return []
        
        try:
            cursor = self.conn.cursor()
            
            # 尝试多种匹配策略
            search_patterns = [
                f'%{component.name}%',
                f'{component.name}',
                f'{component.name.lower()}',
            ]
            
            for pattern in search_patterns:
                cursor.execute("""
                    SELECT p.id, p.name, p.version, p.type
                    FROM package p
                    WHERE LOWER(p.name) LIKE LOWER(?)
                    LIMIT 5
                """, (pattern,))
                
                packages = cursor.fetchall()
                
                for pkg in packages:
                    # 模糊版本匹配
                    version_match = self._match_version(component.version, pkg['version'])
                    if not version_match:
                        continue
                    
                    # 查找关联的漏洞
                    cursor.execute("""
                        SELECT DISTINCT v.cve, v.severity, v.cvss_score, v.cvss_vector,
                               v.description, v.fixed_version, v.published_date
                        FROM vulnerability v
                        JOIN package_vulnerability pv ON v.id = pv.vulnerability_id
                        WHERE pv.package_id = ?
                        AND (v.severity IN ('Critical', 'High', 'Medium') OR v.cvss_score >= 5.0)
                        ORDER BY v.cvss_score DESC
                        LIMIT 50
                    """, (pkg['id'],))
                    
                    for row in cursor.fetchall():
                        vuln = Vulnerability(
                            cve_id=row['cve'],
                            component_name=component.name,
                            component_version=component.version,
                            severity=row['severity'] or 'Unknown',
                            cvss_score=float(row['cvss_score']) if row['cvss_score'] else 0.0,
                            cvss_vector=row['cvss_vector'] or '',
                            description=row['description'] or '',
                            fixed_version=row['fixed_version'],
                            published_date=datetime.strptime(row['published_date'], '%Y-%m-%d')
                                           if row['published_date'] else datetime.now()
                        )
                        
                        # 避免重复
                        if not any(v.cve_id == vuln.cve_id for v in vulns):
                            vuln.epss_score = self._get_epss_score_cached(vuln.cve_id)
                            vulns.append(vuln)
            
        except sqlite3.Error as e:
            logger.error(f"查询 CVE 失败 ({component.name}): {e}")
            return []
        
        return vulns
    
    def _match_version(self, target_version: str, db_version: str) -> bool:
        """版本匹配逻辑（简化版）"""
        if not target_version or target_version == 'unknown':
            return True  # 未知版本时匹配所有
        
        try:
            # 简单的前缀匹配
            return db_version.startswith(target_version.split('-')[0][:4])
        except:
            return True
    
    def _get_epss_score_cached(self, cve_id: str) -> Optional[float]:
        """获取 EPSS 分数（使用本地缓存）"""
        try:
            # 获取 EPSS 管理器实例
            epss_mgr = get_epss_manager()
            
            if epss_mgr is None:
                return None
            
            # 检查数据是否过期（如果需要则自动更新）
            if not epss_mgr.is_data_available():
                logger.info("正在下载最新的 EPSS 数据...")
                success = epss_mgr.download_latest_epss()
                if not success:
                    logger.warning("EPSS 数据下载失败，跳过 EPSS 评分")
                    return None
            
            # 从缓存查询
            score = epss_mgr.get_epss_score(cve_id)
            
            if score is not None:
                return score
            
            # 未找到记录
            return None
            
        except Exception as e:
            logger.debug(f"获取 EPSS 分数失败 ({cve_id}): {e}")
            return None
    
    @staticmethod
    def batch_get_epss_scores(cve_ids: List[str]) -> Dict[str, float]:
        """批量获取 EPSS 分数（优化性能）"""
        try:
            epss_mgr = get_epss_manager()
            
            if epss_mgr is None:
                return {}
            
            return epss_mgr.batch_get_epss_scores(cve_ids)
            
        except Exception as e:
            logger.error(f"批量获取 EPSS 分数失败：{e}")
            return {}
    
    def close(self):
        """关闭数据库连接和 EPSS 管理器"""
        if self.conn:
            self.conn.close()
            logger.info("Grype 数据库连接已关闭")
        
        # 关闭 EPSS 管理器
        global _epss_manager
        if _epss_manager:
            _epss_manager.close()
            _epss_manager = None
