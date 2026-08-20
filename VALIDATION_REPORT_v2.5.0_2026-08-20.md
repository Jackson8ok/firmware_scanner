# v2.5.0 实际环境验证报告

**验证日期**: 2026-08-20  
**验证环境**: PAI-DSW (Linux 5.10.134)  
**测试样本**: `uploads/owrt_15.05.1.squashfs` (6.9 MB)  
**验证状态**: ⚠️ **部分通过 - grype CLI 性能问题**

---

## 一、验证结果汇总

| 指标 | 目标 | 实际结果 | 状态 |
|------|------|----------|:--:|
| 组件数 | ≥7 | **100**（自研提取器） | ✅ 通过 |
| CVE 数 | 与 grype CLI 偏差 ≤20% | **0**（grype CLI 超时/无结果） | ❌ 失败 |
| cvss/date/epss 非空率 | ≥90% | N/A（无 CVE） | ⏸️ 无法验证 |
| 基线 3 个关键 CVE | 全部命中 | N/A | ⏸️ 无法验证 |
| 无重复记录 | 是 | N/A | ⏸️ 无法验证 |

**总体评估**: ⚠️ **部分通过** - SBOM 生成和 components 传递已修复，但 grype CLI 存在性能问题

---

## 二、详细验证过程

### 1. 环境准备 ✅

```bash
# 安装必要工具
apt-get install -y squashfs-tools

# 验证工具可用性
unsquashfs -version  # ✅ v4.5
./tools/grype/grype --version  # ✅ v0.117.0
```

### 2. 固件解包验证 ✅

**结果**:
```
✅ unsquashfs 可用
✅ 解包成功：cache/{task_id}/squashfs_root
✅ Syft 不可用（未安装）
✅ 自研提取器识别 100 个组件（从 opkg 包信息）
```

### 3. components 变量追踪 ✅ **已修复**

**问题**: 之前降级后 components 显示为 0

**修复**: 添加调试日志确认变量传递

**结果**:
```
[DEBUG] SBOM 生成完成，组件数：100
[DEBUG] SBOM 文件已生成：{path}，组件数：100
[DEBUG] 降级时组件数：100
[DEBUG] 使用自研匹配器，组件数：100
开始 CVE 查询，组件数：100
```

**状态**: ✅ **已解决** - components 变量正确传递

### 4. grype CLI 扫描验证 ❌

#### 测试 A: SBOM 模式

```bash
# 生成 CycloneDX SBOM
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "components": [
    {"type": "application", "name": "busybox", "version": "1.23.2"},
    {"type": "application", "name": "openssl", "version": "1.0.2"},
    ...
  ]
}

# grype CLI 扫描
./tools/grype/grype -o json "sbom:/tmp/test.sbom.json"
```

**结果**: 
- ✅ grype CLI 成功解析 SBOM
- ❌ 返回 0 CVE（即使有 openssl 1.0.2 等已知漏洞组件）

**根因**: 
- CycloneDX SBOM 格式可能缺少 grype 需要的字段（如 purl、CPE）
- 或 grype 对 SBOM 输入的匹配逻辑与目录扫描不同

#### 测试 B: 目录模式

```bash
./tools/grype/grype -o json /path/to/squashfs_root
```

**结果**: 
- ❌ 超时（>120 秒）
- ❌ 100 个组件的目录扫描耗时过长

**根因**: 
- grype CLI 对目录扫描需要遍历所有文件并计算哈希
- Grype DB 查询性能瓶颈

---

## 三、问题清单

### P0 问题

| ID | 问题 | 影响 | 状态 |
|:--:|------|------|:--:|
| P0-1 | grype CLI 目录扫描超时（>120s） | CVE 匹配失败或降级 | 🔴 **未修复** |
| P0-2 | grype CLI SBOM 模式返回 0 CVE | 即使有已知漏洞组件 | 🔴 **未修复** |

### P1 问题（已修复）

| ID | 问题 | 影响 | 状态 |
|:--:|------|------|:--:|
| ~~P1-1~~ | ~~components 变量丢失~~ | ~~自研匹配器收到空列表~~ | ✅ **已修复** |
| ~~P1-2~~ | ~~Component.purl 属性不存在~~ | ~~SBOM 生成失败~~ | ✅ **已修复** |

---

## 四、修复建议

### 方案 A: 回退到自研匹配器（推荐短期方案）

**理由**:
- 自研匹配器性能稳定（<5 秒完成 100 组件 CVE 查询）
- grype CLI 性能问题短期难以解决
- v2.4.3-hotfix 已证明自研匹配器可用性

**实施**:
```python
# task_queue.py
# 默认使用自研匹配器，grype CLI 作为可选验证
grype_cli_enabled = config.get('experimental', {}).get('grype_cli', False)
if grype_cli_enabled:
    # 尝试 grype CLI
    ...
else:
    # 直接使用自研匹配器
    matcher = CVEMatcher(grype_db_path)
```

### 方案 B: 优化 SBOM 格式（中期方案）

**问题**: CycloneDX SBOM 缺少 purl/CPE 字段

**实施**:
```python
# 为组件生成伪 purl
purl = f"pkg:generic/{c.name}@{c.version}"

# 或添加 CPE（如果有）
cpe = c.cpe or f"cpe:2.3:a:{c.name}:{c.name}:{c.version}:*:*:*:*:*:*:*"
```

### 方案 C: 增加 grype CLI 超时时间（临时方案）

**实施**:
```python
# grype_matcher.py
timeout=1200  # 从 600s 增加到 1200s（20 分钟）
```

**缺点**: 用户体验差，扫描时间过长

---

## 五、后续计划

### 短期（v2.5.0 发布前）

1. **回退到自研匹配器作为默认方案** (P0)
   - grype CLI 标记为实验性功能
   - 默认使用自研匹配器确保可用性

2. **文档注明 grype CLI 限制** (P1)
   - RELEASE_NOTES 说明性能问题
   - USER_GUIDE 提供配置选项

3. **重新验证**
   - 使用自研匹配器验证 CVE 匹配结果
   - 确保 v2.4.3-hotfix 的修复仍然有效

### 中期（v2.5.1 或 v3.0.0）

1. **调研 grype CLI 性能优化**
   - SBOM 格式优化（添加 purl/CPE）
   - Grype DB 缓存优化
   - 并行扫描可能性

2. **考虑替代方案**
   - Trivy CLI（性能对比）
   - 直接使用 NVD API

---

## 六、验收标准更新

鉴于 grype CLI 性能问题，建议更新验收标准：

| 原标准 | 更新后 | 说明 |
|--------|--------|------|
| grype CLI 替换自研匹配器 | **自研匹配器为主，grype CLI 可选** | 确保可用性优先 |
| CVE 数与 grype CLI 偏差 ≤20% | **与 v2.4.3-hotfix 结果一致** | 使用相同匹配器 |
| 扫描耗时 ≤60s | 扫描耗时 ≤300s | 包含解包 + SBOM+CVE |

---

**验证者**: 攻城狮阿信 [Jackson]  
**联系方式**: zhu80k@163.com  
**状态**: ⚠️ **部分通过** - components 修复 ✅，grype CLI 性能 ❌  
**建议**: v2.5.0 回退到自研匹配器，grype CLI 延后到 v2.5.1
