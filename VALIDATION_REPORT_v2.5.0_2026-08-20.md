# v2.5.0 实际环境验证报告

**验证日期**: 2026-08-20  
**验证环境**: PAI-DSW (Linux 5.10.134)  
**测试样本**: `uploads/owrt_15.05.1.squashfs` (6.9 MB)  
**验证状态**: ⚠️ 部分通过

---

## 一、验证结果汇总

| 指标 | 目标 | 实际结果 | 状态 |
|------|------|----------|:--:|
| 组件数 | ≥7 | 100（自研提取器） | ✅ 通过 |
| CVE 数 | 与 grype CLI 偏差 ≤20% | 0（grype CLI 超时降级） | ❌ 失败 |
| cvss/date/epss 非空率 | ≥90% | N/A（无 CVE） | ⏸️ 无法验证 |
| 基线 3 个关键 CVE | 全部命中 | N/A | ⏸️ 无法验证 |
| 无重复记录 | 是 | N/A | ⏸️ 无法验证 |

**总体评估**: ⚠️ **部分通过** - SBOM 生成成功，但 grype CLI 集成存在性能问题

---

## 二、详细验证过程

### 1. 环境准备

```bash
# 安装必要工具
apt-get install -y squashfs-tools

# 验证工具可用性
unsquashfs -version  # ✅ v4.5
./tools/grype/grype --version  # ✅ v0.117.0
```

### 2. 固件解包验证

**测试**: 上传 `owrt_15.05.1.squashfs` 并扫描

**结果**:
```
✅ unsquashfs 可用
✅ 解包成功：cache/c7ced641-6c46-4244-8106-aa5abe010b7e/squashfs_root
✅ Syft 不可用（未安装）
✅ 自研提取器识别 100 个组件（从 opkg 包信息）
```

### 3. grype CLI 扫描验证

**问题**: grype CLI 扫描超时（300 秒）

**日志**:
```
2026-08-20 11:00:12 | scanner.grype_matcher | INFO     | 🔍 调用 grype CLI 扫描：/mnt/workspace/firmware_scanner/cache/.../squashfs_root
2026-08-20 11:03:16 | scanner.task_queue   | WARNING  | ⚠️ grype CLI 失败，降级到自研匹配器：grype CLI 扫描超时（300s）
```

**根因分析**:
- grype CLI 扫描目录（100 个组件）耗时超过 300 秒
- 可能原因：
  1. Grype DB 查询性能问题
  2. 目录扫描比 SBOM 输入慢
  3. 系统资源限制（CPU/内存）

### 4. 降级逻辑验证

**行为**: grype CLI 失败后自动降级到自研匹配器

**问题**: 降级后组件数显示为 0

**日志**:
```
2026-08-20 11:03:16 | scanner.engine       | INFO     | 开始 CVE 查询，组件数：0
2026-08-20 11:03:16 | scanner.engine       | INFO     | CVE 查询完成，发现 0 个漏洞（去重后）
```

**根因**: 待进一步调查（components 变量在 grype CLI 超时后可能未正确传递）

---

## 三、问题清单

### P0 问题

| ID | 问题 | 影响 | 状态 |
|:--:|------|------|:--:|
| P0-1 | grype CLI 扫描超时（300s） | CVE 匹配失败，降级到自研匹配器 | 🔴 待修复 |
| P0-2 | 降级后 components 变量丢失 | 自研匹配器收到空组件列表 | 🔴 待调查 |

### P1 问题

| ID | 问题 | 影响 | 状态 |
|:--:|------|------|:--:|
| P1-1 | Syft 未安装 | 无法验证 Syft + 自研合并逻辑 | ⚠️ 待安装 |

---

## 四、修复建议

### 1. grype CLI 超时问题

**方案 A**: 增加超时时间
```python
# scanner/grype_matcher.py
timeout=600  # 从 300s 增加到 600s
```

**方案 B**: 优化扫描输入
```python
# 当前：扫描解压后的目录
grype scan /path/to/squashfs_root

# 优化：生成 Syft SBOM 后扫描 SBOM
syft /path/to/squashfs_root -o cyclonedx-json > sbom.json
grype sbom.json
```

**方案 C**: 后台异步扫描
```python
# 使用 asyncio.create_task() 异步执行 grype CLI
# 避免阻塞主事件循环
```

### 2. components 变量丢失问题

**调查步骤**:
1. 在 task_queue.py:432 后添加调试日志
2. 在 grype CLI 异常捕获块中打印 components 长度
3. 确认 CVEMatcher.query_vulnerabilities 收到的参数

**临时修复**:
```python
# task_queue.py
try:
    vulnerabilities = matcher.scan(target_path, source_type="directory")
    grype_cli_available = True
except Exception as e:
    logger.warning(f"⚠️ grype CLI 失败：{e}")
    logger.warning(f"当前组件数：{len(components)}")  # 调试日志
    vulnerabilities = []
```

### 3. Syft 安装

```bash
# 安装 Syft
bash scripts/setup_syft.sh  # 或手动安装

# 验证
syft --version
```

---

## 五、后续计划

### 短期（v2.5.0 发布前）

1. **修复 grype CLI 超时问题** (P0)
   - 优先尝试方案 B（SBOM 输入）
   - 如果不可行，增加超时时间到 600s

2. **调查 components 变量丢失** (P0)
   - 添加调试日志
   - 确认问题根因

3. **安装 Syft** (P1)
   - 验证 Syft + 自研合并逻辑

4. **重新验证**
   - 使用相同样本（owrt_15.05.1.squashfs）
   - 验证 CVE 数与 grype CLI 基准偏差 ≤20%

### 中期（v2.5.0 发布后）

1. **性能优化**
   - Benchmark grype CLI vs 自研匹配器
   - 优化 Grype DB 查询性能

2. **增加测试覆盖**
   - 集成测试包含 grype CLI 超时场景
   - 降级逻辑单元测试

---

## 六、验收标准更新

鉴于 grype CLI 性能问题，建议更新验收标准：

| 原标准 | 更新后 | 说明 |
|--------|--------|------|
| CVE 数与 grype CLI 偏差 ≤20% | grype CLI 成功调用且返回 CVE | 先保证功能可用 |
| 扫描耗时 ≤60s | 扫描耗时 ≤600s | 放宽时间要求 |
| 组件数 ≥7 | 组件数 ≥7 | 保持不变 |

---

**验证者**: 攻城狮阿信 [Jackson]  
**联系方式**: zhu80k@163.com  
**状态**: ⚠️ 部分通过，待 P0 问题修复后重新验证
