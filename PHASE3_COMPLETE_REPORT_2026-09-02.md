# AFVS v2.7.0-Phase3 完成报告

**日期**: 2026-09-02  
**阶段**: Phase 3/4  
**问题编号**: ISSUE-FWSCAN-2026-003  
**状态**: ✅ 完成  

---

## 📋 Phase 3 概述

**需求**: 版本未知组件优化标注  
**来源**: ARM Cortex-M 车载控制器固件验收测试 (FreeRTOS 版本 unknown 案例)  
**严重度**: 🟡 中（版本未知组件报告不清晰）  

---

## 🔧 问题描述

### 现象
FreeRTOS 可被识别（命中 `FreeRTOS Kernel Fault`、`malloc failed hook` 等），但版本始终为 `unknown`——内核版本通常不以字符串形式固化在固件中。

### 影响
- **用户困惑**: 无法区分「未识别组件」和「识别但版本未知」
- **CVE 匹配策略不清晰**: 版本未知时是否报告 CVE？
- **报告缺乏置信度**: 用户无法判断识别结果的可靠性

### 用户需求
1. 明确标注版本未知组件（「版本未知，需厂商提供」）
2. CVE 匹配策略透明化（版本未知时报告全部 CVE，但标注不确定性）
3. 提供置信度指示（高/中/低）

---

## ✅ 实现方案

### 1. Component 类增强 (`scanner/engine.py`)

**新增字段**:
```python
@dataclass
class Component:
    name: str
    version: str
    type: str
    path: str
    cpe: Optional[str] = None
    confidence: str = "high"          # 新增：置信度 (high/medium/low)
    version_note: Optional[str] = None # 新增：版本说明
    evidence: Optional[List[str]] = None  # 新增：识别证据
    
    def to_dict(self):
        return {
            'name': self.name,
            'version': self.version,
            'type': self.type,
            'path': self.path,
            'cpe': self.cpe,
            'confidence': self.confidence,  # ✅ 新增
            'version_note': self.version_note,  # ✅ 新增
            'evidence': self.evidence or []  # ✅ 新增
        }
```

**置信度规则**:

| 场景 | 置信度 | 版本说明 | 示例 |
|------|--------|---------|------|
| 版本已知 | **high** | None | BusyBox v1.35.0 |
| 版本未知但可识别 (FreeRTOS/lwIP) | **medium** | 「版本未知（需厂商提供）」 | FreeRTOS (有证据但无版本) |
| 其他版本未知 | **low** | 「版本未知」 | Zlib (仅有模糊特征) |

### 2. 组件识别逻辑优化

**置信度判定**:
```python
if version:
    confidence = "high"
    version_note = None
elif name in ['FreeRTOS', 'lwIP']:
    # 版本未知但可识别组件
    confidence = "medium"
    version_note = "版本未知（需厂商提供）"
else:
    confidence = "low"
    version_note = "版本未知"

# 收集证据（前 3 个匹配）
evidence = list(set(matches))[:3]
```

**证据收集**:
- 自动收集匹配字符串（去重，前 3 个）
- 示例：`["FreeRTOS Kernel Fault", "malloc failed hook", "xTaskCreate"]`

**日志增强**:
```
✓ 识别 FreeRTOS: 5 次匹配，版本=unknown [medium]
✓ 识别 BusyBox: 3 次匹配，版本=1.35.0 [high]
```

### 3. CVE 匹配策略优化

**版本未知时的策略**:
```python
if component.version and component.version != 'unknown':
    version_matched, fixed_version = self._match_version_with_ranges(
        component.version, row['range_blob_json']
    )
    if not version_matched:
        version_status = "not_matched"
else:
    # Phase 3: 版本未知时，保守策略：报告全部 CVE 但标记为 unknown
    version_status = "unknown"
    logger.debug(f"⚠️  {component.name} 版本未知，将报告全部 CVE（需厂商确认）")
```

**R155 合规判定**:
```python
def is_r155_non_compliant(self, days_threshold: int = 180):
    if self.cvss_score < 7.0:
        return False
    if self.published_date is None:
        return False
    # DEF-NEW-03: 版本未知时不计入 R155 判定
    if self.version_status == "unknown":
        return False
    age_days = (datetime.now() - self.published_date).days
    return age_days > days_threshold and not self.fixed_version
```

**效果**: 版本未知的 CVE 不计入超期（避免误报）

### 4. SBOM 比对引擎增强 (`services/sbom/sbom_parser.py`)

**比对结果增强**:
```python
matched.append({
    "name": sbom_comp.name,
    "sbom_version": sbom_version,
    "fingerprint_version": fp_version,
    "confidence": fp_comp.get('confidence', 'high'),  # ✅ 新增
    "version_note": fp_comp.get('version_note'),  # ✅ 新增
    "status": status,
    "evidence": fp_comp.get('evidence', [])
})
```

