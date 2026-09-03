# AFVS v2.7.0-Phase4 完成报告

**日期**: 2026-09-03  
**阶段**: Phase 4/4  
**问题编号**: ISSUE-FWSCAN-2026-004  
**状态**: ✅ 完成  
**版本**: v2.7.0 正式版就绪  

---

## 📋 Phase 4 概述

**需求**: SBOM 融合架构升级  
**来源**: ARM Cortex-M 车载控制器固件验收测试 (符号裁剪组件漏检)  
**严重度**: 🔴 高 (架构)  

---

## 🔧 问题描述

### 现象
静态链接且已 strip 的组件（如 wolfSSL），二进制中无函数名/版本字符串，纯字符串指纹法无法识别。

**案例**:
- 研发 SBOM 声明：wolfSSL 5.8.4
- 二进制指纹：0 命中
- 实际风险：若二进制确实链接了 wolfSSL → 漏报 67 个 CVE（含 11 个 Critical）

### 核心需求
支持「研发提供 SBOM」作为输入，扫描后输出融合结果，按证据强度分级：
- **A 类**: 指纹确认版本（高置信度，CVE 权重 100%）
- **B 类**: SBOM 声明组件（中置信度，CVE 权重 50%）
- **C 类**: 版本未知组件（低置信度，CVE 权重 25%）

---

## ✅ 实现方案

### 1. SBOM 融合引擎 (`services/sbom/sbom_fusion.py`)

**核心类**:
```python
class SBOMFusionEngine:
    def fuse(sbom_components, fingerprint_components) -> List[FusedComponent]
    def get_fusion_summary() -> Dict
    def calculate_weighted_cve_count(vulnerabilities) -> Dict
```

**融合逻辑**:
```python
# 双方都有（SBOM + 指纹）
if sbom_comp and fp_comp:
    if fp_version == sbom_version and fp_version != 'unknown':
        → A 类（指纹确认）
    elif fp_version == 'unknown':
        → C 类（版本未知）
    else:
        → B 类（版本不一致，以 SBOM 为准）

# 仅有指纹
elif fp_comp:
    → C 类（仅指纹）

# 仅有 SBOM
else:
    → B 类（SBOM 声明，可能符号裁剪）
```

**证据强度分级**:
| 级别 | 含义 | CVE 权重 | 示例 |
|------|------|---------|------|
| **A** | 指纹确认版本 | 1.0 (100%) | BusyBox v1.35.0 (SBOM + 指纹一致) |
| **B** | SBOM 声明 | 0.5 (50%) | wolfSSL 5.8.4 (仅 SBOM) |
| **C** | 仅指纹或版本未知 | 0.25 (25%) | FreeRTOS (版本未知) |

**CVE 加权统计**:
```python
def calculate_weighted_cve_count(vulnerabilities):
    total_weighted = sum(weight[evidence_level] for each vuln)
    # weight: A=1.0, B=0.5, C=0.25
```

### 2. 扫描引擎增强 (`scanner/engine.py`)

**新增方法**:
```python
class SBOMGenerator:
    def generate_sbom_fusion(firmware_path, sbom_components, firmware_type) -> List[FusedComponent]
```

**CVE 匹配器增强**:
```python
class CVEMatcher:
    def query_vulnerabilities(components) -> List[Vulnerability]:
        # Phase 4: 添加 component_evidence_level 字段
        for vuln in comp_vulns:
            vuln.component_evidence_level = comp.evidence_level
    
    def calculate_weighted_statistics(vulnerabilities) -> Dict:
        # 按证据级别加权统计
```

**类型导入**:
```python
from services.sbom.sbom_fusion import FusedComponent
```

### 3. 向后兼容

- 无 SBOM 时行为与 v2.6.0 完全一致
- 现有 API 端点不变
- 数据库 schema 无变更
- 配置文件无变更

---

## 🧪 验证结果

### 测试 1: 融合引擎

**输入**:
- SBOM: FreeRTOS v10.4.3, lwIP v2.1.3, wolfSSL v5.8.4, BusyBox v1.35.0
- 指纹：FreeRTOS (unknown), BusyBox v1.35.0, Zlib v1.2.11

**结果**:
```
📊 融合结果:
  - 总组件数：5
  - A 类（指纹确认）：1 (BusyBox)
  - B 类（SBOM 声明）：2 (wolfSSL, lwIP)
  - C 类（仅指纹/版本未知）：2 (FreeRTOS, Zlib)

📋 融合组件详情:
  BusyBox:
    - 版本：1.35.0
    - 证据级别：A
    - CVE 权重：1.0
  
  wolfSSL:
    - 版本：5.8.4
    - 证据级别：B
    - CVE 权重：0.5
    - 版本说明：SBOM 声明，二进制未检测到（可能符号裁剪）
  
  FreeRTOS:
    - 版本：unknown
    - 证据级别：C
    - CVE 权重：0.25
    - 版本说明：版本未知（需厂商提供）

🔔 告警:
  - [sbom_fingerprint_mismatch] 2 个组件 SBOM 与指纹不一致
  - [fingerprint_only_or_unknown] 2 个组件仅有指纹识别或版本未知
```

### 测试 2: CVE 加权统计

**输入**: 6 个 CVE (Critical=2, High=2, Medium=1, Low=1)
- A 类组件 CVE: 2 个 (Critical=1, High=1)
- B 类组件 CVE: 2 个 (High=1, Medium=1)
- C 类组件 CVE: 2 个 (Critical=1, Low=1)

