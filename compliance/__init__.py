"""
R155 合规模块（已升级）

⚠️ 此模块已废弃，所有功能已迁移到 scanner.r155_compliance。
此处仅做向后兼容的 re-export，不建议在新代码中使用。
"""

# 重新导出到新版实现，避免调用方同时依赖两套规则
from scanner.r155_compliance import (
    R155ComplianceChecker,
    get_r155_checker,
    evaluate_firmware_compliance,
    ComplianceLevel,
    RegulationClause,
    ComplianceEvidence,
    ComplianceScore,
)

__all__ = [
    "R155ComplianceChecker",
    "get_r155_checker",
    "evaluate_firmware_compliance",
    "ComplianceLevel",
    "RegulationClause",
    "ComplianceEvidence",
    "ComplianceScore",
]