**新增告警类型**:
```python
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
```

**Summary 增强**:
```python
"summary": {
    "total_sbom": 4,
    "total_fingerprint": 3,
    "matched_count": 2,
    "sbom_only_count": 1,
    "fingerprint_only_count": 1,
    "unknown_version_count": 1  # ✅ 新增
}
```

---

## 🧪 验证结果

### 测试 1: Component 新字段

**输入**:
```python
comp1 = Component(
    name="FreeRTOS",
    version="unknown",
    type="rtos",
    path="/test/firmware.bin",
    confidence="medium",
    version_note="版本未知（需厂商提供）",
    evidence=["FreeRTOS Kernel Fault", "malloc failed hook"]
)
```

**结果**:
```
✅ Component 类新增字段测试通过

组件 1 (版本未知):
  - 名称：FreeRTOS
  - 版本：unknown
  - 置信度：medium
  - 版本说明：版本未知（需厂商提供）
  - 证据：['FreeRTOS Kernel Fault', 'malloc failed hook']
  - to_dict(): {
      'name': 'FreeRTOS',
      'version': 'unknown',
      'confidence': 'medium',
      'version_note': '版本未知（需厂商提供）',
      'evidence': ['FreeRTOS Kernel Fault', 'malloc failed hook']
    }
```

### 测试 2: 比对引擎增强

**输入**:
- SBOM: FreeRTOS v10.4.3, BusyBox v1.35.0, lwIP v2.1.3
- 指纹: FreeRTOS (unknown, medium), BusyBox (1.35.0, high), Zlib (unknown, low)

**结果**:
```
📊 比对结果:
  - 匹配：2
  - 版本未知组件数：1

✅ 匹配组件:
  - FreeRTOS: 置信度=medium, 版本说明=版本未知（需厂商提供）
  - BusyBox: 置信度=high, 版本说明=None

🔔 告警:
  - [sbom_not_in_fingerprint] 1 个组件在 SBOM 中声明但二进制未检测到
    • lwIP
  - [fingerprint_not_in_sbom] 1 个组件在二进制中检测到但 SBOM 未声明
    • Zlib
  - [version_unknown] 1 个组件版本未知（需厂商提供）
    • {'name': 'FreeRTOS', 'version_note': '版本未知（需厂商提供）'}
```

### 测试 3: 技术验证
```
✅ 语法检查通过
✅ 模块导入测试通过
```

---

## 📊 工作量统计

| 阶段 | 计划 | 实际 | 偏差 |
|------|------|------|------|
| 开发 | 1.5 天 | 1.5 天 | 0 |
| 测试 | 0.5 天 | 0.5 天 | 0 |
| **总计** | **2 天** | **2 天** | **0** ✅ |

**文件统计**:
- 修改文件：2 个
  - `scanner/engine.py` (+48 行)
  - `services/sbom/sbom_parser.py` (+8 行)

**代码量**: +56 行

---

## 📦 交付物

| 类型 | 位置/链接 |
|------|----------|
| **代码提交** | `8b05f84` |
| **GitHub Release** | https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.7.0-phase3 |
| **标签** | `v2.7.0-phase3` |
| **需求文档** | `REQUIREMENTS_v2.7.0_2026-08-28.md` |
| **完成报告** | 本文档 |

---

## 🔗 下一步计划

| Phase | 需求 | 优先级 | 计划开始 | 计划完成 |
|-------|------|:--:|----------|----------|
| **Phase 4** | SBOM 融合架构升级 | P0 | 2026-09-03 | 2026-09-16 |
| **Release** | v2.7.0 正式版 | - | 2026-09-17 | 2026-09-20 |

---

## 📝 技术说明

### 置信度分级策略

| 置信度 | 含义 | 适用场景 | CVE 匹配策略 |
|--------|------|---------|------------|
| **high** | 版本已知，精确匹配 | BusyBox v1.35.0 | 精确匹配版本约束 |
| **medium** | 组件可识别，版本未知 | FreeRTOS (有证据但无版本) | 匹配全部 CVE，标注不确定性 |
| **low** | 组件识别不确定 | Zlib (仅有模糊特征) | 匹配全部 CVE，标注低置信度 |

### 版本说明文案

| 场景 | 文案 |
|------|------|
| FreeRTOS/lwIP 版本未知 | 「版本未知（需厂商提供）」 |
| 其他组件版本未知 | 「版本未知」 |
| 版本已知 | None (不显示) |

### R155 合规判定优化

**问题**: 版本未知的 CVE 是否计入超期？

**决策**: 不计入（避免误报）

**理由**:
- 版本未知时，无法确定 CVE 是否影响该版本
- 保守策略：报告全部 CVE，但不判定超期
- 用户需联系厂商确认版本后重新扫描

---

**攻城狮阿信 [Jackson]**  
**zhu80k@163.com**  
**2026-09-02 18:00**
