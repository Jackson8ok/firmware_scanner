"""
grype CLI 并发匹配器 - v2.6.0 性能优化

基于 asyncio.gather() 实现多组件并行扫描
目标：扫描速度提升 50%

使用方式：
    matcher = ConcurrentGrypeMatcher(grype_bin="/usr/local/bin/grype", max_concurrency=5)
    vulns = await matcher.scan_async("/path/to/extracted/firmware")
"""

import asyncio
import json
import subprocess
import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from .engine import Vulnerability, Component

logger = logging.getLogger(__name__)


@dataclass
class ScanTask:
    """扫描任务"""
    component_name: str
    component_version: str
    purl: str
    target_path: str
    source_type: str = "directory"


@dataclass
class ScanResult:
    """扫描结果"""
    success: bool
    vulns: List[Vulnerability]
    error: Optional[str] = None
    duration: float = 0.0


class ConcurrentGrypeMatcher:
    """并发 grype CLI 匹配器（v2.6.0）"""
    
    def __init__(self, grype_bin: str = "/usr/local/bin/grype", 
                 cache_dir: str = "./cache/grype",
                 timeout: int = 600,
                 max_concurrency: int = 5,
                 enable_cache: bool = True):
        """
        初始化并发 grype CLI 匹配器
        
        Args:
            grype_bin: grype CLI 路径
            cache_dir: 缓存目录
            timeout: 单个任务超时时间（秒）
            max_concurrency: 最大并发数（默认 5）
            enable_cache: 启用结果缓存
        """
        self.grype_bin = grype_bin
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.max_concurrency = max_concurrency
        self.enable_cache = enable_cache
        
        # 结果缓存：{cache_key: vulns}
        self.result_cache: Dict[str, List[Vulnerability]] = {}
        
        # 检查 grype CLI 可用性
        self._check_grype_available()
        
        logger.info(f"🚀 ConcurrentGrypeMatcher 初始化完成")
        logger.info(f"   - grype_bin: {grype_bin}")
        logger.info(f"   - max_concurrency: {max_concurrency}")
        logger.info(f"   - timeout: {timeout}s")
        logger.info(f"   - cache: {'enabled' if enable_cache else 'disabled'}")
    
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
    
    def _build_grype_command(self, target_path: str, source_type: str) -> List[str]:
        """构建 grype 命令"""
        cmd = [
            self.grype_bin,
            "-o", "json",
        ]
        
        # 根据源类型添加参数
        if source_type == "sbom":
            cmd.extend([f"sbom:{target_path}"])
        else:
            cmd.append(target_path)
        
        # 添加排除路径
        exclude_patterns = [
            "./tools/grype",
            "./tools/syft",
            "./cache",
            "./.git"
        ]
        for pattern in exclude_patterns:
            cmd.extend(["--exclude", pattern])
        
        return cmd
    
    async def _scan_component_async(self, task: ScanTask) -> ScanResult:
        """异步扫描单个组件"""
        start_time = datetime.now()
        
        # 检查缓存
        cache_key = f"{task.purl}:{task.source_type}"
        if self.enable_cache and cache_key in self.result_cache:
            duration = (datetime.now() - start_time).total_seconds()
            logger.debug(f"✅ 缓存命中：{task.component_name}")
            return ScanResult(
                success=True,
                vulns=self.result_cache[cache_key],
                duration=duration
            )
        
        # 构建命令
        cmd = self._build_grype_command(task.target_path, task.source_type)
        
        # 设置环境变量
        env = os.environ.copy()
        grype_config_path = os.path.join(os.path.dirname(self.grype_bin), "grype.yaml")
        if Path(grype_config_path).exists():
            env["GRYPE_CONFIG"] = grype_config_path
        
        try:
            # 异步执行 subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # 等待完成（带超时）
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                duration = (datetime.now() - start_time).total_seconds()
                return ScanResult(
                    success=False,
                    vulns=[],
                    error=f"扫描超时（{self.timeout}s）",
                    duration=duration
                )
            
            if process.returncode != 0:
                duration = (datetime.now() - start_time).total_seconds()
                return ScanResult(
                    success=False,
                    vulns=[],
                    error=f"grype 退出码 {process.returncode}: {stderr.decode()[:200]}",
                    duration=duration
                )
            
            # 解析 JSON
            vulns = self._parse_grype_json(stdout.decode(), task.component_name)
            
            # 缓存结果
            if self.enable_cache:
                self.result_cache[cache_key] = vulns
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.debug(f"✅ {task.component_name} 扫描完成：{len(vulns)} CVEs ({duration:.2f}s)")
            
            return ScanResult(
                success=True,
                vulns=vulns,
                duration=duration
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ {task.component_name} 扫描失败：{e}")
            return ScanResult(
                success=False,
                vulns=[],
                error=str(e),
                duration=duration
            )
    
    def _parse_grype_json(self, json_str: str, component_filter: Optional[str] = None) -> List[Vulnerability]:
        """解析 grype JSON 输出"""
        # 过滤非 JSON 行
        json_lines = []
        for line in json_str.splitlines():
            line = line.strip()
            if line.startswith('[') or line.startswith('WARN') or line.startswith('ERROR'):
                continue
            if line:
                json_lines.append(line)
        
        if not json_lines:
            return []
        
        try:
            data = json.loads('\n'.join(json_lines))
        except json.JSONDecodeError:
            return []
        
        vulns = []
        for match in data.get("matches", []):
            try:
                vuln = self._convert_match_to_vulnerability(match)
                
                # 可选：按组件名过滤
                if component_filter and vuln.component_name != component_filter:
                    continue
                
                vulns.append(vuln)
            except Exception as e:
                continue
        
        # 去重
        seen = set()
        unique_vulns = []
        for vuln in vulns:
            key = (vuln.cve_id, vuln.component_name, vuln.component_version)
            if key not in seen:
                seen.add(key)
                unique_vulns.append(vuln)
        
        return unique_vulns
    
    def _convert_match_to_vulnerability(self, match: dict) -> Vulnerability:
        """转换 match 为 Vulnerability 对象"""
        vuln_info = match.get("vulnerability", {})
        artifact = match.get("artifact", {})
        
        # 提取 CVSS
        cvss_score = None
        cvss_vector = None
        for metric in vuln_info.get("cvss", []):
            if isinstance(metric, dict):
                if metric.get("type") == "base":
                    cvss_score = metric.get("score")
                    cvss_vector = metric.get("vector")
                    break
        
        # 提取 EPSS
        epss_score = vuln_info.get("epss", [{}])[0].get("score") if vuln_info.get("epss") else None
        
        # 提取发布日期
        published_date = vuln_info.get("published_date")
        if published_date:
            # 切割时区
            published_date = published_date.split('+')[0].split('Z')[0]
        
        return Vulnerability(
            cve_id=vuln_info.get("id", "UNKNOWN"),
            component_name=artifact.get("name", "unknown"),
            component_version=artifact.get("version", "unknown"),
            purl=artifact.get("purl", ""),
            description=vuln_info.get("description", ""),
            severity=vuln_info.get("severity", "Unknown"),
            cvss_score=cvss_score,
            cvss_vector=cvss_vector,
            epss_score=epss_score,
            published_date=published_date,
            fixed_version=vuln_info.get("fix", {}).get("versions", [None])[0] if vuln_info.get("fix") else None,
            vuln_type=vuln_info.get("type", "Unknown"),
            namespace=vuln_info.get("namespace", "")
        )
    
    async def scan_async(self, target_path: str, components: Optional[List[Dict[str, Any]]] = None) -> List[Vulnerability]:
        """
        异步并发扫描
        
        Args:
            target_path: 固件解压目录
            components: 组件列表（可选），格式：
                [{"name": "busybox", "version": "1.35.0", "purl": "pkg:..."}]
                如果为 None，则扫描整个目录
        
        Returns:
            List[Vulnerability]
        """
        start_time = datetime.now()
        
        if components is None:
            # 无组件列表：直接扫描整个目录
            logger.info(f"🔍 扫描整个目录：{target_path}")
            task = ScanTask(
                component_name="*",
                component_version="*",
                purl="*",
                target_path=target_path
            )
            result = await self._scan_component_async(task)
            
            if result.success:
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ 扫描完成：{len(result.vulns)} CVEs ({duration:.2f}s)")
                return result.vulns
            else:
                logger.error(f"❌ 扫描失败：{result.error}")
                return []
        else:
            # 有组件列表：并发扫描每个组件
            logger.info(f"🔍 并发扫描 {len(components)} 个组件（max_concurrency={self.max_concurrency}）")
            
            # 创建扫描任务
            tasks = []
            for comp in components:
                task = ScanTask(
                    component_name=comp.get("name", "unknown"),
                    component_version=comp.get("version", "unknown"),
                    purl=comp.get("purl", ""),
                    target_path=target_path,
                    source_type="directory"
                )
                tasks.append(task)
            
            # 并发控制：使用 Semaphore
            semaphore = asyncio.Semaphore(self.max_concurrency)
            
            async def bounded_scan(task: ScanTask) -> ScanResult:
                async with semaphore:
                    return await self._scan_component_async(task)
            
            # 并发执行
            results = await asyncio.gather(
                *[bounded_scan(task) for task in tasks],
                return_exceptions=True
            )
            
            # 聚合结果
            all_vulns = []
            success_count = 0
            fail_count = 0
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"❌ 任务异常：{result}")
                    fail_count += 1
                elif isinstance(result, ScanResult):
                    if result.success:
                        success_count += 1
                        all_vulns.extend(result.vulns)
                    else:
                        fail_count += 1
                        logger.warning(f"⚠️ 任务失败：{result.error}")
            
            # 全局去重
            seen = set()
            unique_vulns = []
            for vuln in all_vulns:
                key = (vuln.cve_id, vuln.component_name, vuln.component_version)
                if key not in seen:
                    seen.add(key)
                    unique_vulns.append(vuln)
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ 并发扫描完成：{len(unique_vulns)} CVEs, 成功={success_count}, 失败={fail_count} ({duration:.2f}s)")
            
            return unique_vulns
    
    def scan(self, target_path: str, components: Optional[List[Dict[str, Any]]] = None) -> List[Vulnerability]:
        """同步包装器"""
        return asyncio.run(self.scan_async(target_path, components))
    
    def clear_cache(self):
        """清空缓存"""
        self.result_cache.clear()
        logger.info("✅ 缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "enabled": self.enable_cache,
            "size": len(self.result_cache),
            "max_concurrency": self.max_concurrency,
            "timeout": self.timeout
        }
