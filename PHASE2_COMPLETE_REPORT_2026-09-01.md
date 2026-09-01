# AFVS v2.7.0-Phase2 完成报告

**日期**: 2026-09-01  
**阶段**: Phase 2/4  
**问题编号**: ISSUE-FWSCAN-2026-002  
**状态**: ✅ 完成  

---

## 📋 Phase 2 概述

**需求**: SBOM × 指纹一致性校验  
**来源**: ARM Cortex-M 车载控制器固件验收测试 (wolfSSL 5.8.4 案例)  
**严重度**: 🔴 高（SBOM 与实物不一致静默）  

---

## 🔧 问题描述

### 现象
研发提供的 SBOM 声明固件包含 **wolfSSL 5.8.4**，但二进制指纹扫描未找到任何 wolfSSL 特征（0 命中）。当前工具对此完全静默。

### 风险
- **场景 A**: 二进制实际链接了 wolfSSL 但符号被裁剪
  - → 漏报 67 个 CVE（含 11 个 Critical）
  - → R155 合规风险

- **场景 B**: 二进制确未包含 wolfSSL
  - → SBOM 与实物不符
  - → 成分清单质量问题

### 核心需求
支持「研发提供 SBOM」作为输入，扫描后输出「SBOM 声明组件 × 二进制指纹命中」比对表，对两类差异给出告警：
1. SBOM 有但二进制未命中 → ⚠️ 黄色告警「可能符号裁剪」
2. 二进制命中但 SBOM 未声明 → ⚠️ 黄色告警「SBOM 可能遗漏」

---

## ✅ 实现方案

### 1. SBOM 解析器 (`services/sbom/sbom_parser.py`)

**支持格式**:
- ✅ SPDX 2.3 (JSON) - 完整解析 packages、licenses、externalRefs
- ✅ CycloneDX 1.4 (JSON) - 完整解析 components、supplier、purl
- ✅ CSV (简化格式) - 兼容简单表格数据
- ✅ 自动格式检测 - 基于文件后缀和内容结构

**提取字段**:
```python
@dataclass
class SBOMComponent:
    name: str              # 组件名称
    version: str           # 版本号
    supplier: Optional[str]  # 供应商
    licenses: Optional[List[str]]  # 许可证
    cpe: Optional[str]     # CPE 标识
    purl: Optional[str]    # Package URL
    description: Optional[str]  # 描述
    source: str = "sbom"   # 来源标记
```

**核心函数**:
- `parse_file(file_path)`: 解析 SBOM 文件
- `parse_string(content, format_name)`: 解析 SBOM 字符串
- `_detect_format(file_path)`: 自动检测格式
- `compare_sbom_with_fingerprint(sbom, fingerprint)`: 比对引擎

### 2. SBOM API (`services/sbom/sbom_api.py`)

**端点列表**:

| 端点 | 方法 | 功能 | 请求参数 | 响应 |
|------|------|------|---------|------|
| `/api/sbom/import` | POST | 导入 SBOM | `file` (SBOM 文件), `firmware_id` (可选) | `{sbom_id, components_count, format, status}` |
| `/api/sbom/{id}` | GET | 获取 SBOM 详情 | - | `{sbom: {...}}` |
| `/api/sbom/{id}/comparison` | GET | 比对报告 | - | `{matched, sbom_only, fingerprint_only, warnings, summary}` |
| `/api/sbom/{id}` | DELETE | 删除 SBOM | - | `{success: true}` |

**集成**:
- `api/main.py` 导入并注册 `register_sbom_api(_base_app)`
- 路由总数：32 个（新增 4 个）

### 3. 比对引擎

**比对逻辑**:
```python
def compare_sbom_with_fingerprint(sbom_components, fingerprint_components):
    # 1. 标准化名称映射（大小写不敏感）
    def normalize_name(name):
        return name.lower().replace('-', '').replace('_', '').replace(' ', '')
    
    # 2. 创建索引
    sbom_index = {normalize_name(c.name): c for c in sbom_components}
    fp_index = {normalize_name(c['name']): c for c in fingerprint_components}
    
    # 3. 分类
    matched = []           # 双方均命中
    sbom_only = []         # SBOM 有，指纹无
    fingerprint_only = []  # 指纹有，SBOM 无
    
    # 4. 版本一致性检查
    for name in sbom_index:
        if name in fp_index:
            if sbom_version == fp_version:
                status = "confirmed"
            elif fp_version == 'unknown':
                status = "sbom_version"
            else:
                status = "version_mismatch"
    
    # 5. 生成告警
    warnings = []
    if sbom_only:
        warnings.append({
            "type": "sbom_not_in_fingerprint",
            "message": f"{len(sbom_only)} 个组件在 SBOM 中声明但二进制未检测到"
        })
    if fingerprint_only:
        warnings.append({
            "type": "fingerprint_not_in_sbom",
            "message": f"{len(fingerprint_only)} 个组件在二进制中检测到但 SBOM 未声明"
        })
```

**输出结构**:
```json
{
  "matched": [
    {
      "name": "FreeRTOS",
      "sbom_version": "10.4.3",
      "fingerprint_version": "10.4.3",
      "status": "confirmed",
      "evidence": ["FreeRTOS Kernel Fault"]
    }
  ],
  "sbom_only": [
    {
      "name": "wolfSSL",
      "version": "5.8.4",
      "warning": "二进制未命中，可能符号裁剪或未链接",
      "cpe": "cpe:2.3:a:wolfssl:wolfssl:5.8.4:*:*:*:*:*:*:*"
    }
  ],
  "fingerprint_only": [
    {
      "name": "Zlib",
      "version": "1.2.11",
      "warning": "SBOM 未声明，可能遗漏",
      "evidence": ["zlib_h compressed"]
    }
  ],
  "warnings": [
    {
      "type": "sbom_not_in_fingerprint",
      "count": 2,
      "components": ["lwIP", "wolfSSL"],
      "message": "2 个组件在 SBOM 中声明但二进制未检测到"
    }
  ],
  "summary": {
    "total_sbom": 4,
    "total_fingerprint": 3,
    "matched_count": 2,
    "sbom_only_count": 2,
    "fingerprint_only_count": 1
  }
}
```

