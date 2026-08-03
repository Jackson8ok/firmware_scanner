#!/usr/bin/env python3
"""
P0 Bug 修复验证测试脚本
运行此脚本检查所有 P0 级别的问题是否已修复
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 60)
print("🔧 P0 Bug 修复验证测试")
print("=" * 60)

test_results = []

def test(name, condition, details=""):
    """记录测试结果"""
    status = "✅ PASS" if condition else "❌ FAIL"
    print(f"\n{status} - {name}")
    if details and not condition:
        print(f"   详情：{details}")
    test_results.append((name, condition))
    return condition

# ============================================================
# P0-1: UploadFile.stem → Path(file.filename).stem
# ============================================================
print("\n📋 P0-1: 检查 api/main.py 中的 file.stem 问题")

try:
    with open(PROJECT_ROOT / "api" / "main.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否存在 file.stem (应该不存在)
    has_stem_bug = 'firmware_id = file.stem' in content
    
    # 检查是否正确使用了 Path(file.filename).stem
    has_fix = 'Path(file.filename).stem' in content
    
    test(
        "P0-1: UploadFile.stem 修复",
        not has_stem_bug and has_fix,
        f"仍存在 file.stem: {has_stem_bug}, 已应用修复：{has_fix}"
    )
except Exception as e:
    test("P0-1: 读取文件失败", False, str(e))

# ============================================================
# P0-2: dict vs dataclass 统一
# ============================================================
print("\n📋 P0-2: 检查 task_queue.py 中 r155_compliance 数据格式统一")

try:
    with open(PROJECT_ROOT / "scanner" / "task_queue.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否有 to_dict() 转换逻辑
    has_conversion = 'if hasattr(compliance_result, \'to_dict\'):' in content
    uses_compliance_dict = "'r155_compliance': compliance_dict" in content
    
    test(
        "P0-2: dataclass/dict 统一处理",
        has_conversion and uses_compliance_dict,
        f"有转换逻辑：{has_conversion}, 使用 compliance_dict: {uses_compliance_dict}"
    )
except Exception as e:
    test("P0-2: 读取文件失败", False, str(e))

# ============================================================
# P0-3: 相对导入越界修复
# ============================================================
print("\n📋 P0-3: 检查 scanner/task_queue.py 的导入语句")

try:
    with open(PROJECT_ROOT / "scanner" / "task_queue.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否存在错误的相对导入 ..compliance
    has_wrong_import = 'from ..compliance' in content
    
    # 检查正确的导入
    has_correct_r155_rules = 'from compliance.r155_rules import check_r155_compliance' in content
    has_correct_r155_checker = 'from .r155_compliance import get_r155_checker' in content
    
    test(
        "P0-3: 相对导入越界修复",
        not has_wrong_import and has_correct_r155_rules and has_correct_r155_checker,
        f"存在错误导入：{has_wrong_import}, 正确导入 r155_rules: {has_correct_r155_rules}, "
        f"正确导入 r155_compliance: {has_correct_r155_checker}"
    )
except Exception as e:
    test("P0-3: 读取文件失败", False, str(e))

# ============================================================
# P0-4: YAML 编码问题修复
# ============================================================
print("\n📋 P0-4: 检查 config.yaml 读取时指定 encoding='utf-8'")

try:
    with open(PROJECT_ROOT / "api" / "main.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查 open() 调用是否包含 encoding='utf-8'
    has_encoding = "open(config_path, encoding='utf-8')" in content
    
    test(
        "P0-4: YAML 编码修复",
        has_encoding,
        f"缺少 encoding='utf-8': {not has_encoding}"
    )
except Exception as e:
    test("P0-4: 读取文件失败", False, str(e))

# ============================================================
# P0-5: Grype DB 路径配置修复
# ============================================================
print("\n📋 P0-5: 检查 config.yaml 中的 Grype DB 路径配置")

try:
    with open(PROJECT_ROOT / "config.yaml", 'r', encoding='utf-8') as f:
        config_content = f.read()
    
    # 检查是否仍然存在占位符路径
    has_placeholder = '"grype_db": "/path/to/grype.db"' in config_content or \
                      "grype_db: \"/path/to/grype.db\"" in config_content
    
    # 检查是否有环境变量支持
    has_env_support = 'GRYPE_DB_PATH' in config_content
    
    # 检查 api/main.py 是否有环境变量处理逻辑
    with open(PROJECT_ROOT / "api" / "main.py", 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    has_env_resolver = 'resolve_env_var' in main_content and \
                       'process_config_values' in main_content
    
    test(
        "P0-5: Grype DB 路径配置修复",
        not has_placeholder and has_env_support and has_env_resolver,
        f"仍有占位符：{has_placeholder}, 环境变量支持：{has_env_support}, "
        f"解析逻辑：{has_env_resolver}"
    )
except Exception as e:
    test("P0-5: 读取文件失败", False, str(e))

# ============================================================
# 尝试导入模块（如果语法检查通过）
# ============================================================
print("\n📋 附加测试：尝试导入关键模块")

try:
    # 测试 scanner.task_queue 是否可以正常导入
    from scanner.task_queue import ScanQueue, TaskStatus
    test("附加：导入 scanner.task_queue", True)
except ImportError as e:
    test("附加：导入 scanner.task_queue", False, f"ImportError: {e}")
except Exception as e:
    test("附加：导入 scanner.task_queue", False, f"{type(e).__name__}: {e}")

try:
    # 测试 compliance.r155_rules 是否可以正常导入
    from compliance.r155_rules import check_r155_compliance
    test("附加：导入 compliance.r155_rules", True)
except ImportError as e:
    test("附加：导入 compliance.r155_rules", False, f"ImportError: {e}")
except Exception as e:
    test("附加：导入 compliance.r155_rules", False, f"{type(e).__name__}: {e}")

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
    print("\n🎉 恭喜！所有 P0 级别的问题都已成功修复！")
    print("\n下一步建议:")
    print("  1. 启动 API 服务进行实际测试")
    print("  2. 上传一个测试固件验证上传功能")
    print("  3. 执行一次完整扫描流程")
else:
    print(f"\n⚠️ 仍有 {failed} 个测试未通过，请检查上述失败项。")
    print("\n建议措施:")
    print("  1. 查看失败详情")
    print("  2. 根据提示手动修复")
    print("  3. 重新运行测试脚本")

print("\n" + "=" * 60)

# 退出码：0=全部通过，1=有失败
sys.exit(0 if failed == 0 else 1)
