#!/usr/bin/env python3
"""
跨平台工具检测模块

支持自动检测以下工具在不同操作系统上的可用性和路径:
- Binwalk (Linux/macOS)
- 7-Zip (Windows/Linux/macOS)
- unsquashfs
- syft
- objcopy

用法:
    from scanner.tool_detector import detect_tools, get_tool_path
    
    tools = detect_tools()
    if tools['binwalk']['available']:
        print(f"Binwalk 已安装：{tools['binwalk']['version']}")
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ToolDetector:
    """跨平台工具检测器"""
    
    # Windows 常见安装路径
    WINDOWS_PATHS = {
        '7z': [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
            os.environ.get('PROGRAMFILES', '') + r"\7-Zip\7z.exe",
        ],
        'binwalk': [],  # Binwalk 在 Windows 上通常通过 WSL 或 Git Bash
        'unsquashfs': [],
        'syft': [],
        'objcopy': [],
    }
    
    def __init__(self):
        self.system = platform.system()
        self.tool_cache = {}
    
    def detect_all_tools(self) -> Dict[str, dict]:
        """检测所有工具的可用性"""
        tools = {
            'binwalk': self.check_binwalk(),
            '7zip': self.check_7zip(),
            'unsquashfs': self.check_unsquashfs(),
            'syft': self.check_syft(),
            'objcopy': self.check_objcopy(),
            'strings': self.check_strings(),
            'file': self.check_file_command(),
        }
        
        logger.info("工具检测结果:")
        for name, info in tools.items():
            status = "✅" if info['available'] else "❌"
            version = info.get('version', 'N/A') or '未知'
            path = info.get('path', 'N/A') or '未找到'
            logger.info(f"  {status} {name:15s} v{version:10s} @ {path}")
        
        return tools
    
    def check_binwalk(self) -> dict:
        """检查 Binwalk 是否可用"""
        try:
            if self.system == "Windows":
                # Windows 上尝试 WSL 或 Git Bash
                wsl_result = self._run_command(['wsl', 'which', 'binwalk'])
                if wsl_result:
                    return {'available': True, 'path': wsl_result, 'version': 'WSL'}
                
                # 尝试 Git Bash
                git_bash_paths = [
                    r"C:\Program Files\Git\usr\bin\binwalk.exe",
                    r"C:\Program Files\Git\bin\binwalk.exe",
                ]
                for path in git_bash_paths:
                    if os.path.exists(path):
                        return {'available': True, 'path': path, 'version': 'Git Bash'}
                
                logger.warning("Binwalk 在 Windows 上需要 WSL 或 Git Bash")
                return {'available': False, 'path': None, 'version': None}
            
            # Linux/macOS
            result = self._run_command(['binwalk', '--version'])
            if result:
                version = result.strip().split()[-1] if result else '未知'
                path = self._find_executable('binwalk')
                return {'available': True, 'path': path, 'version': version}
            
        except Exception as e:
            logger.debug(f"Binwalk 检测失败：{e}")
        
        return {'available': False, 'path': None, 'version': None}
    
    def check_7zip(self) -> dict:
        """检查 7-Zip 是否可用"""
        try:
            if self.system == "Windows":
                # 优先检查 PATH
                result = self._run_command(['7z', '--help'])
                if result:
                    path = self._find_executable('7z')
                    return {'available': True, 'path': path, 'version': 'Windows'}
                
                # 检查常见安装路径
                for path in self.WINDOWS_PATHS['7z']:
                    if path and os.path.exists(path):
                        # 获取版本信息
                        version_result = self._run_command([path, '--help'])
                        version = version_result.split('\n')[0] if version_result else '未知'
                        return {'available': True, 'path': path, 'version': version}
                
                return {'available': False, 'path': None, 'version': None}
            
            else:
                # Linux/macOS
                result = self._run_command(['7z', '--help'])
                if result:
                    path = self._find_executable('7z')
                    return {'available': True, 'path': path, 'version': '7-Zip'}
                
                # 尝试 p7zip
                result = self._run_command(['7za', '--help'])
                if result:
                    path = self._find_executable('7za')
                    return {'available': True, 'path': path, 'version': 'p7zip'}
            
        except Exception as e:
            logger.debug(f"7-Zip 检测失败：{e}")
        
        return {'available': False, 'path': None, 'version': None}
    
    def check_unsquashfs(self) -> dict:
        """检查 unsquashfs 是否可用"""
        try:
            # unsquashfs -version 返回 exit code 1，但输出正常
            result = subprocess.run(
                ['unsquashfs', '-version'],
                capture_output=True, text=True, timeout=10
            )
            if result.stdout and 'version' in result.stdout.lower():
                path = self._find_executable('unsquashfs')
                version = 'squashfs-tools'
                return {'available': True, 'path': path, 'version': version}
        except Exception as e:
            logger.debug(f"unsquashfs 检测失败：{e}")
        
        return {'available': False, 'path': None, 'version': None}
    
    def check_syft(self) -> dict:
        """检查 Syft 是否可用"""
        try:
            result = self._run_command(['syft', '--version'])
            if result:
                path = self._find_executable('syft')
                version = result.strip().split()[-1] if result else '未知'
                return {'available': True, 'path': path, 'version': version}
        except Exception as e:
            logger.debug(f"Syft 检测失败：{e}")
        
        return {'available': False, 'path': None, 'version': None}
    
    def check_objcopy(self) -> dict:
        """检查 objcopy 是否可用"""
        try:
            result = self._run_command(['objcopy', '--version'])
            if result:
                path = self._find_executable('objcopy')
                version = result.split('\n')[0] if result else 'binutils'
                return {'available': True, 'path': path, 'version': version}
        except Exception as e:
            logger.debug(f"objcopy 检测失败：{e}")
        
        return {'available': False, 'path': None, 'version': None}
    
    def check_strings(self) -> dict:
        """检查 strings 命令是否可用"""
        try:
            result = self._run_command(['strings', '-V'])
            if result:
                path = self._find_executable('strings')
                return {'available': True, 'path': path, 'version': 'binutils'}
        except Exception as e:
            pass
        
        return {'available': False, 'path': None, 'version': None}
    
    def check_file_command(self) -> dict:
        """检查 file 命令是否可用"""
        try:
            result = self._run_command(['file', '-v'])
            if result:
                path = self._find_executable('file')
                version = result.split('\n')[0] if result else '未知'
                return {'available': True, 'path': path, 'version': version}
        except Exception as e:
            pass
        
        return {'available': False, 'path': None, 'version': None}
    
    def _run_command(self, cmd: list, timeout: int = 10) -> Optional[str]:
        """运行命令并返回输出"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout if result.returncode == 0 else None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
    
    def _find_executable(self, name: str) -> Optional[str]:
        """查找可执行文件的完整路径"""
        return shutil.which(name) if hasattr(__import__('shutil'), 'which') else None


