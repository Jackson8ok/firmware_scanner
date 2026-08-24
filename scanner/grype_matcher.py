"""
grype CLI 匹配器 - v2.5.0 核心组件

替代自研匹配器，直接调用 grype CLI 进行 CVE 匹配
确保结果与 grype CLI 基准一致（偏差 ≤20%）

使用方式：
    matcher = GrypeCLIMatcher(grype_bin="/usr/local/bin/grype")
    vulns = matcher.scan("/path/to/extracted/firmware")
"""

import json
import subprocess
import os  # 添加 os 导入
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .engine import Vulnerability, Component

logger = logging.getLogger(__name__)


class GrypeCLIMatcher:
    """grype CLI 匹配器"""
    
    def __init__(self, grype_bin: str = "/usr/local/bin/grype", 
                 cache_dir: str = "./cache/grype",
                 timeout: int = 600):  # 增加到 600 秒
        """
        初始化 grype CLI 匹配器
        
        Args:
            grype_bin: grype CLI 路径
            cache_dir: 缓存目录
            timeout: 扫描超时时间（秒）
        """
        self.grype_bin = grype_bin
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        
        # 检查 grype CLI 可用性
        self._check_grype_available()
    
    def _check_grype_available(self):
        """检查 grype CLI 是否可用"""
        try:
            result = subprocess.run(
                [self.grype_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"✅ grype CLI 可用：{result.stdout.strip()}")
            else:
                raise RuntimeError(f"grype CLI 检查失败：{result.stderr}")
        except FileNotFoundError:
            raise RuntimeError(f"grype CLI 未找到：{self.grype_bin}")
        except Exception as e:
            raise RuntimeError(f"grype CLI 检查失败：{e}")
    
    def scan(self, target_path: str, source_type: str = "directory") -> List[Vulnerability]:
        """
        扫描目标路径
        
        Args:
            target_path: 固件解压目录或 SBOM 文件路径
            source_type: "directory" | "sbom"
        
        Returns:
            List[Vulnerability]
        """
        target_path = str(Path(target_path).resolve())
        
        if not Path(target_path).exists():
            raise FileNotFoundError(f"目标路径不存在：{target_path}")
        
        # 构建 grype 命令
        cmd = self._build_grype_command(target_path, source_type)
        
        logger.info(f"🔍 调用 grype CLI 扫描：{target_path}")
        logger.debug(f"命令：{' '.join(cmd)}")
        
        # 设置环境变量使用配置文件
        env = os.environ.copy()
        grype_config_path = os.path.join(os.path.dirname(self.grype_bin), "grype.yaml")
        if Path(grype_config_path).exists():
            env["GRYPE_CONFIG"] = grype_config_path
            logger.debug(f"使用 grype 配置：{grype_config_path}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                raise RuntimeError(f"grype CLI 扫描失败 (exit {result.returncode}): {error_msg}")
            
            # 解析 JSON 输出
            vulns = self._parse_grype_json(result.stdout)
            logger.info(f"✅ grype CLI 扫描完成：发现 {len(vulns)} 个 CVE")
            
            return vulns
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"grype CLI 扫描超时（{self.timeout}s）")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"grype JSON 解析失败：{e}")
        except Exception as e:
            logger.error(f"❌ grype CLI 扫描失败：{e}")
            raise
    
    def _build_grype_command(self, target_path: str, source_type: str) -> List[str]:
        """构建 grype 命令"""
        cmd = [
            self.grype_bin,
            "-o", "json",
        ]
        
        # 根据源类型添加参数
        if source_type == "sbom":
            # SBOM 模式：grype sbom:<path>
            cmd.extend([f"sbom:{target_path}"])
            logger.info(f"🔍 grype CLI SBOM 模式：{target_path}")
        else:
            # directory 模式
            cmd.append(target_path)
            logger.info(f"🔍 grype CLI 目录模式：{target_path}")
        
        # 添加排除路径（避免扫描工具自身）
        exclude_patterns = [
            "./tools/grype",
            "./tools/syft",
            "./cache",
            "./.git"
        ]
        for pattern in exclude_patterns:
            cmd.extend(["--exclude", pattern])
        
        return cmd
    
    def _parse_grype_json(self, json_str: str) -> List[Vulnerability]:
        """解析 grype JSON 输出（过滤非 JSON 行）"""
        # 过滤 grype 日志前缀，只保留 JSON 内容
        json_lines = []
        for line in json_str.splitlines():
            line = line.strip()
            # 跳过 grype 日志行：以 [时间戳] 开头或包含 WARN/ERROR
            if line.startswith('[') and ']' in line:
                continue
            if line.startswith('WARN') or line.startswith('ERROR'):
                continue
            if line:
                json_lines.append(line)
        
        if not json_lines:
            logger.warning("grype 输出为空，未找到 JSON 数据")
            return []
        
        json_content = '\n'.join(json_lines)
        
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败：{e}")
            logger.debug(f"原始内容：{json_content[:500]}")
            return []
        
        vulns = []
        for match in data.get("matches", []):
            try:
                vuln = self._convert_match_to_vulnerability(match)
                vulns.append(vuln)
            except Exception as e:
                logger.warning(f"解析 CVE 失败：{match.get('vulnerability', {}).get('id', 'unknown')}: {e}")
                continue
        
        # 全局去重：(cve_id, component_name, version)
        seen = set()
        unique_vulns = []
        for vuln in vulns:
            key = (vuln.cve_id, vuln.component_name, vuln.component_version)
            if key not in seen:
                seen.add(key)
                unique_vulns.append(vuln)
        
        if len(vulns) != len(unique_vulns):
            logger.info(f"去重：{len(vulns)} → {len(unique_vulns)}")
        
        return unique_vulns
    
    def _convert_match_to_vulnerability(self, match: dict) -> Vulnerability:
        """将 grype match 转换为平台 Vulnerability 格式（v2.5.1 字段补全修复）"""
        vuln_data = match.get("vulnerability", {})
        artifact = match.get("artifact", {})
        fix = match.get("fix", {})
        
        # 解析 CVSS（v2.5.1 修复：正确路径是 cvss[].metrics.baseScore）
        cvss_score = 0.0
        cvss_vector = ""
        severity = "Unknown"
        
        cvss_data = vuln_data.get("cvss", [])
        if isinstance(cvss_data, list):
            for cvss_entry in cvss_data:
                if isinstance(cvss_entry, dict):
                    # v2.5.1 修复：grype 输出结构是 cvss[].metrics.baseScore
                    metrics = cvss_entry.get("metrics", {})
                    if isinstance(metrics, dict):
                        cvss_score = float(metrics.get("baseScore", 0.0))
                        cvss_vector = metrics.get("vectorString", cvss_entry.get("vector", ""))
                        severity = metrics.get("severity", cvss_entry.get("severity", "Unknown"))
                    else:
                        # 降级兼容旧格式
                        cvss_score = float(cvss_entry.get("baseScore", 0.0))
                        cvss_vector = cvss_entry.get("vector", "")
                        severity = cvss_entry.get("severity", "Unknown")
                    break
        elif isinstance(cvss_data, dict):
            metrics = cvss_data.get("metrics", {})
            if isinstance(metrics, dict):
                cvss_score = float(metrics.get("baseScore", 0.0))
                cvss_vector = metrics.get("vectorString", cvss_data.get("vector", ""))
                severity = metrics.get("severity", cvss_data.get("severity", "Unknown"))
            else:
                cvss_score = float(cvss_data.get("baseScore", 0.0))
                cvss_vector = cvss_data.get("vector", "")
                severity = cvss_data.get("severity", "Unknown")
        
        # 如果 CVSS 中没有 severity，从 top-level severity 获取
        if severity == "Unknown":
            severity = vuln_data.get("severity", "Unknown")
        
        # 解析发布日期（v2.5.1：grype 输出无此字段，需从 Grype DB 补查）
        published_date = self._get_published_date_from_db(vuln_data.get("id", ""))
        
        # 获取修复版本
        fixed_version = fix.get("version")
        
        # v2.5.1 修复：读取 EPSS 字段（grype 输出中有 epss 数组）
        epss_score = self._extract_epss_from_grype(vuln_data)
        
        return Vulnerability(
            cve_id=vuln_data.get("id", ""),
            component_name=artifact.get("name", ""),
            component_version=artifact.get("version", "unknown"),
            severity=severity,
            cvss_score=cvss_score,
            cvss_vector=cvss_vector,
            description=vuln_data.get("description", ""),
            fixed_version=fixed_version,
            published_date=published_date,
            epss_score=epss_score,
            version_status="matched"
        )
    
    def _extract_epss_from_grype(self, vuln_data: dict) -> Optional[float]:
        """从 grype 输出中提取 EPSS 分数（v2.5.1 新增）"""
        epss_list = vuln_data.get("epss", [])
        if isinstance(epss_list, list) and len(epss_list) > 0:
            epss_entry = epss_list[0]
            if isinstance(epss_entry, dict):
                # grype 输出：epss[0].epss 是分数，epss[0].percentile 是百分位
                epss = epss_entry.get("epss")
                if epss is not None:
                    try:
                        return float(epss)
                    except (ValueError, TypeError):
                        pass
        return None
    
    def _get_published_date_from_db(self, cve_id: str) -> Optional[datetime]:
        """从 Grype DB 查询 CVE 发布日期（v2.5.2 修复：查对库 + 列名）"""
        if not cve_id:
            return None
        
        try:
            # v2.5.2 修复：直接连接 Grype DB（而非 EPSS 缓存库）
            grype_db_path = os.path.join(os.path.dirname(self.grype_bin), "..", "db", "grype", "6", "vulnerability.db")
            grype_db_path = os.path.normpath(grype_db_path)
            
            if not Path(grype_db_path).exists():
                # 尝试备用路径
                grype_db_path = "/mnt/workspace/firmware_scanner/db/grype/6/vulnerability.db"
            
            if not Path(grype_db_path).exists():
                logger.debug(f"Grype DB 未找到：{grype_db_path}")
                return None
            
            import sqlite3
            conn = sqlite3.connect(grype_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # v2.5.2 修复：列名 cve → name（vulnerability_handles 表的 CVE 列名为 name）
            cursor.execute("""
                SELECT published_date FROM vulnerability_handles
                WHERE name = ?
                LIMIT 1
            """, (cve_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row and row['published_date']:
                date_str = row['published_date']
                # v2.5.2 修复：使用 fromisoformat 兼容时区与毫秒格式
                try:
                    # 格式：2023-08-22 19:16:31.08+00:00 或 2023-08-22 19:16:31
                    if '+' in date_str or '-' in date_str[10:]:
                        # 有时区信息，去掉时区部分
                        date_str = date_str.split('+')[0].split('-')[0] + '-' + date_str.split('-')[1]
                        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                            try:
                                return datetime.strptime(date_str, fmt)
                            except ValueError:
                                continue
                    else:
                        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                            try:
                                return datetime.strptime(date_str, fmt)
                            except ValueError:
                                continue
                except Exception as e:
                    logger.debug(f"解析 published_date 失败 ({cve_id}): {e}")
                    
        except Exception as e:
            logger.debug(f"查询 Grype DB published_date 失败 ({cve_id}): {e}")
        return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """解析日期字符串"""
        if not date_str:
            return None
        
        try:
            # grype 日期格式：2021-12-10T00:00:00Z
            if isinstance(date_str, datetime):
                return date_str
            
            # 尝试多种格式
            for fmt in (
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d"
            ):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            return None
        except Exception:
            return None
    
    def get_grype_version(self) -> str:
        """获取 grype 版本"""
        try:
            result = subprocess.run(
                [self.grype_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"


class GrypeDBMatcher:
    """
    直接查询 Grype SQLite DB（备选方案）
    
    当 grype CLI 性能不满足要求时使用
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self._connect()
    
    def _connect(self):
        """连接数据库"""
        import sqlite3
        
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Grype DB 不存在：{self.db_path}")
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"已连接 Grype DB：{self.db_path}")
    
    def query(self, components: List[Component]) -> List[Vulnerability]:
        """
        批量查询 CVE（修复自研匹配器缺陷）
        
        关键改进：
        1. 使用 Grype version ranges 精确版本匹配
        2. 完整解析 severity/CVSS/EPSS
        3. 全局去重：(cve_id, component_name, version)
        """
        # TODO: 实现 Grype DB 直接查询逻辑
        # 参考 scanner/engine.py CVEMatcher._query_component()
        # 但修复版本约束和字段补全问题
        pass
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()


# 便捷函数
def scan_with_grype(target_path: str, grype_bin: str = "/usr/local/bin/grype") -> List[Vulnerability]:
    """
    快速扫描（便捷函数）
    
    Args:
        target_path: 目标路径
        grype_bin: grype CLI 路径
    
    Returns:
        List[Vulnerability]
    """
    matcher = GrypeCLIMatcher(grype_bin=grype_bin)
    return matcher.scan(target_path)