---

## 🧪 验证结果

### 测试 1: SPDX 解析
**输入**: `test_sbom.spdx.json` (4 个组件)

**结果**:
```
✅ SPDX 解析成功：4 个组件
  - FreeRTOS v10.4.3 (CPE: cpe:2.3:a:freertos:freertos:10.4.3)
  - lwIP v2.1.3 (CPE: cpe:2.3:a:lwip:lwip:2.1.3)
  - wolfSSL v5.8.4 (CPE: cpe:2.3:a:wolfssl:wolfssl:5.8.4)
  - BusyBox v1.35.0 (CPE: cpe:2.3:a:busybox:busybox:1.35.0)
```

### 测试 2: 比对引擎
**输入**:
- SBOM: 4 个组件 (FreeRTOS, lwIP, wolfSSL, BusyBox)
- 指纹: 3 个组件 (FreeRTOS, BusyBox, Zlib)

**结果**:
```
📊 比对结果:
  - SBOM 组件数：4
  - 指纹组件数：3
  - 匹配：2
  - SBOM 独有：2
  - 指纹独有：1

✅ 匹配组件:
  - FreeRTOS: SBOM v10.4.3 = 指纹 v10.4.3 [confirmed]
  - BusyBox: SBOM v1.35.0 = 指纹 v1.35.0 [confirmed]

⚠️  SBOM 独有:
  - lwIP v2.1.3: 可能符号裁剪或未链接
  - wolfSSL v5.8.4: 可能符号裁剪或未链接

⚠️  指纹独有:
  - Zlib v1.2.11: SBOM 可能遗漏

🔔 告警:
  - [sbom_not_in_fingerprint] 2 个组件在 SBOM 中声明但二进制未检测到
  - [fingerprint_not_in_sbom] 1 个组件在二进制中检测到但 SBOM 未声明
```

### 测试 3: 技术验证
```
✅ 语法检查通过
✅ SBOM 模块导入成功
✅ SBOMParser 实例化成功
✅ main.py 加载成功 (32 个路由)
✅ SBOM API 已注册：/api/sbom/*
```

---

## 📊 工作量统计

| 阶段 | 计划 | 实际 | 偏差 |
|------|------|------|------|
| 开发 | 3 天 | 3 天 | 0 |
| 测试 | 1 天 | 1 天 | 0 |
| **总计** | **4 天** | **4 天** | **0** ✅ |

**文件统计**:
- 新增文件：3 个
  - `services/sbom/sbom_parser.py` (12 KB, 330 行)
  - `services/sbom/sbom_api.py` (6 KB, 180 行)
  - `test_sbom.spdx.json` (2 KB, 测试样本)
- 修改文件：1 个
  - `api/main.py` (+6 行)

**代码量**: +516 行

---

## 📦 交付物

| 类型 | 位置/链接 |
|------|----------|
| **代码提交** | `e8a6129` |
| **GitHub Release** | https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.7.0-phase2 |
| **标签** | `v2.7.0-phase2` |
| **需求文档** | `REQUIREMENTS_v2.7.0_2026-08-28.md` |
| **完成报告** | 本文档 |
| **测试样本** | `test_sbom.spdx.json` |

---

## 🔗 下一步计划

| Phase | 需求 | 优先级 | 计划开始 | 计划完成 |
|-------|------|:--:|----------|----------|
| **Phase 3** | 版本未知组件优化标注 | P1 | 2026-09-02 | 2026-09-04 |
| **Phase 4** | SBOM 融合架构升级 | P0 | 2026-09-05 | 2026-09-16 |
| **Release** | v2.7.0 正式版 | - | 2026-09-17 | 2026-09-20 |

---

## 📝 技术说明

### 为什么使用内存存储而非数据库？
- **Phase 2 原型阶段**: 快速验证功能
- **简化依赖**: 避免引入额外的数据库依赖
- **Phase 4 升级**: 将在 SBOM 融合架构中引入 SQLite 持久化

### 名称标准化策略
```python
def normalize_name(name: str) -> str:
    return name.lower().replace('-', '').replace('_', '').replace(' ', '')
```
- **目的**: 处理命名差异（如 `FreeRTOS` vs `free-rtos` vs `FREE_RTOS`）
- **效果**: 提高匹配率，减少误报
- **限制**: 极端情况下可能误匹配（如 `zlib` vs `z-lib`），需人工审核

### 告警分级策略
| 告警类型 | 级别 | 含义 | 建议操作 |
|---------|------|------|---------|
| `sbom_not_in_fingerprint` | 🟡 中 | SBOM 声明但二进制未检测到 | 联系研发确认是否符号裁剪 |
| `fingerprint_not_in_sbom` | 🟡 中 | 二进制检测到但 SBOM 未声明 | 更新 SBOM，补充遗漏组件 |
| `version_mismatch` | 🟠 高 | SBOM 与指纹版本不一致 | 优先以指纹为准，更新 SBOM |

---

**攻城狮阿信 [Jackson]**  
**zhu80k@163.com**  
**2026-09-01 17:00**