# 全局实例和便捷函数
_detector: Optional[ToolDetector] = None

def get_detector() -> ToolDetector:
    """获取工具检测器实例"""
    global _detector
    if _detector is None:
        _detector = ToolDetector()
    return _detector

def detect_tools() -> Dict[str, dict]:
    """检测所有工具的可用性（便捷函数）"""
    return get_detector().detect_all_tools()

def is_tool_available(tool_name: str) -> bool:
    """检查特定工具是否可用"""
    tools = detect_tools()
    return tools.get(tool_name, {}).get('available', False)

def get_tool_path(tool_name: str) -> Optional[str]:
    """获取特定工具的路径"""
    tools = detect_tools()
    return tools.get(tool_name, {}).get('path')

# 导入 shutil
import shutil

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 工具检测报告")
    print("=" * 60)
    
    detector = ToolDetector()
    tools = detector.detect_all_tools()
    
    available_count = sum(1 for t in tools.values() if t['available'])
    total_count = len(tools)
    
    print(f"\n总计：{available_count}/{total_count} 工具可用")
    print("\n详情:")
    for name, info in tools.items():
        status = "✅" if info['available'] else "❌"
        version = info.get('version', 'N/A') or '未知'
        path = info.get('path', 'N/A') or '未找到'
        print(f"  {status} {name:15s} v{version:10s} @ {path}")
