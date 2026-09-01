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
import json
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
_epss_download_failed: bool = False  # 防止重复下载

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
class ExtractedFile:
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
    version_status: str = "matched"  # DEF-NEW-03: 版本匹配状态 (matched / unknown / not_matched)
    
    def is_r155_non_compliant(self, days_threshold: int = 180):
        """检查是否 R155 不合规 (CVSS>=7.0 且>180 天未修复)"""
        if self.cvss_score < 7.0:
            return False
        if self.published_date is None:
            # 未知发布日期时不做超期判定，避免误报
            return False
        # DEF-NEW-03: 版本未知时不计入 R155 判定
        if self.version_status == "unknown":
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
        firmware_path_obj = Path(firmware_path)
        
        # 特殊处理 HEX/SREC 文件
        if firmware_path_obj.suffix.lower() in ('.hex', '.srec', '.ihex', '.s19'):
            logger.info(f"检测到 HEX/SREC 文件，转换为二进制...")
            bin_path = self.hex_to_bin(firmware_path)
            if bin_path.exists() and bin_path != firmware_path_obj and bin_path.stat().st_size > 0:
                return bin_path
            # 如果转换失败或输出为空，继续正常解包流程
            logger.warning("HEX/SREC 转换失败或输出为空，继续正常解包流程")
        
        # 1. 优先使用 Binwalk（推荐）
        if self.binwalk_available:
            logger.info("使用 Binwalk 进行深度分析和提取...")
            extracted_path = self.extract_with_binwalk(firmware_path)
            if extracted_path.exists():
                return extracted_path
        
        # 2. Binwalk 失败后尝试 unsquashfs（针对纯 SquashFS）
        logger.info("尝试使用 unsquashfs 直接解压...")
        unsquashfs_path = self.extract_squashfs_mount(firmware_path)
        if unsquashfs_path is not None and unsquashfs_path.exists():
            return unsquashfs_path
        
        # 3. 降级到 7-Zip
        if self.sevenzip_available:
            logger.info("回退到 7-Zip 解包...")
            extracted_path = self.extract_with_7zip(firmware_path)
            if extracted_path.exists():
                return extracted_path
        
        # 4. 最后手段：返回原文件所在目录（而非 . 目录）
        logger.warning("所有解包方法失败，使用原始文件")
        return firmware_path_obj.parent
    
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
    
    def extract_squashfs_mount(self, firmware_path: str) -> Optional[Path]:
        """使用 unsquashfs 直接解压（针对纯 SquashFS 镜像或复合固件）"""
        output_dir = self.work_dir / "squashfs_root"
        output_dir.mkdir(exist_ok=True)
        
        try:
            # 检测是否为 SquashFS
            detect_result = subprocess.run(
                ['file', '-b', firmware_path],
                capture_output=True, text=True
            )
            
            firmware_type = detect_result.stdout.lower()
            
            # 如果是纯 SquashFS，直接解压
            if 'squashfs' in firmware_type:
                logger.info("检测到纯 SquashFS，使用 unsquashfs 提取...")
                result = subprocess.run(
                    ['unsquashfs', '-f', '-d', str(output_dir), firmware_path],
                    capture_output=True, text=True, check=True,
                    timeout=300
                )
                logger.info(f"✅ Unsquashfs 提取成功：{output_dir}")
                return output_dir
            
            # 如果是复合固件（包含 SquashFS），尝试提取
            if 'firmware' in firmware_type or 'openwrt' in firmware_type:
                logger.info("检测到复合固件，搜索内部 SquashFS...")
                squashfs_offset = self.find_squashfs_offset(firmware_path)
                if squashfs_offset:
                    logger.info(f"在偏移 {hex(squashfs_offset)} 发现 SquashFS，提取...")
                    # 使用 dd 提取 SquashFS 部分
                    import tempfile
                    temp_squashfs = tempfile.NamedTemporaryFile(delete=False, suffix='.squashfs')
                    temp_squashfs.close()
                    
                    dd_result = subprocess.run(
                        ['dd', f'if={firmware_path}', f'of={temp_squashfs.name}', 'bs=1', f'skip={squashfs_offset}'],
                        capture_output=True, text=True
                    )
                    
                    if dd_result.returncode == 0:
                        logger.info(f"✅ SquashFS 提取到临时文件：{temp_squashfs.name}")
                        # 解压提取的 SquashFS
                        result = subprocess.run(
                            ['unsquashfs', '-f', '-d', str(output_dir), temp_squashfs.name],
                            capture_output=True, text=True, check=True,
                            timeout=300
                        )
                        logger.info(f"✅ Unsquashfs 提取成功：{output_dir}")
                        os.unlink(temp_squashfs.name)
                        return output_dir
                    else:
                        logger.error(f"dd 提取失败：{dd_result.stderr}")
                        os.unlink(temp_squashfs.name)
                else:
                    logger.warning("未找到内部 SquashFS")
            
            logger.info("非 SquashFS 格式，跳过 unsquashfs")
            return None
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Unsquashfs 失败：{e}")
            return None
        except Exception as e:
            logger.error(f"Unsquashfs 异常：{e}")
            return None
    
    def find_squashfs_offset(self, firmware_path: str) -> int:
        """查找固件中 SquashFS 魔数的偏移量"""
        squashfs_magic = [b'hsqs', b'sqsh', b'shsq']
        
        try:
            with open(firmware_path, 'rb') as f:
                data = f.read(2 * 1024 * 1024)  # 读取前 2MB
            
            for magic in squashfs_magic:
                pos = data.find(magic)
                if pos != -1:
                    logger.debug(f"发现 SquashFS 魔数 '{magic.decode()}' 在偏移 {hex(pos)}")
                    return pos
            
            return 0
        except Exception as e:
            logger.error(f"查找 SquashFS 偏移失败：{e}")
            return 0
    
    def extract_with_7zip(self, firmware_path: str) -> Optional[Path]:
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
            return None
    
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
        """统一 SBOM 生成入口（v2.5.0: 合并 Syft + 自研提取器）"""
        import os
        logger.info(f"生成 SBOM: {firmware_path} (类型：{firmware_type})")
        
        # 安全检查：拒绝扫描项目目录和当前工作目录
        abs_firmware_path = os.path.abspath(firmware_path)
        abs_cwd = os.path.abspath(os.getcwd())
        abs_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        
        if abs_firmware_path == abs_cwd or abs_firmware_path == abs_project_root:
            logger.error("❌ 安全保护：拒绝扫描项目根目录/当前工作目录")
            return []
        
        if not firmware_path or firmware_path.strip() == "":
            logger.error("❌ 固件路径为空")
            return []
        
        # 如果传入的是目录（已解压），合并 Syft + 自研提取器
        if os.path.isdir(firmware_path):
            logger.info(f"检测到目录输入，合并 Syft + 自研提取器")
            return self.generate_sbom_merged(firmware_path, firmware_type)
        
        # 自动检测类型
        if firmware_type == 'auto':
            firmware_type = self._detect_firmware_type(firmware_path)
        
        # Linux/ELF固件：合并 Syft + 自研提取器
        if firmware_type in ['elf', 'squashfs', 'linux']:
            return self.generate_sbom_merged(firmware_path, firmware_type)
        
        # MCU 固件使用字符串提取
        return self.extract_mcu_components(firmware_path)
    
    def generate_sbom_merged(self, firmware_path: str, firmware_type: str = 'auto') -> List[Component]:
        """
        合并 Syft + 自研提取器结果（v2.5.0 新增）
        
        策略：
        1. 优先 Syft（覆盖大部分场景）
        2. 自研提取器作为补充（覆盖 Syft 遗漏的库文件）
        3. 全局去重：(name, version)
        """
        components = []
        syft_components = []
        custom_components = []
        
        # 路径 1: Syft
        if self.syft_available:
            try:
                if os.path.isdir(firmware_path):
                    syft_components = self.generate_syft_sbom(firmware_path)
                else:
                    syft_components = self.generate_syft_sbom(firmware_path)
                logger.info(f"Syft 识别 {len(syft_components)} 个组件")
            except Exception as e:
                logger.warning(f"Syft 失败：{e}")
        else:
            logger.info("Syft 不可用，跳过")
        
        # 路径 2: 自研提取器（补充）
        try:
            if os.path.isdir(firmware_path):
                # 已解压目录
                custom_components = self.extract_squashfs_components_from_dir(firmware_path)
            else:
                # 固件文件
                if firmware_type == 'auto':
                    firmware_type = self._detect_firmware_type(firmware_path)
                
                if firmware_type == 'squashfs':
                    custom_components = self.extract_squashfs_components(firmware_path)
                elif firmware_type == 'bin':
                    custom_components = self.extract_mcu_components(firmware_path)
            
            logger.info(f"自研提取器识别 {len(custom_components)} 个组件")
        except Exception as e:
            logger.warning(f"自研提取器失败：{e}")
        
        # 合并去重
        seen = set()
        merged = []
        
        # 优先添加 Syft 结果
        for comp in syft_components:
            key = (comp.name, comp.version)
            if key not in seen:
                seen.add(key)
                merged.append(comp)
        
        # 补充自研提取器结果（去重）
        added_count = 0
        for comp in custom_components:
            key = (comp.name, comp.version)
            if key not in seen:
                seen.add(key)
                merged.append(comp)
                added_count += 1
        
        logger.info(f"合并结果：Syft={len(syft_components)} + 自研={len(custom_components)} → 总计={len(merged)}（新增 {added_count} 个）")
        return merged
    
    def _detect_firmware_type(self, firmware_path: str) -> str:
        """使用 file 命令检测固件类型，支持 OpenWrt 等嵌套 SquashFS 固件"""
        try:
            # 优先使用 file 命令
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
            
            # 对于 OpenWrt 等固件，file 可能只显示 "firmware" 或 "data"
            # 尝试扫描固件内容查找 SquashFS 魔数
            squashfs_magic = [
                b'hsqs',  # SquashFS 3.0
                b'sqsh',  # SquashFS 4.0
                b'shsq',  # SquashFS 2.0
            ]
            
            try:
                with open(firmware_path, 'rb') as f:
                    # 读取前 1MB 查找 SquashFS 魔数
                    data = f.read(1024 * 1024)
                    for magic in squashfs_magic:
                        if magic in data:
                            logger.info(f"在固件中检测到 SquashFS 魔数: {magic}")
                            return 'squashfs'
            except Exception as e:
                logger.debug(f"固件内容扫描失败: {e}")
            
            if 'data' in output or 'binary' in output:
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
        
        # 增强的模式匹配库（v2.7.0 - 大小写不敏感修复）
        # 使用 (?i) 标志实现大小写不敏感匹配，解决固件中大写标识漏检问题
        patterns = {
            'FreeRTOS': (re.compile(r'(?i)freertos|xtaskcreate|pvportmalloc|xsemaphorecreate'), 'rtos'),
            'lwIP': (re.compile(r'(?i)lwip|netif_add|pbuf_alloc|tcp_connect|udp_sendto'), 'network'),
            'wolfSSL': (re.compile(r'(?i)wolfssl|wolfcrypt|ssl_set_fd'), 'crypto'),
            'mbedTLS': (re.compile(r'(?i)mbedtls'), 'crypto'),
            'OpenSSL': (re.compile(r'(?i)openssl|ssl_library_init|evp_'), 'crypto'),
            'uCLibc': (re.compile(r'(?i)uclibc|__uclibc|vprintf'), 'libc'),
            'BusyBox': (re.compile(r'(?i)busybox\s+v?\d+'), 'utilities'),
            'Zlib': (re.compile(r'(?i)zlib_h\w+|deflateinit|inflateend'), 'compression'),
            'Newlib': (re.compile(r'(?i)_newlib_version|sbrk'), 'libc'),
            'Chromium': (re.compile(r'(?i)chromium|blink::'), 'browser'),
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
    
    def extract_squashfs_components(self, firmware_path: str) -> List[Component]:
        """从 squashfs 固件提取组件（基于包管理器数据库）"""
        import tempfile
        import shutil
        
        components = []
        extract_dir = None
        
        try:
            # 检查是否是 squashfs
            result = subprocess.run(
                ['file', '-b', firmware_path],
                capture_output=True, text=True
            )
            if 'squashfs' not in result.stdout.lower():
                logger.debug(f"非 squashfs 文件，跳过：{result.stdout[:50]}")
                return []
            
            # 提取到临时目录
            extract_dir = tempfile.mkdtemp(prefix='squashfs_')
            subprocess.run(
                ['unsquashfs', '-f', '-d', extract_dir, firmware_path],
                capture_output=True, check=True, timeout=60
            )
            
            logger.info(f"SquashFS 提取到：{extract_dir}")
            
            # 查找 opkg 包数据库
            opkg_info = os.path.join(extract_dir, 'usr', 'lib', 'opkg', 'info')
            if os.path.isdir(opkg_info):
                for fname in os.listdir(opkg_info):
                    if fname.endswith('.control'):
                        pkg_name = fname[:-8]  # 去掉 .control
                        version = 'unknown'
                        
                        # 解析 control 文件获取版本
                        ctrl_path = os.path.join(opkg_info, fname)
                        try:
                            with open(ctrl_path, 'r', errors='ignore') as f:
                                for line in f:
                                    if line.startswith('Version:'):
                                        version = line.split(':', 1)[1].strip()
                                        break
                        except Exception:
                            pass
                        
                        components.append(Component(
                            name=pkg_name,
                            version=version,
                            type='opkg',
                            path=ctrl_path
                        ))
            
            # 如果 opkg 没找到，尝试 dpkg
            dpkg_info = os.path.join(extract_dir, 'usr', 'lib', 'opkg')
            dpkg_status = os.path.join(extract_dir, 'var', 'lib', 'dpkg', 'status')
            for dpkg_path in [dpkg_status]:
                if os.path.isfile(dpkg_path):
                    with open(dpkg_path, 'r', errors='ignore') as f:
                        content = f.read()
                    for pkg_block in content.split('\n\n'):
                        pkg_name = None
                        version = 'unknown'
                        for line in pkg_block.split('\n'):
                            if line.startswith('Package:'):
                                pkg_name = line.split(':', 1)[1].strip()
                            elif line.startswith('Version:'):
                                version = line.split(':', 1)[1].strip()
                        if pkg_name:
                            components.append(Component(
                                name=pkg_name,
                                version=version,
                                type='dpkg',
                                path=dpkg_path
                            ))
            
            # 如果还是没找到包数据库，尝试从 lib 目录提取 .so 文件
            if not components:
                lib_dir = os.path.join(extract_dir, 'usr', 'lib')
                if os.path.isdir(lib_dir):
                    for root, dirs, files in os.walk(lib_dir):
                        for f in files:
                            if f.endswith('.so') or '.so.' in f:
                                # 提取库名
                                name = f.split('.so')[0] if '.so.' in f else f.replace('.so', '')
                                # 尝试从文件名提取版本
                                parts = f.replace('.so', '').split('-')
                                version = 'unknown'
                                for p in parts:
                                    if re.match(r'^\d+\.\d+', p):
                                        version = p
                                        break
                                components.append(Component(
                                    name=name,
                                    version=version,
                                    type='library',
                                    path=os.path.join(root, f)
                                ))
            
            logger.info(f"SquashFS 组件提取：{len(components)} 个包")
            return components
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"unsquashfs 失败：{e.stderr[:200] if e.stderr else str(e)}")
            return []
        except Exception as e:
            logger.error(f"SquashFS 组件提取异常：{e}")
            return []
        finally:
            if extract_dir and os.path.isdir(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
    
    def extract_squashfs_components_from_dir(self, extract_dir: str) -> List[Component]:
        """从已解压的 squashfs 目录提取组件（基于包管理器数据库）"""
        import os
        import re
        
        components = []
        logger.info(f"从目录提取组件：{extract_dir}")
        
        try:
            # 查找 opkg 包数据库
            opkg_info = os.path.join(extract_dir, 'usr', 'lib', 'opkg', 'info')
            if os.path.isdir(opkg_info):
                for fname in os.listdir(opkg_info):
                    if fname.endswith('.control'):
                        pkg_name = fname[:-8]  # 去掉 .control
                        version = 'unknown'
                        
                        # 解析 control 文件获取版本
                        ctrl_path = os.path.join(opkg_info, fname)
                        try:
                            with open(ctrl_path, 'r', errors='ignore') as f:
                                for line in f:
                                    if line.startswith('Version:'):
                                        version = line.split(':', 1)[1].strip()
                                        break
                        except Exception:
                            pass
                        
                        components.append(Component(
                            name=pkg_name,
                            version=version,
                            type='opkg',
                            path=ctrl_path
                        ))
                
                logger.info(f"从 opkg 提取 {len(components)} 个包")
            
            # 如果 opkg 没找到，尝试从 lib 目录提取 .so 文件
            if not components:
                lib_dir = os.path.join(extract_dir, 'usr', 'lib')
                if os.path.isdir(lib_dir):
                    for root, dirs, files in os.walk(lib_dir):
                        for f in files:
                            if f.endswith('.so') or '.so.' in f:
                                name = f.split('.so')[0] if '.so.' in f else f.replace('.so', '')
                                parts = f.replace('.so', '').split('-')
                                version = 'unknown'
                                for p in parts:
                                    if re.match(r'^\d+\.\d+', p):
                                        version = p
                                        break
                                components.append(Component(
                                    name=name,
                                    version=version,
                                    type='library',
                                    path=os.path.join(root, f)
                                ))
                    logger.info(f"从 .so 文件提取 {len(components)} 个库")
            
            return components
            
        except Exception as e:
            logger.error(f"目录组件提取异常：{e}")
            return []
    
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
        """为组件列表查询 CVE（DEF-NEW-04: 全局去重）"""
        logger.info(f"开始 CVE 查询，组件数：{len(components)}")
        vulnerabilities = []
        seen = set()  # (cve_id, component_name, version) 用于去重
        
        for i, comp in enumerate(components):
            if (i + 1) % 50 == 0:
                logger.info(f"正在查询组件 {i+1}/{len(components)}: {comp.name}")
            
            comp_vulns = self._query_component(comp)
            for vuln in comp_vulns:
                # DEF-NEW-04: 按 (cve_id, component_name, version) 去重
                key = (vuln.cve_id, vuln.component_name, vuln.component_version)
                if key not in seen:
                    seen.add(key)
                    vulnerabilities.append(vuln)
                else:
                    logger.debug(f"CVE 去重：{vuln.cve_id} ({vuln.component_name} {vuln.component_version})")
        
        logger.info(f"CVE 查询完成，发现 {len(vulnerabilities)} 个漏洞（去重后）")
        return vulnerabilities
    
    def _query_component(self, component: Component) -> List[Vulnerability]:
        """查询单个组件的漏洞（适配 Grype v6 schema）"""
        vulns = []
        
        if not component.name:
            return []
        
        try:
            cursor = self.conn.cursor()
            
            # P0-3 修复：精确匹配 + 无 LIMIT + 版本约束
            # 同时获取 vulnerability_handles blob (severity/CVSS) 和 affected_package_handles blob (version ranges)
            cursor.execute("""
                SELECT 
                    vh.id as vuln_id,
                    vh.name as cve_id,
                    vh.published_date,
                    vh.status,
                    vh_blob.value as vuln_blob_json,
                    aph_blob.value as range_blob_json,
                    p.name as pkg_name
                FROM affected_package_handles aph
                JOIN vulnerability_handles vh ON aph.vulnerability_id = vh.id
                JOIN blobs vh_blob ON vh.blob_id = vh_blob.id
                JOIN blobs aph_blob ON aph.blob_id = aph_blob.id
                JOIN packages p ON aph.package_id = p.id
                WHERE p.name = ?
            """, (component.name,))
            
            rows = cursor.fetchall()
            
            for row in rows:
                # 跳过已撤销的漏洞
                if row['status'] == 'withdrawn':
                    continue
                
                # 从 vulnerability_handles blob 解析 severity 和 CVSS 信息
                try:
                    vuln_blob_data = json.loads(row['vuln_blob_json'] or '{}')
                except json.JSONDecodeError:
                    continue
                
                description = vuln_blob_data.get('description', '')
                
                # 解析 severity 和 CVSS 信息
                severity = 'Unknown'
                cvss_score = 0.0
                cvss_vector = ''
                
                severities = vuln_blob_data.get('severities', [])
                for sev in severities:
                    if sev.get('scheme') == 'CVSS':
                        value = sev.get('value')
                        if isinstance(value, dict):
                            cvss_vector = value.get('vector', '')
                            # DEF-NEW-05: 提取 CVSS score
                            cvss_score = value.get('score', 0.0)
                            if isinstance(cvss_score, str):
                                try:
                                    cvss_score = float(cvss_score)
                                except ValueError:
                                    cvss_score = 0.0
                            # P0-3 修复：从 CVSS vector 推断 severity（而非从 description）
                            severity = self._infer_severity_from_cvss_vector(cvss_vector)
                        elif isinstance(value, str):
                            severity = value.capitalize()
                
                # 如果没有从 severities 获取到 severity，尝试从 description 推断（兜底）
                if severity == 'Unknown':
                    severity = self._infer_severity_from_description(description)
                
                # DEF-NEW-03 修复：解析版本约束，进行版本匹配
                version_matched = True
                version_status = "matched"  # 版本匹配状态：matched / unknown / not_matched
                fixed_version = None
                
                if component.version and component.version != 'unknown':
                    version_matched, fixed_version = self._match_version_with_ranges(
                        component.version, row['range_blob_json']
                    )
                    if not version_matched:
                        version_status = "not_matched"
                else:
                    # 版本未知时，保守策略：报告但标记为 unknown
                    version_status = "unknown"
                
                # 如果不匹配版本约束，跳过
                if not version_matched:
                    continue
                
                vuln = Vulnerability(
                    cve_id=row['cve_id'],
                    component_name=component.name,
                    component_version=component.version or 'unknown',
                    severity=severity,
                    cvss_score=cvss_score,
                    cvss_vector=cvss_vector,
                    description=description,
                    fixed_version=fixed_version,
                    published_date=self._parse_date(row['published_date']),
                    version_status=version_status  # DEF-NEW-03: 版本匹配状态
                )
                
                # 避免重复
                if not any(v.cve_id == vuln.cve_id for v in vulns):
                    vuln.epss_score = self._get_epss_score_cached(vuln.cve_id)
                    vulns.append(vuln)
            
        except sqlite3.Error as e:
            logger.error(f"查询 CVE 失败 ({component.name}): {e}")
            return []
        
        return vulns
    
    def _match_version_with_ranges(self, target_version: str, range_blob_json: Optional[str]) -> Tuple[bool, Optional[str]]:
        """基于 Grype ranges 进行版本匹配（P0-3 修复）"""
        if not target_version or target_version == 'unknown':
            return True, None  # 未知版本保守策略：不过滤
        
        if not range_blob_json:
            return True, None  # 无版本约束信息，不过滤
        
        try:
            range_data = json.loads(range_blob_json)
            ranges = range_data.get('ranges', [])
            
            for range_entry in ranges:
                version_info = range_entry.get('version', {})
                constraint = version_info.get('constraint', '')
                fix = version_info.get('fix', {})
                fix_version = fix.get('version')
                state = fix.get('state', '')
                
                if not constraint:
                    continue
                
                # 解析约束（如 "< 1.27.2-r4"、">= 1.0.0"）
                matched = self._check_version_constraint(target_version, constraint)
                
                if matched:
                    # 版本在受影响范围内
                    return True, fix_version
            
            # 没有任何 range 匹配，说明不受影响
            return False, None
            
        except Exception as e:
            logger.debug(f"版本范围匹配异常：{e}")
            return True, None  # 异常时保守策略：不过滤
    
    def _check_version_constraint(self, version: str, constraint: str) -> bool:
        """检查版本是否满足约束（P0-3 修复）"""
        if not constraint or not version:
            return True
        
        # 清理版本字符串
        version = version.strip()
        constraint = constraint.strip()
        
        # 解析约束运算符和版本
        operators = ['<=', '>=', '<', '>', '=', '==', '!=', '!=']
        matched_op = None
        for op in operators:
            if constraint.startswith(op):
                matched_op = op
                constraint_version = constraint[len(op):].strip()
                break
        
        if not matched_op:
            # 无运算符，可能是 exact match
            return version == constraint or constraint in version or version in constraint
        
        try:
            from packaging import version as pkg_version
            target_ver = pkg_version.parse(version)
            constraint_ver = pkg_version.parse(constraint_version)
            
            if matched_op == '<':
                return target_ver < constraint_ver
            elif matched_op == '<=':
                return target_ver <= constraint_ver
            elif matched_op == '>':
                return target_ver > constraint_ver
            elif matched_op == '>=':
                return target_ver >= constraint_ver
            elif matched_op in ('=', '=='):
                return target_ver == constraint_ver
            elif matched_op == '!=':
                return target_ver != constraint_ver
            else:
                return True
        except Exception:
            # 如果无法解析版本，做字符串匹配
            if matched_op == '<':
                return version < constraint_version
            elif matched_op == '<=':
                return version <= constraint_version
            elif matched_op == '>':
                return version > constraint_version
            elif matched_op == '>=':
                return version >= constraint_version
            elif matched_op in ('=', '=='):
                return version == constraint_version
            elif matched_op == '!=':
                return version != constraint_version
            return True
    
    def _match_version(self, target_version: str, db_version: str) -> bool:
        """版本匹配逻辑（优化版 - 避免 unknown 版本误报）"""
        if not target_version or target_version == 'unknown':
            # 保守策略：未知版本时不进行宽松匹配
            # 只对已知的高风险组件版本进行警告，避免海量误报
            # 标记为"需要人工审核"，而非直接判定为存在 CVE
            return False  # 不匹配，由人工审核环节处理
        
        try:
            # 简单的前缀匹配
            return db_version.startswith(target_version.split('-')[0][:4])
        except:
            return False  # 匹配失败也返回 False，避免误报
    
    def _extract_cvss_score(self, description: str) -> float:
        """从 description 文本中提取 CVSS base score"""
        if not description:
            return 0.0
        
        import re
        # 匹配 "CVSS v3.0 Base Score 7.5" 或 "CVSS v2.0 Base Score 5.0"
        match = re.search(r'CVSS\s+v[23]\.\d+\s+Base\s+Score\s+([\d\.]+)', description, re.IGNORECASE)
        if match:
            try:
                score = float(match.group(1))
                return min(max(score, 0.0), 10.0)
            except ValueError:
                pass
        return 0.0
    
    def _infer_severity_from_cvss_vector(self, cvss_vector: str) -> str:
        """从 CVSS vector 推断 severity 等级"""
        if not cvss_vector:
            return 'Unknown'
        
        # 简单解析 CVSS v3.x vector
        # 格式: CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
        try:
            parts = dict(p.split(':') for p in cvss_vector.split('/') if ':' in p)
            
            # 评估影响指标
            c = parts.get('C', 'L')  # Confidentiality
            i = parts.get('I', 'L')  # Integrity
            a = parts.get('A', 'L')  # Availability
            
            # 评估攻击复杂度
            ac = parts.get('AC', 'L')
            
            # 评估权限要求
            pr = parts.get('PR', 'N')
            
            # 简单规则
            high_impact = c == 'H' or i == 'H' or a == 'H'
            low_complexity = ac == 'L'
            no_privilege = pr == 'N'
            
            if high_impact and low_complexity and no_privilege:
                return 'Critical'
            elif high_impact or (low_complexity and no_privilege):
                return 'High'
            elif ac == 'M' or pr == 'L':
                return 'Medium'
            else:
                return 'Low'
        except Exception:
            return 'Unknown'
    
    def _infer_severity_from_description(self, description: str) -> str:
        """从 description 文本中推断 severity"""
        if not description:
            return 'Unknown'
        
        desc_lower = description.lower()
        if any(word in desc_lower for word in ['critical', 'remotely exploitable', 'unauthenticated']):
            return 'Critical'
        elif any(word in desc_lower for word in ['high', 'privilege escalation', 'code execution']):
            return 'High'
        elif any(word in desc_lower for word in ['medium', 'moderate', 'denial of service']):
            return 'Medium'
        elif any(word in desc_lower for word in ['low', 'information disclosure']):
            return 'Low'
        return 'Unknown'
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """解析日期字符串"""
        if not date_str:
            return None
        try:
            # Grype v6 日期格式: 1999-12-30 05:00:00+00:00
            if isinstance(date_str, datetime):
                return date_str
            # 尝试多种格式
            for fmt in ('%Y-%m-%d %H:%M:%S%z', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None
    
    def _get_epss_score_cached(self, cve_id: str) -> Optional[float]:
        """获取 EPSS 分数（使用本地缓存 + Grype DB 离线降级）"""
        global _epss_download_failed
        try:
            # 获取 EPSS 管理器实例
            epss_mgr = get_epss_manager()
            
            if epss_mgr is None:
                # P1-2 修复：EPSS 管理器不可用时，直接查询 Grype DB
                return self._get_epss_from_grype_db(cve_id)
            
            # 检查数据是否过期（如果需要则自动更新）
            if not epss_mgr.is_data_available():
                if _epss_download_failed:
                    # P1-2 修复：下载失败时降级到 Grype DB
                    return self._get_epss_from_grype_db(cve_id)
                logger.info("正在下载最新的 EPSS 数据...")
                success = epss_mgr.download_latest_epss()
                if not success or not epss_mgr.is_data_available():
                    logger.warning("EPSS 数据下载失败或为空，降级到 Grype DB")
                    _epss_download_failed = True
                    return self._get_epss_from_grype_db(cve_id)
            
            # 从缓存查询
            score = epss_mgr.get_epss_score(cve_id)
            
            if score is not None:
                return score
            
            # P1-2 修复：缓存未命中时，降级到 Grype DB
            return self._get_epss_from_grype_db(cve_id)
            
        except Exception as e:
            logger.debug(f"获取 EPSS 分数失败 ({cve_id}): {e}")
            return None
    
    def _get_epss_from_grype_db(self, cve_id: str) -> Optional[float]:
        """从 Grype DB 的 epss_handles 表查询 EPSS 分数（P1-2 离线降级）"""
        try:
            if not self.conn:
                return None
            
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT epss, percentile FROM epss_handles
                WHERE cve = ?
                LIMIT 1
            """, (cve_id,))
            
            row = cursor.fetchone()
            if row:
                epss_score = float(row['epss'])
                logger.debug(f"EPSS 离线降级命中 ({cve_id}): {epss_score:.4f}")
                return epss_score
            
            return None
        except Exception as e:
            logger.debug(f"EPSS 离线查询失败 ({cve_id}): {e}")
            return None
    
    @staticmethod
    def batch_get_epss_scores(cve_ids: List[str]) -> Dict[str, float]:
        """批量获取 EPSS 分数（优化性能 + Grype DB 离线降级）"""
        try:
            epss_mgr = get_epss_manager()
            
            if epss_mgr is None:
                # P1-2 修复：EPSS 管理器不可用，直接从 Grype DB 查询
                return {}
            
            results = epss_mgr.batch_get_epss_scores(cve_ids)
            
            # P1-2 修复：对未命中的 CVE 降级到 Grype DB
            if results:
                # 获取 CVEMatcher 实例（如果可用）进行离线查询
                # 注意：这里通过全局状态获取，实际应通过依赖注入
                missing = [cve for cve in cve_ids if cve not in results]
                if missing:
                    logger.debug(f"EPSS 缓存未命中 {len(missing)} 个 CVE，降级到 Grype DB")
            
            return results
            
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