**结果**:
```
📊 CVE 统计:
  - 原始总数：6
  - 加权总数：3.5

  按严重程度:
    - Critical: 2 (原始) → 1.25 (加权)  [1×1.0 + 1×0.25]
    - High: 2 (原始) → 1.5 (加权)       [1×1.0 + 1×0.5]
    - Medium: 1 (原始) → 0.5 (加权)     [1×0.5]
    - Low: 1 (原始) → 0.25 (加权)       [1×0.25]
```

### 测试 3: 技术验证
```
✅ 语法检查通过
✅ 模块导入测试通过
✅ 融合引擎测试通过
✅ CVE 加权统计测试通过
```

---

## 📊 工作量统计

| 阶段 | 计划 | 实际 | 偏差 |
|------|------|------|------|
| 开发 | 5 天 | 5 天 | 0 |
| 测试 | 2 天 | 2 天 | 0 |
| 文档 | 1 天 | 1 天 | 0 |
| **总计** | **8 天** | **8 天** | **0** ✅ |

**文件统计**:
- 新增文件：1 个
  - `services/sbom/sbom_fusion.py` (10.5 KB, 290 行)
- 修改文件：1 个
  - `scanner/engine.py` (+127 行)

**代码量**: +417 行

---

## 📦 交付物

| 类型 | 位置/链接 |
|------|----------|
| **代码提交** | `ebb8b02` |
| **GitHub Release** | https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.7.0 |
| **标签** | `v2.7.0` |
| **需求文档** | `REQUIREMENTS_v2.7.0_2026-08-28.md` |
| **完成报告** | 本文档 |

---

## 🎯 v2.7.0 完整版总结

### 4 Phase 完成情况

| Phase | 需求 | 工作量 | 状态 | 交付物 |
|-------|------|--------|------|--------|
| **Phase 1** | 大小写不敏感修复 | 1 天 | ✅ | `scanner/engine.py` 组件模式库更新 |
| **Phase 2** | SBOM × 指纹一致性校验 | 4 天 | ✅ | `services/sbom/sbom_parser.py`, `sbom_api.py` |
| **Phase 3** | 版本未知组件优化 | 2 天 | ✅ | `Component` 类增强，置信度分级 |
| **Phase 4** | SBOM 融合架构 | 8 天 | ✅ | `services/sbom/sbom_fusion.py`, CVE 加权统计 |
| **总计** | - | **15 天** | ✅ | **v2.7.0 正式版** |

### 功能矩阵终态

| 功能 | 状态 | 说明 |
|------|:--:|------|
| 大小写不敏感匹配 | ✅ | 10 个核心组件支持 |
| SBOM 解析 (SPDX/CycloneDX/CSV) | ✅ | 自动格式检测 |
| SBOM × 指纹比对 | ✅ | 三类差异识别 + 告警 |
| 版本未知组件标注 | ✅ | 置信度分级 + 版本说明 |
| CVE 匹配策略优化 | ✅ | 版本未知时匹配全部 CVE |
| R155 判定优化 | ✅ | 版本未知 CVE 不计入超期 |
| SBOM 融合架构 | ✅ | A/B/C 类证据分级 + CVE 加权 |

### 测试覆盖率

| 测试类型 | 用例数 | 通过率 |
|---------|--------|--------|
| Phase 1 大小写不敏感 | 12 | 100% |
| Phase 2 SBOM 解析 | 4 | 100% |
| Phase 2 比对引擎 | 3 | 100% |
| Phase 3 Component 字段 | 2 | 100% |
| Phase 3 比对增强 | 2 | 100% |
| Phase 4 融合引擎 | 5 | 100% |
| Phase 4 CVE 加权 | 1 | 100% |
| **总计** | **29** | **100%** |

---

## 🔗 下一步计划

### 短期（v2.7.1 补丁版）
- [ ] 观察项修复：批量任务 completed_at 字段
- [ ] 观察项修复：批量路由格式统一
- [ ] 观察项修复：SMTP Mock 测试方案

### 中期（v2.8.0 功能版）
- [ ] WebSocket 实时推送（替代轮询）
- [ ] 批量扫描性能优化（并发度提升）
- [ ] 报告模板增强（更多预设模板）

### 长期（v3.0.0 架构版）
- [ ] SAST 静态分析集成
- [ ] 二进制相似度分析
- [ ] 分布式扫描架构

---

## 📝 技术说明

### 为什么采用加权统计而非二元判定？

**问题**: B 类组件（仅 SBOM 声明）是否应计入 CVE 统计？

**决策**: 加权统计（A=100%, B=50%, C=25%）

**理由**:
1. **避免误报**: B 类组件可能存在（符号裁剪），二元判定会漏报
2. **避免虚高**: B 类组件也可能不存在（SBOM 错误），全权重会计入虚高
3. **保守策略**: 50% 权重反映「可能存在」的不确定性
4. **用户透明**: 报告同时显示原始数和加权数，用户可自行判断

### 证据强度分级标准

| 级别 | 判定标准 | 置信度 | 建议操作 |
|------|---------|--------|---------|
| **A** | SBOM + 指纹版本一致 | 高 | 直接用于 R155 判定 |
| **B** | 仅 SBOM 声明 | 中 | 联系研发确认是否符号裁剪 |
| **C** | 仅指纹或版本未知 | 低 | 建议补充 SBOM 或联系厂商确认版本 |

### CVE 加权统计公式

```
加权 CVE 总数 = Σ(每个 CVE 的证据权重)

其中：
- A 类组件的 CVE: 权重 = 1.0
- B 类组件的 CVE: 权重 = 0.5
- C 类组件的 CVE: 权重 = 0.25

按严重程度加权:
Critical_weighted = Σ(Critical CVE 的权重)
High_weighted = Σ(High CVE 的权重)
...
```

---

**攻城狮阿信 [Jackson]**  
**zhu80k@163.com**  
**2026-09-03 19:00**
