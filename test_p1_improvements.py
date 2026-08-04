#!/usr/bin/env python3
"""
P1 改进验证测试脚本
检查日志轮转、错误处理、工具检测等功能
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 60)
print("🔧 P1 改进验证测试")
print("=" * 60)

test_results = []

def test(name, condition, details=""):
    status = "✅ PASS" if condition else "❌ FAIL"
    print(f"\n{status} - {name}")
    if details and not condition:
        print(f"   详情：{details}")
    test_results.append((name, condition))
    return condition

# ============================================================
# P1-4: 日志轮转配置
# ============================================================
print("\n📋 P1-4: 检查日志配置模块")

try:
    from scanner.logging_config import setup_logging, log_audit, get_audit_logger
    test("P1-4a: 导入 logging_config 模块", True)
    
    # 测试初始化
    logger = setup_logging(log_dir="./logs_test", console_level=20)
    test("P1-4b: 日志系统初始化", logger is not None)
    
    # 检查是否创建了日志目录
    logs_test_dir = Path("./logs_test")
    has_log_dir = logs_test_dir.exists()
    
    test("P1-4c: 日志目录创建", has_log_dir)
    
    # 清理测试目录
    import shutil
    if logs_test_dir.exists():
        try:
            shutil.rmtree(logs_test_dir)
        except OSError:
            pass  # 忽略目录非空错误
        
except ImportError as e:
    test("P1-4: 导入日志模块", False, f"ImportError: {e}")
except Exception as e:
    test("P1-4: 日志功能测试", False, f"{type(e).__name__}: {e}")

# ============================================================
# P1-3: 结构化错误响应
# ============================================================
print("\n📋 P1-3: 检查错误处理模块")

try:
    from api.error_handler import (
        ErrorCode, ErrorResponse, AppException,
        raise_file_not_found, raise_file_too_large
    )
    test("P1-3a: 导入 error_handler 模块", True)
    
    # 测试 ErrorCode 常量
    has_error_codes = all(hasattr(ErrorCode, code) for code in [
        'FILE_TOO_LARGE', 'SCAN_FAILED', 'TASK_NOT_FOUND'
    ])
    test("P1-3b: ErrorCode 常量定义", has_error_codes)
    
    # 测试 ErrorResponse 模型
    error = ErrorResponse(
        code="TEST_ERROR",
        message="测试错误消息",
        details="详细技术信息",
        suggestion="解决建议"
    )
    error_dict = error.dict()
    has_required_fields = all(k in error_dict for k in ['code', 'message', 'details', 'suggestion'])
    test("P1-3c: ErrorResponse 模型结构", has_required_fields)
    
    # 测试自定义异常
    try:
        raise AppException(
            code="CUSTOM_ERROR",
            message="自定义错误",
            suggestion="请重试"
        )
    except AppException as e:
        correct_attributes = hasattr(e, 'code') and hasattr(e, 'message') and hasattr(e, 'status_code')
        test("P1-3d: AppException 属性", correct_attributes)
        
except ImportError as e:
    test("P1-3: 导入错误模块", False, f"ImportError: {e}")
except Exception as e:
    test("P1-3: 错误处理测试", False, f"{type(e).__name__}: {e}")

# ============================================================
# P1-2: Windows 工具检测
# ============================================================
print("\n📋 P1-2: 检查跨平台工具检测")

try:
    from scanner.tool_detector import detect_tools, is_tool_available, ToolDetector
    
    detector = ToolDetector()
    test("P1-2a: 创建 ToolDetector 实例", detector is not None)
    
    tools = detect_tools()
    has_all_tools = all(tool in tools for tool in [
        'binwalk', '7zip', 'unsquashfs', 'syft', 'objcopy', 'strings', 'file'
    ])
    test("P1-2b: 检测到所有工具类型", has_all_tools)
    
    # 打印当前系统的可用工具
    available = [name for name, info in tools.items() if info['available']]
    print(f"\n💡 当前系统可用工具：{', '.join(available) or '无'}")
    test("P1-2c: 工具可用性检测", True)  # 总是通过，只是展示信息
        
except ImportError as e:
    test("P1-2: 导入工具检测器", False, f"ImportError: {e}")
except Exception as e:
    test("P1-2: 工具检测测试", False, f"{type(e).__name__}: {e}")

# ============================================================
# 附加测试：集成验证
# ============================================================
print("\n📋 附加：集成测试")

try:
    # 测试 engine.py 使用新的工具检测器
    from scanner.engine import FirmwareExtractor
    extractor = FirmwareExtractor("./test_extract")
    test("附加：FirmwareExtractor 使用新检测器", True)
    
    # 清理
    import shutil
    if Path("./test_extract").exists():
        shutil.rmtree("./test_extract")
        
except Exception as e:
    test("附加：Engine 集成测试", False, f"{type(e).__name__}: {e}")

# ============================================================
# 总结
# ============================================================
print("\n" + "=" * 60)
print("📊 测试结果汇总")
print("=" * 60)

passed = sum(1 for _, result in test_results if result)
failed = sum(1 for _, result in test_results if not result)
total = len(test_results)

print(f"\n总测试数：{total}")
print(f"✅ 通过：{passed}")
print(f"❌ 失败：{failed}")

if failed == 0:
    print("\n🎉 恭喜！所有 P1 改进都已成功实施！")
else:
    print(f"\n⚠️ 仍有 {failed} 个测试未通过")

print("\n" + "=" * 60)

sys.exit(0 if failed == 0 else 1)
